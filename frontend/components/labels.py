"""
agt_sea — Display Labels

Human-readable labels for enum values used across the frontend.
Kept here so multiple components can share one source of truth.
"""

from __future__ import annotations

from agt_sea.models.state import CreativePhilosophy, StrategicPhilosophy


CREATIVE_PHILOSOPHY_LABELS: dict[CreativePhilosophy, str] = {
    CreativePhilosophy.NEUTRAL: "neutral (no lens)",
    CreativePhilosophy.BOLD_AND_DISRUPTIVE: "bold & disruptive",
    CreativePhilosophy.MINIMAL_AND_REFINED: "minimal & refined",
    CreativePhilosophy.EMOTIONALLY_DRIVEN: "emotionally driven",
    CreativePhilosophy.DATA_LED: "data led",
    CreativePhilosophy.CULTURALLY_PROVOCATIVE: "culturally provocative",
}

STRATEGIC_PHILOSOPHY_LABELS: dict[StrategicPhilosophy, str] = {
    StrategicPhilosophy.NEUTRAL: "neutral (no lens)",
    StrategicPhilosophy.CHALLENGER: "challenger brand",
    StrategicPhilosophy.HUMAN_FIRST: "human-first",
    StrategicPhilosophy.CULTURAL_STRATEGY: "cultural strategy",
    StrategicPhilosophy.BRAND_WORLD: "brand-world building",
    StrategicPhilosophy.COMMERCIAL_PRAGMATIST: "commercial pragmatist",
}
