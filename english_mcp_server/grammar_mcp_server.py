from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:
    import language_tool_python  # type: ignore
except Exception:
    language_tool_python = None  # type: ignore


mcp = FastMCP("GrammarServer")


def _check_with_languagetool(text: str) -> list[dict]:
    if language_tool_python is None:
        raise RuntimeError(
            "language-tool-python not installed. Install it or use requirements.txt."
        )
    tool = language_tool_python.LanguageTool('en-US')  # type: ignore
    matches = tool.check(text)  # type: ignore
    suggestions: list[dict] = []
    for m in matches:
        suggestions.append({
            "message": getattr(m, "message", ""),
            "offset": getattr(m, "offset", 0),
            "error_length": getattr(m, "errorLength", 0),
            "replacements": list(getattr(m, "replacements", [])),
            "rule_id": getattr(m, "ruleId", None),
        })
    return suggestions


def _simple_rules(text: str) -> list[dict]:
    suggestions: list[dict] = []
    if text and text[0].islower():
        suggestions.append({
            "message": "Sentence should start with a capital letter.",
            "offset": 0,
            "error_length": 1,
            "replacements": [text[0].upper() + text[1:]],
            "rule_id": "CAPITALIZATION_SENTENCE_START",
        })
    if text and not text.strip().endswith(('.', '!', '?')):
        suggestions.append({
            "message": "Sentence should end with proper punctuation.",
            "offset": max(0, len(text) - 1),
            "error_length": 1,
            "replacements": [text.rstrip() + "."],
            "rule_id": "TERMINAL_PUNCTUATION",
        })
    return suggestions


@mcp.tool()
def check_grammar(text: str, use_languagetool: bool = True) -> dict:
    """Check English grammar and return issues with suggestions.

    - text: input sentence or paragraph to check.
    - use_languagetool: if True and language-tool-python available, uses it; otherwise falls back to simple rules.
    Returns a dict with keys: engine ("languagetool"|"simple"), issues: list[dict].
    """
    if use_languagetool and language_tool_python is not None:
        issues = _check_with_languagetool(text)
        return {"engine": "languagetool", "issues": issues}
    issues = _simple_rules(text)
    return {"engine": "simple", "issues": issues}


if __name__ == "__main__":
    mcp.run()


