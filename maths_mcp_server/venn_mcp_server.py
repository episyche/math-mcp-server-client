from __future__ import annotations

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("VennServer")


def _validate_non_negative(n: int) -> int:
    if n < 0:
        raise ValueError("Counts must be non-negative integers.")
    return n


@mcp.tool()
def two_set_regions(n_a: int, n_b: int, n_a_intersect_b: int) -> dict:
    """Return region sizes for a two-set Venn diagram.

    Inputs are non-negative integers:
    - n_a: |A|
    - n_b: |B|
    - n_a_intersect_b: |A ∩ B|

    Returns a dict with keys:
    - only_a: |A \ B|
    - only_b: |B \ A|
    - both: |A ∩ B|
    - union: |A ∪ B|
    """
    n_a = _validate_non_negative(n_a)
    n_b = _validate_non_negative(n_b)
    n_i = _validate_non_negative(n_a_intersect_b)
    if n_i > min(n_a, n_b):
        raise ValueError("Intersection cannot exceed either set size.")
    only_a = n_a - n_i
    only_b = n_b - n_i
    union = n_a + n_b - n_i
    return {"only_a": only_a, "only_b": only_b, "both": n_i, "union": union}


@mcp.tool()
def three_set_regions(n_a: int, n_b: int, n_c: int,
                      n_ab: int, n_ac: int, n_bc: int, n_abc: int) -> dict:
    """Return region sizes for a three-set Venn diagram.

    Inputs are non-negative integers representing sizes:
    - n_a, n_b, n_c: |A|, |B|, |C|
    - n_ab, n_ac, n_bc: pairwise intersections |A∩B|, |A∩C|, |B∩C|
    - n_abc: triple intersection |A∩B∩C|

    Returns a dict with keys for each disjoint region:
    - only_a, only_b, only_c
    - a_b_only (A∩B minus C)
    - a_c_only (A∩C minus B)
    - b_c_only (B∩C minus A)
    - all_three (A∩B∩C)
    - union
    """
    n_a = _validate_non_negative(n_a)
    n_b = _validate_non_negative(n_b)
    n_c = _validate_non_negative(n_c)
    n_ab = _validate_non_negative(n_ab)
    n_ac = _validate_non_negative(n_ac)
    n_bc = _validate_non_negative(n_bc)
    n_abc = _validate_non_negative(n_abc)

    if n_abc > min(n_ab, n_ac, n_bc):
        raise ValueError("Triple intersection cannot exceed any pairwise intersection.")

    a_b_only = n_ab - n_abc
    a_c_only = n_ac - n_abc
    b_c_only = n_bc - n_abc

    only_a = n_a - (a_b_only + a_c_only + n_abc)
    only_b = n_b - (a_b_only + b_c_only + n_abc)
    only_c = n_c - (a_c_only + b_c_only + n_abc)

    if min(only_a, only_b, only_c) < 0:
        raise ValueError("Inconsistent inputs: negative exclusive region size.")

    union = only_a + only_b + only_c + a_b_only + a_c_only + b_c_only + n_abc
    return {
        "only_a": only_a,
        "only_b": only_b,
        "only_c": only_c,
        "a_b_only": a_b_only,
        "a_c_only": a_c_only,
        "b_c_only": b_c_only,
        "all_three": n_abc,
        "union": union,
    }


if __name__ == "__main__":
    mcp.run()


