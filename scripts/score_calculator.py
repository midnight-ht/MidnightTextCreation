#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scoring utilities for midnight-advertorial."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ScoreBreakdown:
    blacklist_score: int = 0
    meta_score: int = 0
    repeated_start_score: int = 0
    paragraph_symmetry_penalty: int = 0
    list_overuse_penalty: int = 0
    generic_opening_penalty: int = 0
    generic_ending_penalty: int = 0
    total_score: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def level_for_score(score: int) -> str:
    if score <= 25:
        return "pass"
    if score <= 45:
        return "light_rewrite"
    if score <= 70:
        return "heavy_rewrite"
    return "restructure_required"


def action_for_score(score: int) -> str:
    if score <= 25:
        return "human_review"
    if score <= 45:
        return "targeted_rewrite"
    if score <= 70:
        return "restructure_and_rewrite"
    return "return_to_structure_planning"
