"""
agt_sea — Prompt loader

Loads prompt content from plain text files on disk. Prompts are organised
by category (e.g. ``philosophies/``, ``templates/``, ``guidance/``) and
keyed by name — each category maps to a subdirectory under ``prompts/``
and each prompt to a ``.txt`` file inside it.
"""

from __future__ import annotations

from pathlib import Path

from agt_sea.models.state import (
    CreativePhilosophy,
    Provenance,
    StrategicPhilosophy,
    Taste,
)

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(category: str, name: str) -> str:
    """Load a prompt text file from disk.

    Prompts are organised by category (e.g. 'philosophies', 'templates',
    'guidance') and keyed by name. Each maps to a plain text file at
    ``prompts/{category}/{name}.txt``.

    Args:
        category: The prompt category directory (e.g. 'philosophies').
        name: The filename stem (e.g. 'bold_and_disruptive').

    Returns:
        The prompt text with leading/trailing whitespace stripped.

    Raises:
        FileNotFoundError: If no prompt file exists for the given category/name.
    """
    path = _PROMPTS_DIR / category / f"{name}.txt"
    return path.read_text().strip()


def load_creative_philosophy(philosophy: CreativePhilosophy) -> str:
    """Load a creative-philosophy prompt from disk.

    Convenience wrapper around load_prompt() for the creative philosophies category.
    """
    return load_prompt("philosophies/creative", philosophy.value)


def load_strategic_philosophy(philosophy: StrategicPhilosophy) -> str:
    """Load a strategic-philosophy prompt from disk.

    Convenience wrapper around load_prompt() for the strategic philosophies category.
    """
    return load_prompt("philosophies/strategic", philosophy.value)


def load_provenance(provenance: Provenance) -> str:
    """Load a provenance prompt from disk.

    Convenience wrapper around load_prompt() for the provenance category.
    Callers must check for NEUTRAL before invoking — NEUTRAL bypasses
    injection entirely and there is no ``neutral.txt`` on disk.
    """
    return load_prompt("provenance", provenance.value)


def load_taste(taste: Taste) -> str:
    """Load a taste prompt from disk.

    Convenience wrapper around load_prompt() for the taste category.
    Callers must check for NEUTRAL before invoking — NEUTRAL bypasses
    injection entirely and there is no ``neutral.txt`` on disk.
    """
    return load_prompt("taste", taste.value)


def load_template(name: str) -> str:
    """Load a template prompt from disk.

    Convenience wrapper around load_prompt() for the templates category.
    """
    return load_prompt("templates", name)


def load_guidance(name: str) -> str:
    """Load a guidance prompt from disk.

    Convenience wrapper around load_prompt() for the guidance category.
    """
    return load_prompt("guidance", name)
