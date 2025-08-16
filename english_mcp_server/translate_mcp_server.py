from __future__ import annotations

from mcp.server.fastmcp import FastMCP

try:
    from deep_translator import GoogleTranslator  # type: ignore
except Exception:
    GoogleTranslator = None  # type: ignore


mcp = FastMCP("TranslateServer")


def _translate(text: str, target: str, src: str | None = None) -> str:
    if GoogleTranslator is None:
        raise RuntimeError(
            "deep-translator not installed. Install it or run 'pip install -r requirements.txt'."
        )
    if src:
        translator = GoogleTranslator(source=src, target=target)  # type: ignore
    else:
        translator = GoogleTranslator(source="auto", target=target)  # type: ignore
    return translator.translate(text)  # type: ignore


@mcp.tool()
def translate_to_english(text: str, source_language: str | None = None) -> str:
    """Translate text to English.

    - text: input text
    - source_language: optional ISO 639-1 code for source language (e.g., 'es', 'fr'). If omitted, autodetect is used.
    Returns translated English text.
    """
    return _translate(text, target="en", src=source_language)


@mcp.tool()
def translate_from_english(text: str, target_language: str) -> str:
    """Translate English text to a specified target language.

    - text: English input text
    - target_language: ISO 639-1 code for target language (e.g., 'es', 'fr', 'de').
    Returns translated text in the target language.
    """
    return _translate(text, target=target_language, src="en")


if __name__ == "__main__":
    mcp.run()


