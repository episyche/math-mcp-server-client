from __future__ import annotations

import asyncio
import json
import os
import sys
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

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
    script_path: str
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
}


async def build_capability_graph(server_scripts: Dict[str, str]) -> CapabilityGraph:
    logger = logging.getLogger("orchestrator")
    graph = CapabilityGraph()
    for server_key, script_path in server_scripts.items():
        if not os.path.exists(script_path):
            continue
        logger.info("discovering tools for server=%s script=%s", server_key, script_path)
        server_params = StdioServerParameters(command=sys.executable, args=[script_path], env=None)
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
        if not tools_for_server and server_key in DEFAULT_CAPABILITIES:
            logger.info("using default capability catalog for server=%s", server_key)
            for schema in DEFAULT_CAPABILITIES[server_key]:
                tools_for_server.append(schema)
                graph.tools[f"{server_key}.{schema.name}"] = ToolSpec(
                    server_key=server_key,
                    tool_name=schema.name,
                    schema=schema,
                )

        graph.servers[server_key] = ServerSpec(
            key=server_key,
            script_path=script_path,
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


def build_capability_graph_static(server_scripts: Dict[str, str]) -> CapabilityGraph:
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
        graph.servers[server_key] = ServerSpec(
            key=server_key,
            script_path=script_path,
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


async def llm_planner(master_question: str, graph: CapabilityGraph, model: str) -> Plan:
    logger = logging.getLogger("orchestrator")
    client = ensure_openai_client()
    catalog = _tools_catalog_for_prompt(graph)
    system = (
        "You are a precise planning agent that decomposes a master question into a minimal set of tool calls. "
        "Return ONLY JSON with a 'steps' array. Each step has: id, tool_key, intent, args_hint (object), depends_on (array of ids). "
        "Use correct tool directionality. If translating from English to another language, use translate.translate_from_english with target_language ISO code. "
        "Language codes: tamil=ta, spanish=es, french=fr, german=de, hindi=hi, chinese=zh, japanese=ja, korean=ko, arabic=ar, russian=ru, portuguese=pt, italian=it. "
        "Prefer sequential dependencies where later steps need outputs from earlier steps. Keep steps minimal."
    )
    user = (
        f"Master question: {master_question}\n\n"
        f"Available tools:\n{catalog}\n\n"
        "Plan now."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    plan_json: Dict[str, Any]
    try:
        plan_json = json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        logger.exception("planner LLM returned invalid JSON; falling back to simple planner")
        return simple_planner(master_question, graph)
    steps_in: List[Dict[str, Any]] = list(plan_json.get("steps", []))
    steps: List[PlanStep] = []
    for idx, s in enumerate(steps_in, start=1):
        tool_key = str(s.get("tool_key", "")).strip()
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
    system = (
        "You are a tool argument generator. Produce ONLY a JSON object with the exact argument keys required. "
        "When tool is translate.translate_from_english, use ISO codes (e.g., 'ta' for Tamil) for target_language."
    )
    user = (
        f"Master question: {master_question}\n"
        f"Sub-intent: {step.intent}\n"
        f"Target tool: {spec.server_key}.{spec.tool_name}\n"
        f"Arguments schema:\n" + "\n".join(schema_lines)
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    try:
        logger.info("generated args for %s.%s", spec.server_key, spec.tool_name)
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception:
        logger.exception("failed to parse generated args for %s.%s", spec.server_key, spec.tool_name)
        return {}


# ---------- Orchestrator ----------


async def _call_tool(server_key: str, script_path: str, tool_name: str, args: Dict[str, Any]) -> str:
    logger = logging.getLogger("orchestrator")
    server_params = StdioServerParameters(command=sys.executable, args=[script_path], env=None)
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
        # Simple dep interpolation: replace ${STEP_X_OUTPUT}
        for k, v in list(args.items()):
            if isinstance(v, str) and "${STEP_" in v:
                for sid, out_val in results.items():
                    placeholder = f"${{{sid}_OUTPUT}}"
                    if placeholder in v:
                        args[k] = v.replace(placeholder, str(out_val))
        # Merge with any planner hints (hints override LLM-generated args)
        args.update(step.args_hint)

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
                        else:
                            cleaned_args[key] = str(val)
                    except Exception:
                        logger.warning("dropping invalid arg %s=%r for tool %s (expected %s)", key, val, step.tool_key, expected)
                logger.debug("final args for %s: %s", step.tool_key, cleaned_args)
                return step.id, await asyncio.wait_for(
                    _call_tool(spec.server_key, graph.servers[spec.server_key].script_path, spec.tool_name, cleaned_args),
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
        logger.info("orchestrator running %d ready step(s) in parallel", len(ready))
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


