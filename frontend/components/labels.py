"""
agt_sea — Display Labels

Human-readable labels for enum values used across the frontend.
Kept here so multiple components can share one source of truth.
"""

from __future__ import annotations

from agt_sea.models.state import CreativePhilosophy


PHILOSOPHY_LABELS: dict[CreativePhilosophy, str] = {
    CreativePhilosophy.BOLD_AND_DISRUPTIVE: "bold & disruptive",
    CreativePhilosophy.MINIMAL_AND_REFINED: "minimal & refined",
    CreativePhilosophy.EMOTIONALLY_DRIVEN: "emotionally driven",
    CreativePhilosophy.DATA_LED: "data led",
    CreativePhilosophy.CULTURALLY_PROVOCATIVE: "culturally provocative",
}
