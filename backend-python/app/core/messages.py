"""Carga los mensajes del backend desde un archivo JSON."""

import json
from pathlib import Path


_MESSAGES_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "messages.json"
)


def _load_messages() -> dict[str, str]:
    """Carga y valida los mensajes al importar el módulo."""
    with _MESSAGES_PATH.open(encoding="utf-8") as file:
        messages = json.load(file)

    if not isinstance(messages, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in messages.items()
    ):
        raise ValueError("messages.json debe contener claves y valores de texto.")

    return messages


_MESSAGES = _load_messages()


def get_message(key: str) -> str:
    """Obtiene un mensaje por su clave; si no existe, lanza KeyError."""
    return _MESSAGES[key]