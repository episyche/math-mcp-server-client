from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:  # optional dependency for species info
    import wikipedia  # type: ignore
except Exception:
    wikipedia = None  # type: ignore


mcp = FastMCP("ZoologyServer")


def _wiki_summary(title: str, sentences: int = 3) -> str:
    if wikipedia is None:
        raise RuntimeError("'wikipedia' package not installed. Install it or run 'pip install -r requirements.txt'.")
    try:
        wikipedia.set_lang("en")  # type: ignore
        return wikipedia.summary(title, sentences=sentences)  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Wikipedia lookup failed for '{title}': {exc}")


@mcp.tool()
def animal_summary(name: str, sentences: int = 3) -> str:
    """Return a brief Wikipedia summary for an animal by common or scientific name.

    If the 'wikipedia' package is not installed or lookup fails, returns a helpful message
    instead of raising, to keep the MCP server stable.
    """
    if wikipedia is None:
        return (
            "Wikipedia package not installed. Install 'wikipedia' (see requirements.txt) "
            "to enable summaries."
        )
    try:
        return _wiki_summary(name, sentences=sentences)
    except Exception as exc:
        return f"Wikipedia lookup failed for '{name}': {exc}"


@mcp.tool()
def animal_taxonomy(name: str) -> dict:
    """Return a simple taxonomy dict (best-effort) for an animal.

    Keys: kingdom, phylum, class, order, family, genus, species.
    """
    try:
        summary = _wiki_summary(name, sentences=1)
    except Exception:
        summary = ""
    return {
        "kingdom": "Animalia",
        "phylum": None,
        "class": None,
        "order": None,
        "family": None,
        "genus": None,
        "species": name,
        "note": "Best-effort. For precise taxonomy, integrate a dedicated API (e.g., GBIF).",
        "summary": summary,
    }


@mcp.tool()
def basal_metabolic_rate(body_mass_kg: float) -> float:
    """Allometric BMR scaling ~ 70 * mass^0.75 (kcal/day), rough estimate.

    Returns kcal/day.
    """
    import math

    return float(70.0 * (max(body_mass_kg, 0.0) ** 0.75))


@mcp.tool()
def field_of_view(predator: bool) -> str:
    """Return typical field-of-view: predators often have narrower FoV (binocular), prey wider.

    Returns a qualitative category: 'narrow', 'wide'.
    """
    return "narrow" if predator else "wide"


@mcp.tool()
def max_running_speed(body_mass_kg: float) -> float:
    """Very rough hump-shaped relationship for terrestrial animals (m/s)."""
    import math

    m = max(body_mass_kg, 0.001)
    # Peak around cheetah-like mass ~ 50 kg in this toy model
    speed = 30.0 * math.exp(-((math.log(m) - math.log(50.0)) ** 2) / (2 * (0.8 ** 2)))
    return float(speed)


@mcp.tool()
def daily_food_requirement(body_mass_kg: float, trophic_level: str = "omnivore") -> float:
    """Estimate daily food intake as % of body mass depending on trophic level.

    Returns kg/day.
    """
    level = trophic_level.strip().lower()
    perc = 0.05  # default 5%
    if level == "herbivore":
        perc = 0.08
    elif level == "carnivore":
        perc = 0.03
    return float(body_mass_kg * perc)


@mcp.tool()
def thermal_comfort_index(ambient_c: float, preferred_c: float) -> float:
    """Return a [0..1] comfort index based on deviation from preferred temperature."""
    import math

    deviation = abs(ambient_c - preferred_c)
    return float(max(0.0, 1.0 - deviation / 20.0))


@mcp.tool()
def population_growth_rate(r_per_year: float, n0: float, years: int) -> float:
    """Exponential growth: N(t) = N0 * e^{rt}. Returns N(years)."""
    import math

    return float(n0 * math.exp(r_per_year * float(years)))


@mcp.tool()
def predator_prey_equilibrium(prey_growth: float, pred_efficiency: float, pred_death: float, encounter_rate: float) -> dict:
    """Lotka-Volterra equilibrium for prey X and predator Y (toy):

    X* = d / (c)
    Y* = a / (b)
    where a=prey_growth, b=encounter_rate, c=pred_efficiency*encounter_rate, d=pred_death
    """
    if encounter_rate <= 0 or pred_efficiency <= 0:
        raise ValueError("encounter_rate and pred_efficiency must be positive")
    x_star = pred_death / (pred_efficiency * encounter_rate)
    y_star = prey_growth / encounter_rate
    return {"prey_eq": float(x_star), "predator_eq": float(y_star)}


@mcp.tool()
def habitat_suitability(temperature_c: float, rainfall_mm: float) -> float:
    """Simple suitability index [0..1] increasing with moderate temp and rainfall."""
    import math

    temp_term = max(0.0, 1.0 - abs(temperature_c - 20.0) / 20.0)
    rain_term = max(0.0, min(1.0, rainfall_mm / 2000.0))
    return float(0.5 * temp_term + 0.5 * rain_term)


@mcp.tool()
def lifespan_estimate(body_mass_kg: float) -> float:
    """Very rough allometric lifespan estimate (years): ~ 5 * mass^0.2."""
    return float(5.0 * (max(body_mass_kg, 0.0) ** 0.2))


@mcp.tool()
def classify_diet(teeth_shape: str) -> str:
    """Classify diet from teeth shape: 'flat'->herbivore, 'sharp'->carnivore, 'mixed'->omnivore."""
    key = teeth_shape.strip().lower()
    if key == "flat":
        return "herbivore"
    if key == "sharp":
        return "carnivore"
    return "omnivore"


if __name__ == "__main__":
    mcp.run()


