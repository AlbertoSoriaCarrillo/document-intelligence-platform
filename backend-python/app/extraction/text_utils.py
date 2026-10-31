"""Normalización compartida para comparar etiquetas del documento."""

import unicodedata

def normalize_label(text: str) -> str:
    """Unifica acentos, mayúsculas y espacios solo para comparar etiquetas."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.lower().split())
