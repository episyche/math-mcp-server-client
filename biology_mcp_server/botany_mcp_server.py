from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:  # optional dependency
    import wikipedia  # type: ignore
except Exception:
    wikipedia = None  # type: ignore


mcp = FastMCP("BotanyServer")


# --- Data snippets for quick lookups ---
_EDIBLE_PLANTS: set[str] = {
    "spinach", "lettuce", "tomato", "potato", "carrot", "broccoli", "cabbage",
    "basil", "mint", "cilantro", "parsley", "strawberry", "apple", "banana",
}

_MEDICINAL_USES: dict[str, list[str]] = {
    "aloe vera": ["skin soothing", "burn treatment"],
    "turmeric": ["anti-inflammatory", "antioxidant"],
    "ginger": ["anti-nausea", "digestive aid"],
}

_SEED_DISPERSAL: dict[str, list[str]] = {
    "dandelion": ["wind"],
    "coconut": ["water"],
    "burdock": ["animals"],
}


def _wiki_summary(title: str, sentences: int = 3) -> str:
    if wikipedia is None:
        raise RuntimeError("'wikipedia' package not installed. Install it or run 'pip install -r requirements.txt'.")
    try:
        wikipedia.set_lang("en")  # type: ignore
        return wikipedia.summary(title, sentences=sentences)  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Wikipedia lookup failed for '{title}': {exc}")


@mcp.tool()
def plant_summary(name: str, sentences: int = 3) -> str:
    """Return a brief Wikipedia summary for a plant by common or scientific name.

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
def plant_taxonomy(name: str) -> dict:
    """Return a simple taxonomy dict using Wikipedia infobox parsing when possible.

    Keys: kingdom, phylum, class, order, family, genus, species (best-effort).
    """
    # Best-effort: fetch summary page and return placeholders if unavailable
    try:
        summary = _wiki_summary(name, sentences=1)
    except Exception:
        summary = ""
    # Placeholder taxonomy without heavy scraping
    return {
        "kingdom": "Plantae",
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
def is_edible(name: str) -> bool:
    """Return True if the plant is commonly edible (heuristic)."""
    key = name.strip().lower()
    return key in _EDIBLE_PLANTS


@mcp.tool()
def medicinal_uses(name: str) -> list[str]:
    """Return known traditional medicinal uses (non-clinical, heuristic)."""
    key = name.strip().lower()
    return _MEDICINAL_USES.get(key, [])


@mcp.tool()
def leaf_area_index(total_leaf_area_m2: float, ground_area_m2: float) -> float:
    """Compute Leaf Area Index (LAI) = total leaf area / ground area."""
    if ground_area_m2 <= 0:
        raise ValueError("ground_area_m2 must be positive")
    return float(total_leaf_area_m2) / float(ground_area_m2)


@mcp.tool()
def photosynthesis_rate(light_umol_m2_s: float, co2_ppm: float, temperature_c: float) -> float:
    """Approximate photosynthesis rate with a simple response surface.

    Not a mechanistic model; returns relative rate [0..1]. Peaks near moderate temp (25C),
    saturates with light and CO2 (Michaelis-Menten like).
    """
    # Light response (half-saturation ~ 300 umol m^-2 s^-1)
    light_term = light_umol_m2_s / (light_umol_m2_s + 300.0)
    # CO2 response (half-saturation ~ 400 ppm)
    co2_term = co2_ppm / (co2_ppm + 400.0)
    # Temperature bell-shaped around 25C
    temp_term = max(0.0, 1.0 - ((temperature_c - 25.0) ** 2) / (25.0 ** 2))
    rate = light_term * co2_term * temp_term
    return float(max(0.0, min(1.0, rate)))


@mcp.tool()
def transpiration_rate(stomatal_conductance_mol_m2_s: float, vpd_kpa: float) -> float:
    """Approximate transpiration rate ~ conductance * VPD (scaled)."""
    rate = stomatal_conductance_mol_m2_s * vpd_kpa
    return float(max(0.0, rate))


@mcp.tool()
def growth_rate_logistic(r_per_day: float, carrying_capacity: float, initial_biomass: float, days: int) -> float:
    """Logistic growth: N(t) = K / (1 + (K-N0)/N0 * e^{-rt}). Returns N(days).

    r_per_day: intrinsic growth rate
    carrying_capacity: K
    initial_biomass: N0
    days: time in days
    """
    import math

    if initial_biomass <= 0 or carrying_capacity <= 0:
        raise ValueError("initial_biomass and carrying_capacity must be positive")
    if initial_biomass >= carrying_capacity:
        return float(carrying_capacity)
    exponent = -r_per_day * float(days)
    denom = 1.0 + (carrying_capacity - initial_biomass) / initial_biomass * math.exp(exponent)
    return float(carrying_capacity / denom)


@mcp.tool()
def chlorophyll_index(red_reflectance: float, nir_reflectance: float) -> float:
    """Compute NDVI-like index: (NIR - Red) / (NIR + Red)."""
    denom = nir_reflectance + red_reflectance
    if denom == 0:
        raise ValueError("Sum of reflectances cannot be zero")
    return float((nir_reflectance - red_reflectance) / denom)


@mcp.tool()
def classify_life_form(height_m: float) -> str:
    """Classify plant by height: herb (<0.5 m), shrub (0.5–5 m), tree (>5 m)."""
    if height_m < 0.5:
        return "herb"
    if height_m <= 5.0:
        return "shrub"
    return "tree"


@mcp.tool()
def seed_dispersal_methods(name: str) -> list[str]:
    """Return common seed dispersal methods for a plant if known."""
    return _SEED_DISPERSAL.get(name.strip().lower(), [])


@mcp.tool()
def drought_stress_index(soil_moisture_vol_pct: float, wilting_point_vol_pct: float = 10.0, field_capacity_vol_pct: float = 35.0) -> float:
    """Compute a simple drought stress index [0..1], where 1 means high stress.

    Index = 1 - clamp((SM - WP) / (FC - WP), 0, 1)
    """
    if field_capacity_vol_pct <= wilting_point_vol_pct:
        raise ValueError("field_capacity must exceed wilting_point")
    ratio = (soil_moisture_vol_pct - wilting_point_vol_pct) / (field_capacity_vol_pct - wilting_point_vol_pct)
    ratio = max(0.0, min(1.0, ratio))
    return float(1.0 - ratio)


if __name__ == "__main__":
    mcp.run()


