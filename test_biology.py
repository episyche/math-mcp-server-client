from biology_mcp_server.botany_mcp_server import (
    plant_summary,
    plant_taxonomy,
    is_edible,
    medicinal_uses,
    leaf_area_index,
    photosynthesis_rate,
    classify_life_form,
    seed_dispersal_methods,
    drought_stress_index,
)
from biology_mcp_server.zoology_mcp_server import (
    animal_summary,
    basal_metabolic_rate,
    field_of_view,
    max_running_speed,
)


def main() -> None:
    print("-- Botany --")
    print("summary(sunflower):", plant_summary("sunflower", sentences=2))
    print("tax(sunflower):", plant_taxonomy("sunflower"))
    print("is_edible(basil):", is_edible("basil"))
    print("medicinal(turmeric):", medicinal_uses("turmeric"))
    print("LAI:", leaf_area_index(12, 4))
    print("photosynthesis:", photosynthesis_rate(800, 500, 25))
    print("classify height 8m:", classify_life_form(8))
    print("seed dispersal (dandelion):", seed_dispersal_methods("dandelion"))
    print("drought stress:", drought_stress_index(12))

    print("\n-- Zoology --")
    print("summary(lion):", animal_summary("lion", sentences=2))
    print("BMR 70kg:", basal_metabolic_rate(70))
    print("FoV predator:", field_of_view(True))
    print("max speed 50kg:", max_running_speed(50))


if __name__ == "__main__":
    main()


