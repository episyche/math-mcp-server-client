import asyncio
import argparse
import json
import os
import sys
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
logger = logging.getLogger("mcp_client")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)



def get_available_server_scripts() -> dict[str, str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return {
        "arithmetic": os.path.join(current_dir, "maths_mcp_server", "arithmetic_mcp_server.py"),
        "integration": os.path.join(current_dir, "maths_mcp_server", "integration_mcp_server.py"),
        "differentiation": os.path.join(current_dir, "maths_mcp_server", "differentiation_mcp_server.py"),
        "probability": os.path.join(current_dir, "maths_mcp_server", "probability_mcp_server.py"),
        "venn": os.path.join(current_dir, "maths_mcp_server", "venn_mcp_server.py"),
        "grammar": os.path.join(current_dir, "english_mcp_server", "grammar_mcp_server.py"),
        "translate": os.path.join(current_dir, "english_mcp_server", "translate_mcp_server.py"),
        "botany": os.path.join(current_dir, "biology_mcp_server", "botany_mcp_server.py"),
        "zoology": os.path.join(current_dir, "biology_mcp_server", "zoology_mcp_server.py"),
    }


async def call_tool(session: ClientSession, name: str, **arguments) -> str:
    try:
        result = await session.call_tool(name=name, arguments=arguments)
    except Exception as exc:
        return f"Tool call failed: {exc}"

    try:
        content_items = getattr(result, "content", []) or []
        if not content_items:
            return str(result)

        # Prefer text content if available
        for item in content_items:
            text = getattr(item, "text", None)
            if text is not None:
                return text

        # Fallback: try JSON-like payloads
        for item in content_items:
            data = getattr(item, "json", None)
            if data is not None:
                try:
                    return json.dumps(data, ensure_ascii=False)
                except Exception:
                    pass

        # Last resort: stringify the first content item
        return str(content_items[0])
    except Exception as exc:
        return f"Could not parse tool result: {exc}"


def ensure_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Export OPENAI_API_KEY.")
    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "OpenAI SDK not installed. Install 'openai' or run 'pip install -r requirements.txt'."
        ) from exc
    return OpenAI()


def llm_route_task(question: str, model: str | None = None) -> tuple[str | None, str | None, dict | None]:
    client = ensure_openai_client()
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    system_prompt = (
        "You route math queries to MCP servers and tools. "
        "Choose exactly one server and one tool and return arguments. "
        "Servers and tools:\n"
        "- arithmetic: add(a,b), subtract(a,b), multiply(a,b), divide(a,b)\n"
        "- integration: integrate_indefinite(expression, variable), integrate_definite(expression, variable, lower, upper)\n"
        "- differentiation: derivative(expression, variable, order)\n"
        "- probability: complement(p), union_independent(p_a, p_b), intersection_independent(p_a, p_b), conditional(p_a_and_b, p_b), bayes(p_a, p_b_given_a, p_b)\n"
        "- venn: two_set_regions(n_a, n_b, n_a_intersect_b), three_set_regions(n_a, n_b, n_c, n_ab, n_ac, n_bc, n_abc)\n"
        "- grammar: check_grammar(text, use_languagetool=True)\n"
        "- translate: translate_to_english(text, source_language=None), translate_from_english(text, target_language)\n"
        "- botany: plant_summary(name, sentences=3), plant_taxonomy(name), is_edible(name), medicinal_uses(name), leaf_area_index(total_leaf_area_m2, ground_area_m2), photosynthesis_rate(light_umol_m2_s, co2_ppm, temperature_c), transpiration_rate(stomatal_conductance_mol_m2_s, vpd_kpa), growth_rate_logistic(r_per_day, carrying_capacity, initial_biomass, days), chlorophyll_index(red_reflectance, nir_reflectance), classify_life_form(height_m), seed_dispersal_methods(name), drought_stress_index(soil_moisture_vol_pct, wilting_point_vol_pct=10.0, field_capacity_vol_pct=35.0)\n"
        "- zoology: animal_summary(name, sentences=3), animal_taxonomy(name), basal_metabolic_rate(body_mass_kg), field_of_view(predator), max_running_speed(body_mass_kg), daily_food_requirement(body_mass_kg, trophic_level='omnivore'), thermal_comfort_index(ambient_c, preferred_c), population_growth_rate(r_per_year, n0, years), predator_prey_equilibrium(prey_growth, pred_efficiency, pred_death, encounter_rate), habitat_suitability(temperature_c, rainfall_mm), lifespan_estimate(body_mass_kg), classify_diet(teeth_shape)\n"
        "Rules: Return ONLY JSON with keys server, tool, arguments. "
        "Use numbers for numeric fields. Use strings for expressions/variables/bounds. "
        "Use JSON booleans for boolean fields (e.g., predator: true for predator, false for prey). "
        "Prefer Pythonic exponent '**' in expressions. If the query mentions 'from A to B', use definite integral with lower=A, upper=B."
    )

    user_prompt = f"Question: {question}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        server = str(data.get("server")) if data.get("server") is not None else None
        tool = str(data.get("tool")) if data.get("tool") is not None else None
        arguments = data.get("arguments") if isinstance(data.get("arguments"), dict) else None
        return server, tool, arguments
    except Exception:
        return None, None, None


def _normalize_arguments(server: str, tool: str, args: dict) -> dict:
    # Cast types as expected by servers
    if server in ("arithmetic", "math"):
        return {"a": float(args.get("a")), "b": float(args.get("b"))}
    if server == "integration":
        if tool == "integrate_indefinite":
            return {"expression": str(args.get("expression")), "variable": str(args.get("variable"))}
        if tool == "integrate_definite":
            return {
                "expression": str(args.get("expression")),
                "variable": str(args.get("variable")),
                "lower": str(args.get("lower")),
                "upper": str(args.get("upper")),
            }
    if server == "differentiation":
        order_val = args.get("order", 1)
        try:
            order_int = int(order_val)
        except Exception:
            order_int = 1
        return {
            "expression": str(args.get("expression")),
            "variable": str(args.get("variable")),
            "order": order_int,
        }
    if server == "probability":
        # Convert any present numeric args to float
        normalized = {}
        for key, value in args.items():
            try:
                normalized[key] = float(value)
            except Exception:
                normalized[key] = value
        return normalized
    if server == "venn":
        # Convert any present numeric args to int
        normalized = {}
        for key, value in args.items():
            try:
                normalized[key] = int(value)
            except Exception:
                normalized[key] = value
        return normalized
    if server in ("grammar", "translate"):
        # Pass-through for English utilities
        return args
    if server == "zoology":
        # Per-tool casting for zoology
        def _to_bool(value: object) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            s = str(value).strip().lower()
            if s in {"true", "yes", "y", "1", "predator"}:
                return True
            if s in {"false", "no", "n", "0", "prey"}:
                return False
            # default: False to avoid validation error on random strings
            return False

        tool_name = tool
        # Cast common numeric fields generically when present
        numeric_float_keys = {
            "body_mass_kg", "ambient_c", "preferred_c", "r_per_year", "n0",
            "prey_growth", "pred_efficiency", "pred_death", "encounter_rate",
            "temperature_c", "rainfall_mm",
        }
        numeric_int_keys = {"years", "sentences"}

        normalized: dict = {}
        for key, value in args.items():
            if tool_name == "field_of_view" and key == "predator":
                normalized[key] = _to_bool(value)
                continue
            if key in numeric_float_keys:
                try:
                    normalized[key] = float(value)
                    continue
                except Exception:
                    pass
            if key in numeric_int_keys:
                try:
                    normalized[key] = int(value)
                    continue
                except Exception:
                    pass
            # pass-through for strings or anything else
            normalized[key] = value
        return normalized
    return args


async def handle_question(question: str, model: str | None = None) -> str:
    server, tool, arguments = llm_route_task(question, model=model)
    if not server or not tool or not arguments:
        return "Router could not determine server/tool/arguments. Please rephrase your question."

    server_scripts = get_available_server_scripts()
    server_script = server_scripts.get(server)
    if not server_script or not os.path.exists(server_script):
        return f"Selected server '{server}' is not available."

    # Log which server/tool were selected by the router
    logger.info("router selection: server=%s tool=%s args=%s", server, tool, arguments)

    normalized_args = _normalize_arguments(server, tool, arguments)

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None,
    )

    logger.info("launching: script=%s tool=%s normalized_args=%s", server_script, tool, normalized_args)

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result_text = await call_tool(session, tool, **normalized_args)
                return result_text
    except Exception as exc:
        logger.exception("tool execution failed: server=%s tool=%s", server, tool)
        return f"Error executing tool {tool}: {exc}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="MCP multi-math client")
    parser.add_argument("--question", "-q", nargs="+", help="Natural language question", required=True)
    parser.add_argument("--model", "-m", default=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), help="LLM model name for routing")
    args = parser.parse_args()

    qtext = " ".join(args.question)
    result = await handle_question(qtext, model=args.model)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())


