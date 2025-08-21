from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------- Data model: Capability Graph ----------


@dataclass
class ToolSchema:
    name: str
    description: Optional[str] = None
    parameters: Dict[str, str] = field(default_factory=dict)  # arg_name -> type string


@dataclass
class ToolSpec:
    server_key: str
    tool_name: str
    schema: ToolSchema


@dataclass
class ServerSpec:
    key: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    tools: List[ToolSchema] = field(default_factory=list)


@dataclass
class CapabilityGraph:
    servers: Dict[str, ServerSpec] = field(default_factory=dict)
    tools: Dict[str, ToolSpec] = field(default_factory=dict)  # "server.tool" -> ToolSpec


# ---------- Planner model ----------


@dataclass
class PlanStep:
    id: str
    intent: str
    tool_key: str  # "server.tool"
    args_hint: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)


@dataclass
class Plan:
    steps: List[PlanStep] = field(default_factory=list)


# ---------- Capability discovery ----------


async def _fetch_tools_metadata(session: ClientSession) -> List[Dict[str, Any]]:
    logger = logging.getLogger("orchestrator")
    # Try common method/property names; fall back gracefully.
    for candidate in ("list_tools", "get_tools"):
        method = getattr(session, candidate, None)
        if callable(method):
            try:
                logger.debug("fetching tools via %s", candidate)
                return await method()
            except Exception:
                logger.exception("tool metadata fetch via %s failed", candidate)
                pass
    prop = getattr(session, "tools", None)
    if isinstance(prop, list):
        return prop
    return []


def _coerce_schema(meta: Any) -> ToolSchema:
    # Accept various shapes: dict, (name, dict), (name, description), str
    if isinstance(meta, tuple) and len(meta) == 2:
        name_candidate, details = meta
        if isinstance(details, dict):
            meta = {"name": name_candidate, **details}
        else:
            meta = {"name": name_candidate, "description": str(details)}
    elif isinstance(meta, str):
        meta = {"name": meta}

    if not isinstance(meta, dict):
        meta = {"name": "unknown"}

    name = meta.get("name") or meta.get("tool") or "unknown"
    description = meta.get("description") or meta.get("docstring")
    params: Dict[str, str] = {}
    # Look for common schema layouts
    schema = meta.get("inputSchema") or meta.get("parameters") or {}
    props = schema.get("properties") if isinstance(schema, dict) else {}
    if isinstance(props, dict):
        for k, v in props.items():
            if isinstance(v, dict):
                params[k] = v.get("type", "string")
            else:
                params[k] = "string"
    # Fallback: args list
    for k in meta.get("args", []):
        params[k] = params.get(k, "string")
    return ToolSchema(name=name, description=description, parameters=params)


# Static fallback capability map when runtime discovery is unavailable
DEFAULT_CAPABILITIES: Dict[str, List[ToolSchema]] = {
    "arithmetic": [
        ToolSchema("add", parameters={"a": "number", "b": "number"}),
        ToolSchema("subtract", parameters={"a": "number", "b": "number"}),
        ToolSchema("multiply", parameters={"a": "number", "b": "number"}),
        ToolSchema("divide", parameters={"a": "number", "b": "number"}),
    ],
    "integration": [
        ToolSchema("integrate_indefinite", parameters={"expression": "string", "variable": "string"}),
        ToolSchema("integrate_definite", parameters={"expression": "string", "variable": "string", "lower": "string", "upper": "string"}),
    ],
    "differentiation": [
        ToolSchema("derivative", parameters={"expression": "string", "variable": "string", "order": "integer"}),
    ],
    "probability": [
        ToolSchema("complement", parameters={"p": "number"}),
        ToolSchema("union_independent", parameters={"p_a": "number", "p_b": "number"}),
        ToolSchema("intersection_independent", parameters={"p_a": "number", "p_b": "number"}),
        ToolSchema("conditional", parameters={"p_a_and_b": "number", "p_b": "number"}),
        ToolSchema("bayes", parameters={"p_a": "number", "p_b_given_a": "number", "p_b": "number"}),
    ],
    "venn": [
        ToolSchema("two_set_regions", parameters={"n_a": "integer", "n_b": "integer", "n_a_intersect_b": "integer"}),
        ToolSchema("three_set_regions", parameters={"n_a": "integer", "n_b": "integer", "n_c": "integer", "n_ab": "integer", "n_ac": "integer", "n_bc": "integer", "n_abc": "integer"}),
    ],
    "grammar": [
        ToolSchema("check_grammar", parameters={"text": "string", "use_languagetool": "boolean"}),
    ],
    "translate": [
        ToolSchema("translate_to_english", parameters={"text": "string", "source_language": "string"}),
        ToolSchema("translate_from_english", parameters={"text": "string", "target_language": "string"}),
    ],
    "botany": [
        ToolSchema("plant_summary", parameters={"name": "string", "sentences": "integer"}),
        ToolSchema("plant_taxonomy", parameters={"name": "string"}),
        ToolSchema("is_edible", parameters={"name": "string"}),
        ToolSchema("medicinal_uses", parameters={"name": "string"}),
        ToolSchema("leaf_area_index", parameters={"total_leaf_area_m2": "number", "ground_area_m2": "number"}),
        ToolSchema("photosynthesis_rate", parameters={"light_umol_m2_s": "number", "co2_ppm": "number", "temperature_c": "number"}),
        ToolSchema("transpiration_rate", parameters={"stomatal_conductance_mol_m2_s": "number", "vpd_kpa": "number"}),
        ToolSchema("growth_rate_logistic", parameters={"r_per_day": "number", "carrying_capacity": "number", "initial_biomass": "number", "days": "integer"}),
        ToolSchema("chlorophyll_index", parameters={"red_reflectance": "number", "nir_reflectance": "number"}),
        ToolSchema("classify_life_form", parameters={"height_m": "number"}),
        ToolSchema("seed_dispersal_methods", parameters={"name": "string"}),
        ToolSchema("drought_stress_index", parameters={"soil_moisture_vol_pct": "number", "wilting_point_vol_pct": "number", "field_capacity_vol_pct": "number"}),
    ],
    "zoology": [
        ToolSchema("animal_summary", parameters={"name": "string", "sentences": "integer"}),
        ToolSchema("animal_taxonomy", parameters={"name": "string"}),
        ToolSchema("basal_metabolic_rate", parameters={"body_mass_kg": "number"}),
        ToolSchema("field_of_view", parameters={"predator": "boolean"}),
        ToolSchema("max_running_speed", parameters={"body_mass_kg": "number"}),
        ToolSchema("daily_food_requirement", parameters={"body_mass_kg": "number", "trophic_level": "string"}),
        ToolSchema("thermal_comfort_index", parameters={"ambient_c": "number", "preferred_c": "number"}),
        ToolSchema("population_growth_rate", parameters={"r_per_year": "number", "n0": "number", "years": "integer"}),
        ToolSchema("predator_prey_equilibrium", parameters={"prey_growth": "number", "pred_efficiency": "number", "pred_death": "number", "encounter_rate": "number"}),
        ToolSchema("habitat_suitability", parameters={"temperature_c": "number", "rainfall_mm": "number"}),
        ToolSchema("lifespan_estimate", parameters={"body_mass_kg": "number"}),
        ToolSchema("classify_diet", parameters={"teeth_shape": "string"}),
    ],
     "youtube": [
        ToolSchema("refresh_token", parameters={}),
        ToolSchema("list_videos", parameters={}),
        ToolSchema("search_videos", parameters={"arguments": "dict"}),
        ToolSchema("upload_video", parameters={"arguments": "dict"}),
        ToolSchema("add_comment", parameters={"arguments": "dict"}),
        ToolSchema("reply_comment", parameters={"arguments": "dict"}),
        ToolSchema("get_video_comments", parameters={"arguments": "dict"}),
        ToolSchema("rate_video", parameters={"arguments": "dict"}),
        ToolSchema("video_analytics", parameters={"arguments": "dict"}),
        ToolSchema("channel_analytics", parameters={"channel_id": "string"}),
        ToolSchema("remove_video", parameters={"arguments": "dict"}),
    ],
    "tiktok": [
        ToolSchema("tiktok_get_subtitle", parameters={"tiktok_url": "string", "language_code": "string"}),
        ToolSchema("tiktok_get_post_details", parameters={"tiktok_url": "string"}),
        ToolSchema("tiktok_search", parameters={"query": "string", "cursor": "string", "search_uid": "string"}),
    ],
    "x": [
        ToolSchema("create_post", parameters={"a": "string"}),
        ToolSchema("delete_post", parameters={"a": "string"}),
        ToolSchema("get_post_by_id", parameters={"a": "string"}),
        ToolSchema("get_my_user_info", parameters={}),
        ToolSchema("get_all_post_of_user", parameters={"a": "string"}),
        ToolSchema("get_user_by_username", parameters={"a": "string"}),
        ToolSchema("follow_user", parameters={"a": "string", "b": "string"}),
        ToolSchema("unfollow_user", parameters={"a": "string", "b": "string"}),
        ToolSchema("recent_post_by_query", parameters={"a": "string"}),
        ToolSchema("like_post", parameters={"a": "string", "b": "string"}),
        ToolSchema("unlike_post", parameters={"a": "string", "b": "string"}),
        ToolSchema("get_liked_post_of_user", parameters={"a": "string"}),
        ToolSchema("recent_post_count_by_query", parameters={"a": "string"}),
    ],
}


async def build_capability_graph(server_scripts: Dict[str, str]) -> CapabilityGraph:
    logger = logging.getLogger("orchestrator")
    graph = CapabilityGraph()
    for server_key, script_path in server_scripts.items():
        # Backward-compatible: accept either a path string or a dict with command/args
        if isinstance(script_path, dict):
            command = script_path.get("command")
            args = script_path.get("args", [])
            env = script_path.get("env") if isinstance(script_path.get("env"), dict) else None
        else:
            command = sys.executable
            args = [script_path]
            env = None
        if not command:
            continue
        logger.info("discovering tools for server=%s command=%s args=%s", server_key, command, args)
        server_params = StdioServerParameters(command=command, args=args, env=env)
        tools_for_server: List[ToolSchema] = []
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    metas = await _fetch_tools_metadata(session)
                    for meta in metas:
                        schema = _coerce_schema(meta)
                        tools_for_server.append(schema)
                        logger.debug("discovered tool: %s.%s", server_key, schema.name)
                        graph.tools[f"{server_key}.{schema.name}"] = ToolSpec(
                            server_key=server_key,
                            tool_name=schema.name,
                            schema=schema,
                        )
        except Exception:
            # Keep discovery robust; skip servers that fail to start
            logger.exception("failed to discover tools for server=%s", server_key)
        # Fallback to defaults if discovery yielded nothing
        if not tools_for_server:
            if server_key in DEFAULT_CAPABILITIES:
                logger.info("using default capability catalog for server=%s", server_key)
                for schema in DEFAULT_CAPABILITIES[server_key]:
                    tools_for_server.append(schema)
                    graph.tools[f"{server_key}.{schema.name}"] = ToolSpec(
                        server_key=server_key,
                        tool_name=schema.name,
                        schema=schema,
                    )
            # Extra: if server key contains 'tiktok', use TikTok defaults
            elif "tiktok" in server_key.lower() and "tiktok" in DEFAULT_CAPABILITIES:
                logger.info("using TikTok default capability catalog for server=%s", server_key)
                for schema in DEFAULT_CAPABILITIES["tiktok"]:
                    tools_for_server.append(schema)
                    graph.tools[f"{server_key}.{schema.name}"] = ToolSpec(
                        server_key=server_key,
                        tool_name=schema.name,
                        schema=schema,
                    )

        graph.servers[server_key] = ServerSpec(
            key=server_key,
            command=command,
            args=args,
            env=env,
            tools=tools_for_server,
        )
    return graph


# ---------- Planner ----------


def simple_planner(master_question: str, graph: CapabilityGraph) -> Plan:
    logger = logging.getLogger("orchestrator")
    # Very simple heuristic planner:
    # - Choose 1–N tools based on keyword hints in the question and available tool names.
    q = master_question.lower()
    chosen: List[PlanStep] = []

    def add_first_match(hints: List[str], prefer: List[str] = [], args_hint: Dict[str, Any] = {}):
        for key, spec in graph.tools.items():
            hay = f"{spec.server_key}.{spec.tool_name}".lower()
            if any(h in hay or h in q for h in hints + prefer):
                chosen.append(PlanStep(
                    id=f"step_{len(chosen)+1}",
                    intent=f"{spec.tool_name} for {master_question}",
                    tool_key=key,
                    args_hint=args_hint.copy(),
                    depends_on=[],
                ))
                logger.info("planner selected tool=%s for intent='%s'", key, master_question)
                return

    # Examples: expand/replace to fit your domain
    # Heuristic integral parsing for args hints
    def _infer_integral_args(question: str) -> Dict[str, Any]:
        m = re.search(r"(?i)integrate\s+(.+?)\s+from\s+([^\s]+)\s+to\s+([^\s]+)", question.strip())
        if m:
            expr = m.group(1).strip()
            lower = m.group(2).strip()
            upper = m.group(3).strip()
            var = "x"
            if "x" in expr:
                var = "x"
            elif "t" in expr:
                var = "t"
            elif "y" in expr:
                var = "y"
            return {"expression": expr, "variable": var, "lower": lower, "upper": upper}
        # Indefinite fallback: try to capture expression after 'integrate'
        m2 = re.search(r"(?i)integrate\s+(.+)$", question.strip())
        expr = m2.group(1).strip() if m2 else "x"
        var = "x" if "x" in expr else ("t" if "t" in expr else "x")
        return {"expression": expr, "variable": var}

    if any(k in q for k in ["integral", "integrate", "area under"]):
        hints = _infer_integral_args(master_question)
        if {"expression", "variable", "lower", "upper"}.issubset(hints.keys()):
            add_first_match(["integration.integrate_definite"], args_hint=hints)
        else:
            add_first_match(["integration.integrate_indefinite", "integrate_indefinite"], args_hint=hints)
    if any(k in q for k in ["derivative", "differentiate", "slope"]):
        add_first_match(["differentiation.derivative"])
    if any(k in q for k in ["probability", "bayes", "conditional"]):
        add_first_match(["probability."])
    if any(k in q for k in ["venn"]):
        add_first_match(["venn."])
    if any(k in q for k in ["grammar", "proofread"]):
        add_first_match(["grammar.check_grammar"])
    if any(k in q for k in ["translate", "english"]):
        add_first_match(["translate."])
    # Heuristic for creating a post on X/Twitter
    if not chosen and any(k in q for k in ["twitter", " on x", " on twitter", "tweet", "create post", "create a post", "post on x", "post on twitter"]):
        # Try to infer the post text
        post_text = None
        m = re.search(r"(?i)post\s+(.+)$", master_question.strip())
        if m:
            post_text = m.group(1).strip()
        if not post_text:
            # Fallback: remove the leading command-like words
            post_text = re.sub(r"(?i)create\s+(a\s+)?(twitter|x)\s+post\s*", "", master_question).strip()
        args_hint = {"a": post_text} if post_text else {}
        if "x.create_post" in graph.tools:
            chosen.append(PlanStep(
                id=f"step_{len(chosen)+1}",
                intent=f"create post for {master_question}",
                tool_key="x.create_post",
                args_hint=args_hint,
                depends_on=[],
            ))
            logger.info("planner selected x.create_post via heuristic with args=%s", args_hint)
    # Heuristic for X/Twitter queries
    if not chosen and any(k in q for k in ["twitter", " on x", " on twitter", "tweets", "tweet", " x ", " x:", "@", "x user", "twitter user", "user details", "user info"]):
        # Try to extract an @username or a 'username <name>' phrase
        uname_match = re.search(r"@([A-Za-z0-9_]{1,15})", master_question)
        if not uname_match:
            uname_match = re.search(r"username\s+([A-Za-z0-9_]{1,15})", master_question, re.IGNORECASE)
        if uname_match and "x.get_user_by_username" in graph.tools:
            chosen.append(PlanStep(
                id=f"step_{len(chosen)+1}",
                intent=f"get user by username for {master_question}",
                tool_key="x.get_user_by_username",
                args_hint={"a": uname_match.group(1)},
                depends_on=[],
            ))
            logger.info("planner selected x.get_user_by_username via heuristic")
        elif "x.get_my_user_info" in graph.tools:
            chosen.append(PlanStep(
                id=f"step_{len(chosen)+1}",
                intent=f"get user info for {master_question}",
                tool_key="x.get_my_user_info",
                args_hint={},
                depends_on=[],
            ))
            logger.info("planner selected x.get_my_user_info via heuristic")
    # Heuristic for TikTok queries
    if not chosen and any(k in q for k in ["tiktok", "tik tok", "tt video", "tiktok video", "tiktok post", "tiktok search"]):
        # Choose specific tool by intent keywords
        if "subtitle" in q or "subtitles" in q:
            add_first_match(["tiktok.tiktok_get_subtitle"])
        elif any(k in q for k in ["detail", "details", "info", "information"]):
            add_first_match(["tiktok.tiktok_get_post_details"])
        elif any(k in q for k in ["search", "find", "videos", "posts"]):
            add_first_match(["tiktok.tiktok_search"])
        else:
            # default to search for generic tiktok queries
            add_first_match(["tiktok.tiktok_search"])
    # Heuristic for YouTube actions
    if not chosen:
        # Delete video intent
        if ("youtube" in q or "video" in q) and any(k in q for k in ["delete", "remove"]):
            vid_match = re.search(r"([A-Za-z0-9_-]{8,})", master_question)
            args_hint = {}
            if vid_match:
                args_hint = {"arguments": {"video_id": vid_match.group(1)}}
            key = "youtube.remove_video"
            if key in graph.tools:
                chosen.append(PlanStep(
                    id=f"step_{len(chosen)+1}",
                    intent=f"remove video for {master_question}",
                    tool_key=key,
                    args_hint=args_hint,
                    depends_on=[],
                ))
                logger.info("planner selected youtube.remove_video via heuristic with args=%s", args_hint)
        # Upload video intent (only if explicit upload or file path present)
        elif ("upload" in q or re.search(r"[a-zA-Z]:\\\\[^\n\r]+?\.(mp4|mov|mkv|avi)", master_question) is not None):
            file_match = re.search(r"([a-zA-Z]:\\[^\n\r]+?\.(mp4|mov|mkv|avi))", master_question)
            title_match = re.search(r"(?:named|title is|title)\s+\"?([^\"\n\r]+)\"?", master_question, re.IGNORECASE)
            args_hint: Dict[str, Any] = {}
            if file_match:
                args_hint["arguments"] = {"file": file_match.group(1)}
            if title_match:
                if "arguments" not in args_hint:
                    args_hint["arguments"] = {}
                args_hint["arguments"]["title"] = title_match.group(1).strip()
            key = "youtube.upload_video"
            if key in graph.tools:
                chosen.append(PlanStep(
                    id=f"step_{len(chosen)+1}",
                    intent=f"upload video for {master_question}",
                    tool_key=key,
                    args_hint=args_hint,
                    depends_on=[],
                ))
                logger.info("planner selected youtube.upload_video via heuristic with args=%s", args_hint)

    if not chosen:
        # Fallback: pick the first tool in the graph
        if graph.tools:
            first_key = next(iter(graph.tools))
            spec = graph.tools[first_key]
            chosen.append(PlanStep(
                id="step_1",
                intent=f"{spec.tool_name} for {master_question}",
                tool_key=first_key,
            ))
            logger.info("planner fallback selected tool=%s", first_key)
    return Plan(steps=chosen)


def format_plan(plan: Plan) -> str:
    lines: List[str] = []
    for step in plan.steps:
        lines.append(f"- {step.id}: {step.tool_key} :: intent='{step.intent}' deps={step.depends_on}")
    return "\n".join(lines)


def format_plan_diagram(plan: Plan) -> str:
    if not plan.steps:
        return "(no steps)"
    # Simple top-to-bottom diagram
    parts: List[str] = []
    for idx, step in enumerate(plan.steps, start=1):
        parts.append(f"[{idx}] {step.id} :: {step.tool_key}")
        if idx < len(plan.steps):
            parts.append("  |\n  v")
    return "\n".join(parts)


# ---------- Static capability graph (no runtime discovery) ----------


def build_capability_graph_static(server_scripts: Dict[str, Any]) -> CapabilityGraph:
    logger = logging.getLogger("orchestrator")
    graph = CapabilityGraph()
    logger.info("using static capability catalog; no runtime discovery")
    for server_key, script_path in server_scripts.items():
        tools_for_server: List[ToolSchema] = []
        for schema in DEFAULT_CAPABILITIES.get(server_key, []):
            tools_for_server.append(schema)
            graph.tools[f"{server_key}.{schema.name}"] = ToolSpec(
                server_key=server_key,
                tool_name=schema.name,
                schema=schema,
            )
        if isinstance(script_path, dict):
            command = script_path.get("command")
            args = script_path.get("args", [])
            env = script_path.get("env") if isinstance(script_path.get("env"), dict) else None
        else:
            command = sys.executable
            args = [script_path]
            env = None
        graph.servers[server_key] = ServerSpec(
            key=server_key,
            command=command or sys.executable,
            args=args,
            env=env,
            tools=tools_for_server,
        )
    return graph


# ---------- LLM-based Planner ----------


def _tools_catalog_for_prompt(graph: CapabilityGraph) -> str:
    lines: List[str] = []
    for key, spec in graph.tools.items():
        params = ", ".join(f"{k}:{v}" for k, v in spec.schema.parameters.items())
        lines.append(f"- {key}({params})")
    return "\n".join(lines)

def deepseek_api_call(system_prompt, user_prompt):
    
    url = "http://52.20.185.4:8006/v1/chat/completions"

    payload = {
        "messages": [
            {
                "content": system_prompt,
                "role": "system"
            },
            {
                "content": user_prompt,
                "role": "user"
            }
        ],
        # "model": "gpt-4o-mini",
        "tool_choice": "none",
        "stream": False
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print('deepseek resp ---------- ',response , response.text)
    response = response.json()
    
    return response

def safe_load_plan(content: str) -> Dict[str, Any]:
    """
    Parse LLM JSON output and always return a dict.
    If the content is not a dict, return an empty dict.
    """
    # Attempt direct parse first
    try:
        data = json.loads(content or "{}")
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"steps": data}
        if isinstance(data, str):
            try:
                nested = json.loads(data)
                if isinstance(nested, dict):
                    return nested
                if isinstance(nested, list):
                    return {"steps": nested}
            except Exception:
                pass
    except Exception:
        pass

    # Strip Markdown code fences if present
    try:
        text = content.strip()
        if text.startswith("```"):
            # remove opening fence with optional language tag
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1 :]
            if text.endswith("```"):
                text = text[: -3]
        text = text.strip()
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"steps": data}
    except Exception:
        pass

    # Fallback: extract the largest JSON object substring
    try:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = content[start : end + 1]
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        # Also try list brackets
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = content[start : end + 1]
            data = json.loads(snippet)
            if isinstance(data, list):
                return {"steps": data}
    except Exception:
        pass

    # Last resort: handle multiple JSON objects concatenated; parse and merge
    try:
        merged: Dict[str, Any] = {}
        # Normalize adjacent objects like '}{' to parse separately
        normalized = re.sub(r"}\s*{", "}\n{", content.strip())
        for part in re.split(r"\n+", normalized):
            p = part.strip()
            if not p:
                continue
            try:
                obj = json.loads(p)
                if isinstance(obj, dict):
                    merged.update(obj)
                elif isinstance(obj, list):
                    merged.update({"steps": obj})
            except Exception:
                continue
        if merged:
            return merged
    except Exception:
        pass

        return {}

async def llm_planner(master_question: str, graph: CapabilityGraph, model: str) -> Plan:
    logger = logging.getLogger("orchestrator")
    client = ensure_openai_client()
    catalog = _tools_catalog_for_prompt(graph)
    system = (
        "You are a precise planning agent that decomposes a master question into a minimal set of tool calls. "
        "Return ONLY JSON with a 'steps' array. Each step has: id, tool_key, intent, args_hint (object), depends_on (array of ids). "
        "Use correct tool directionality. If translating from English to another language, use translate.translate_from_english with target_language ISO code. "
        "Language codes: tamil=ta, spanish=es, french=fr, german=de, hindi=hi, chinese=zh, japanese=ja, korean=ko, arabic=ar, russian=ru, portuguese=pt, italian=it. "
        "Prefer sequential dependencies where later steps need outputs from earlier steps. Keep steps minimal. "
        "Routing rule: If the question mentions TikTok (tiktok, tik tok), you MUST select a tiktok.* tool (not translate.*)."
    )
    user = (
        f"Master question: {master_question}\n\n"
        f"Available tools:\n{catalog}\n\n"
        "Plan now."
    )
    # resp = client.chat.completions.create(
    #     model=model,
    #     messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    #     temperature=0,
    #     response_format={"type": "json_object"},
    # )
    resp = deepseek_api_call(system, user)
    plan_json: Dict[str, Any]
    try:
        # plan_json = json.loads(resp.choices[0].message.content or "{}")
        content = resp["choices"][0]["message"]["content"]
        print('llm planner Content: ', content , type(content))
        plan_json = safe_load_plan(content)
    except Exception:
        logger.exception("planner LLM returned invalid JSON; falling back to simple planner")
        return simple_planner(master_question, graph)
    steps_in: List[Dict[str, Any]] = list(plan_json.get("steps", []))
    steps: List[PlanStep] = []
    # Known alias mappings from LLM outputs to actual tool keys in our graph
    alias_map: Dict[str, str] = {
        "tiktok.search_videos": "tiktok.tiktok_search",
        "tiktok.get_post_details": "tiktok.tiktok_get_post_details",
        "tiktok.get_subtitle": "tiktok.tiktok_get_subtitle",
    }
    for idx, s in enumerate(steps_in, start=1):
        tool_key = str(s.get("tool_key", "")).strip()
        # Normalize aliases
        tool_key = alias_map.get(tool_key, tool_key)
        # If TikTok tool_key not found, try resolve by suffix across any TikTok-like server key
        if tool_key not in graph.tools and ".tiktok_" in tool_key:
            suffix = tool_key.split(".", 1)[1]
            for k in graph.tools.keys():
                sk, tn = k.split(".", 1)
                if tn == suffix and ("tiktok" in sk.lower()):
                    tool_key = k
                    break
        if tool_key not in graph.tools:
            # Skip invalid tools
            logger.warning("planner proposed unknown tool: %s", tool_key)
            continue
        steps.append(PlanStep(
            id=str(s.get("id") or f"step_{idx}"),
            intent=str(s.get("intent") or f"Run {tool_key}"),
            tool_key=tool_key,
            args_hint=dict(s.get("args_hint") or {}),
            depends_on=list(s.get("depends_on") or []),
        ))
    if not steps:
        return simple_planner(master_question, graph)
    return Plan(steps=steps)


# ---------- Question Generator ----------


def ensure_openai_client():
    logger = logging.getLogger("orchestrator")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    from openai import OpenAI  # type: ignore
    logger.debug("created OpenAI client")
    return OpenAI()


async def generate_tool_args_with_llm(
    client, model: str, master_question: str, step: PlanStep, spec: ToolSpec
) -> Dict[str, Any]:
    logger = logging.getLogger("orchestrator")
    # Prompt LLM to produce a JSON object with only the needed arguments.
    schema_lines = [f"- {k}: {v}" for k, v in spec.schema.parameters.items()]

    # If the tool requires no arguments, return an empty object immediately
    if not spec.schema.parameters:
        logger.info("%s.%s requires no arguments; returning {}", spec.server_key, spec.tool_name)
        return {}

    # Enrich schema hints for tools that accept a single 'arguments' dict with inner required keys
    if spec.server_key == "youtube":
        youtube_arg_hints: Dict[str, str] = {
            "search_videos": "arguments: object { query: string }",
            "upload_video": "arguments: object { file: string (path to video), title: string, description?: string, tags?: array[string], categoryId?: string, privacyStatus?: string }",
            "add_comment": "arguments: object { video_id: string, text: string }",
            "reply_comment": "arguments: object { comment_id: string, text: string }",
            "get_video_comments": "arguments: object { video_id: string, max_results?: integer }",
            "rate_video": "arguments: object { video_id: string, rating: string (like|dislike|none) }",
            "video_analytics": "arguments: object { video_id: string }",
            "remove_video": "arguments: object { video_id: string }",
        }
        hint = youtube_arg_hints.get(spec.tool_name)
        if hint:
            schema_lines = [f"- {hint}"]

    system = (
        "You are a tool argument generator. Produce ONLY a JSON object with the exact argument keys required. "
        "If the tool signature includes 'arguments: dict/object', then return an 'arguments' JSON object containing ONLY the required inner fields. "
        "Do NOT include optional fields unless they are explicitly specified in the master question or sub-intent. "
        "If the tool requires no arguments, return an empty JSON object: {}. "
        "When tool is translate.translate_from_english, use ISO codes (e.g., 'ta' for Tamil) for target_language."
    )
    user = (
        f"Master question: {master_question}\n"
        f"Sub-intent: {step.intent}\n"
        f"Target tool: {spec.server_key}.{spec.tool_name}\n"
        f"Arguments schema:\n" + "\n".join(schema_lines)
    )
    print('user: ', user, type(user))
    # resp = client.chat.completions.create(
    #     model=model,
    #     messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    #     temperature=0,
    #     response_format={"type": "json_object"},
    # )
    # print('openai resp: ', resp, type(resp))
    resp = deepseek_api_call(system, user)

    try:
        logger.info("generated args for %s.%s", spec.server_key, spec.tool_name)
        content = resp["choices"][0]["message"]["content"]
        print('generate_tool_args_with_llm Content: ', content , type(content))
        parsed = safe_load_plan(content)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except Exception:
        logger.exception("failed to parse generated args for %s.%s", spec.server_key, spec.tool_name)
        return {}


# ---------- Orchestrator ----------


async def _call_tool(server_key: str, server: ServerSpec, tool_name: str, args: Dict[str, Any]) -> str:
    logger = logging.getLogger("orchestrator")
    server_params = StdioServerParameters(command=server.command, args=server.args, env=server.env)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("executing tool %s.%s with args=%s", server_key, tool_name, args)
            result = await session.call_tool(name=tool_name, arguments=args)
            # Extract text/json similar to your existing client
            content_items = getattr(result, "content", []) or []
            for item in content_items:
                if getattr(item, "text", None) is not None:
                    return item.text
            for item in content_items:
                data = getattr(item, "json", None)
                if data is not None:
                    try:
                        return json.dumps(data, ensure_ascii=False)
                    except Exception:
                        pass
            return str(content_items[0]) if content_items else str(result)


async def orchestrate(
    graph: CapabilityGraph,
    plan: Plan,
    master_question: str,
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    timeout_s: float = 20.0,
    max_retries: int = 1,
) -> Dict[str, Any]:
    logger = logging.getLogger("orchestrator")
    client = ensure_openai_client()
    logger.info("execution plan:\n%s", format_plan(plan))
    logger.info("plan diagram:\n%s", format_plan_diagram(plan))
    pending = {s.id: s for s in plan.steps}
    deps: Dict[str, List[str]] = {s.id: list(s.depends_on) for s in plan.steps}

    async def run_step(step: PlanStep) -> Tuple[str, Any]:
        spec = graph.tools[step.tool_key]
        # Generate args
        args = await generate_tool_args_with_llm(client, llm_model, master_question, step, spec)
        print('run_step args: ', args, type(args))
        # Simple dep interpolation: replace ${STEP_X_OUTPUT}
        # Normalize string or object-like returns into dict
        try:
            if isinstance(args, str):
                args = safe_load_plan(args) or {}
            args = args.arguments if hasattr(args, "arguments") else args
            if not isinstance(args, dict):
                args = {}
        except Exception as exc:
            logger.error("failed to parse args for step %s: %s", step.id, exc)
            args = {}
        
        for k, v in list(args.items()):
            if isinstance(v, str) and "${STEP_" in v:
                for sid, out_val in results.items():
                    placeholder = f"${{{sid}_OUTPUT}}"
                    if placeholder in v:
                        args[k] = v.replace(placeholder, str(out_val))
        # Merge with any planner hints without overwriting LLM-generated args
        if isinstance(step.args_hint, dict):
            for hk, hv in step.args_hint.items():
                if hk == "arguments" and isinstance(hv, dict):
                    existing = args.get("arguments")
                    if not isinstance(existing, dict):
                        args["arguments"] = dict(hv)
                    else:
                        for ak, av in hv.items():
                            if ak not in existing:
                                existing[ak] = av
                else:
                    if hk not in args:
                        args[hk] = hv

        # Flatten nested 'arguments' dict when spec expects top-level params (e.g., TikTok tools)
        if isinstance(args.get("arguments"), dict):
            nested = args["arguments"]
            if isinstance(nested, dict):
                for expected_key in spec.schema.parameters.keys():
                    if expected_key not in args and expected_key in nested:
                        args[expected_key] = nested[expected_key]
                # Remove nested after flattening to avoid confusion
                args.pop("arguments", None)

        # As a final fallback, fill any missing expected keys from step hints (top-level or inside 'arguments')
        if isinstance(step.args_hint, dict):
            hint_args = step.args_hint
            hint_nested = hint_args.get("arguments") if isinstance(hint_args.get("arguments"), dict) else {}
            for expected_key in spec.schema.parameters.keys():
                if expected_key not in args:
                    if expected_key in hint_args:
                        args[expected_key] = hint_args[expected_key]
                    elif expected_key in hint_nested:
                        args[expected_key] = hint_nested[expected_key]

        # Special-case fallback: ensure X post text is populated under the correct key
        if spec.server_key == "x" and spec.tool_name == "create_post":
            text_val = ""
            if isinstance(args.get("arguments"), dict):
                text_val = str(args["arguments"].get("a", args["arguments"].get("text", ""))).strip()
            if not text_val:
                text_val = str(args.get("a", args.get("text", ""))).strip()
            if not text_val:
                # Try to infer from the master question
                m = re.search(r"(?i)post\s+(.+)$", master_question.strip())
                if m:
                    text_val = m.group(1).strip()
                if not text_val:
                    text_val = re.sub(r"(?i)^\s*create\s+(a\s+)?(twitter|x)\s+post\s*", "", master_question).strip()
            if text_val:
                # Normalize to expected param name 'a' and drop nested forms
                args["a"] = text_val
                if isinstance(args.get("arguments"), dict):
                    args.pop("arguments", None)

        # Retries + timeout + guardrails for args
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= max_retries:
            try:
                # Basic guardrails: drop clearly wrong args based on schema types
                cleaned_args: Dict[str, Any] = {}
                for key, expected in spec.schema.parameters.items():
                    if key not in args:
                        continue
                    val = args[key]
                    t = str(expected).lower()
                    try:
                        if t in ("number", "float"):
                            cleaned_args[key] = float(val)
                        elif t in ("integer", "int"):
                            cleaned_args[key] = int(val)
                        elif t in ("boolean", "bool"):
                            if isinstance(val, bool):
                                cleaned_args[key] = val
                            else:
                                s = str(val).strip().lower()
                                cleaned_args[key] = s in {"true", "1", "yes", "y"}
                        elif t in ("dict", "object", "map", "json"):
                            # Preserve dictionaries as-is; attempt to parse JSON strings
                            if isinstance(val, dict):
                                cleaned_args[key] = val
                            else:
                                try:
                                    parsed = json.loads(val)
                                    if isinstance(parsed, dict):
                                        cleaned_args[key] = parsed
                                    else:
                                        # Fallback: pass through original value
                                        cleaned_args[key] = val
                                except Exception:
                                    cleaned_args[key] = val
                        else:
                            cleaned_args[key] = str(val)
                    except Exception:
                        logger.warning("dropping invalid arg %s=%r for tool %s (expected %s)", key, val, step.tool_key, expected)
                logger.debug("final args for %s: %s", step.tool_key, cleaned_args)
                # Prune empty optional fields inside nested 'arguments' dict for youtube-like tools
                if spec.server_key == "youtube" and isinstance(cleaned_args.get("arguments"), dict):
                    pruned: Dict[str, Any] = {}
                    for k, v in cleaned_args["arguments"].items():
                        if v is None:
                            continue
                        if isinstance(v, str) and v.strip() == "":
                            continue
                        if isinstance(v, (list, dict)) and not v:
                            continue
                        pruned[k] = v
                    cleaned_args["arguments"] = pruned
                return step.id, await asyncio.wait_for(
                    _call_tool(spec.server_key, graph.servers[spec.server_key], spec.tool_name, cleaned_args),
                    timeout=timeout_s,
                )
            except Exception as exc:
                last_exc = exc
                attempt += 1
        logger.error("tool %s failed after %d attempts: %s", step.tool_key, max_retries + 1, last_exc)
        return step.id, f"ERROR: {last_exc}"

    results: Dict[str, Any] = {}

    # Simple dep scheduler: run any step whose deps satisfied; parallelize ready sets
    while pending:
        ready = [s for s in list(pending.values()) if all(d in results for d in deps.get(s.id, []))]
        if not ready:
            # Deadlock or missing deps; break
            break
        logger.info("orchestrator running %d ready step(s) in parallel %s", len(ready) , ready)
        tasks = [asyncio.create_task(run_step(s)) for s in ready]
        for s in ready:
            pending.pop(s.id, None)
        pairs = await asyncio.gather(*tasks, return_exceptions=False)
        for sid, out in pairs:
            results[sid] = out

    # Order summary by plan step order
    ordered = [results[s.id] for s in plan.steps if s.id in results]
    return {"steps": results, "summary": "\n\n".join(str(v) for v in ordered)}


# ---------- Reflector (optional) ----------


def needs_follow_up(results: Dict[str, Any]) -> bool:
    # Extremely simple heuristic; replace with LLM-based reflection
    text = " ".join(str(v) for v in results.values()).lower()
    return any(k in text for k in ["error", "failed", "unknown", "could not"])


async def reflect_and_fill(
    graph: CapabilityGraph,
    master_question: str,
    previous: Dict[str, Any],
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
) -> Dict[str, Any]:
    logger = logging.getLogger("orchestrator")
    if not needs_follow_up(previous.get("steps", {})):
        return previous
    # Example follow-up: re-run first step with relaxed constraints.
    # In practice: ask LLM to propose follow-up sub-intents.
    logger.info("reflector decided no follow-up implemented; returning previous results")
    return previous


# ---------- Entry point to use from mcp_client.py ----------


async def answer_master_question(
    master_question: str,
    server_scripts: Dict[str, str],
    llm_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
) -> str:
    logger = logging.getLogger("orchestrator")
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    # Speed & determinism: use static graph first, avoid runtime discovery
    logger.info("building capability graph (static)")
    graph = build_capability_graph_static(server_scripts)
    logger.info("planning steps for question: %s", master_question)
    # Use LLM-based planner first; fall back to simple heuristic if needed
    try:
        plan = await llm_planner(master_question, graph, model=llm_model)
    except Exception:
        logger.exception("LLM planner failed; using simple planner")
        plan = simple_planner(master_question, graph)

    # Sanitize plan: remove explicit YouTube refresh steps (tools auto-refresh on 401)
    try:
        removed_ids = {s.id for s in plan.steps if s.tool_key == "youtube.refresh_token"}
        if removed_ids:
            logger.info("sanitizing plan: removing youtube.refresh_token steps %s", removed_ids)
            kept_steps: List[PlanStep] = []
            for s in plan.steps:
                if s.id in removed_ids:
                    continue
                # Drop dependencies on removed steps
                s.depends_on = [d for d in s.depends_on if d not in removed_ids]
                kept_steps.append(s)
            plan = Plan(steps=kept_steps)
    except Exception:
        logger.exception("failed to sanitize plan; continuing with original plan")

    # If query mentions TikTok but plan contains no valid tiktok.* step, inject a tiktok search step and drop translate.*
    try:
        qlower = master_question.lower()
        has_valid_tiktok = any(s.tool_key.startswith("tiktok.") and s.tool_key in graph.tools for s in plan.steps)
        if any(k in qlower for k in ["tiktok", "tik tok"]) and not has_valid_tiktok:
            logger.info("sanitizing plan: enforcing TikTok tool for TikTok query")
            # Remove translate steps if present
            plan = Plan(steps=[s for s in plan.steps if not s.tool_key.startswith("translate.")])
            # Prefer search as generic default; find available tiktok_search tool
            search_key = None
            if "tiktok.tiktok_search" in graph.tools:
                search_key = "tiktok.tiktok_search"
            else:
                for k in graph.tools.keys():
                    sk, tn = k.split(".", 1)
                    if tn == "tiktok_search" and ("tiktok" in sk.lower()):
                        search_key = k
                        break
            if search_key:
                plan.steps.insert(0, PlanStep(
                    id="step_1",
                    intent=f"search tiktok for {master_question}",
                    tool_key=search_key,
                    args_hint={"query": master_question},
                    depends_on=[],
                ))
    except Exception:
        logger.exception("failed to enforce TikTok tool; continuing with original plan")
    # If translation target language is linguistically mentioned, enforce correct tool and args
    qlower = master_question.lower()
    lang_map = {"tamil": "ta", "spanish": "es", "french": "fr", "german": "de", "hindi": "hi", "chinese": "zh", "japanese": "ja", "korean": "ko", "arabic": "ar", "russian": "ru", "portuguese": "pt", "italian": "it"}
    target_detected: Optional[str] = None
    for name, code in lang_map.items():
        if f"to {name}" in qlower or f"to {code}" in qlower:
            target_detected = code
            break
    if target_detected:
        steps = [s for s in plan.steps if not s.tool_key.startswith("translate.translate_to_english")]
        # Ensure integration/first computational step is first, then translation-from-English second
        first_id = steps[0].id if steps else "step_1"
        steps.append(PlanStep(
            id=f"step_{len(steps)+1}",
            intent=f"Translate result to {target_detected}",
            tool_key="translate.translate_from_english",
            args_hint={"target_language": target_detected, "text": f"${{{first_id}_OUTPUT}}"},
            depends_on=[first_id],
        ))
        plan = Plan(steps=steps)
    logger.info("orchestrating %d step(s)", len(plan.steps))
    results = await orchestrate(graph, plan, master_question, llm_model=llm_model)
    logger.info("reflection phase (optional)")
    reflected = await reflect_and_fill(graph, master_question, results, llm_model=llm_model)
    return reflected.get("summary", "")


