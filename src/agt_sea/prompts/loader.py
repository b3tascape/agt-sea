"""
agt_sea — Prompt loader

Loads prompt content from plain text files on disk. Prompts are organised
by function (e.g. philosophies/) and keyed to their corresponding enum values.
"""

from __future__ import annotations

from pathlib import Path

from agt_sea.models.state import CreativePhilosophy

_PROMPTS_DIR = Path(__file__).parent


def load_philosophy_prompt(philosophy: CreativePhilosophy) -> str:
    """Load a creative-philosophy prompt from disk.

    Each philosophy maps to a plain text file at
    ``prompts/philosophies/{enum_value}.txt``.

    Args:
        philosophy: The creative philosophy whose prompt to load.

    Returns:
        The prompt text with leading/trailing whitespace stripped.

    Raises:
        FileNotFoundError: If no prompt file exists for the given philosophy.
    """
    path = _PROMPTS_DIR / "philosophies" / f"{philosophy.value}.txt"
    return path.read_text().strip()
