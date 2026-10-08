#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Text normalization utilities for midnight-advertorial."""

from __future__ import annotations

import re
from collections.abc import Callable


def transform_prose(text: str, transform: Callable[[str], str], *, trim_edges: bool = False) -> str:
    """Apply prose edits without changing fenced code, including unclosed fences."""
    output, buffer = [], []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^[ \t]*(`{3,}|~{3,})", line)
        if fence is None and marker:
            output.append(transform("".join(buffer)))
            buffer = []
            fence = marker[1]
            output.append(line)
        elif fence is not None:
            output.append(line)
            if re.fullmatch(r"[ \t]*" + re.escape(fence[0]) + r"{" + str(len(fence)) + r",}[ \t]*\n?", line):
                fence = None
        else:
            buffer.append(line)
    output.append(transform("".join(buffer)))
    if trim_edges:
        output[0] = output[0].lstrip()
        output[-1] = output[-1].rstrip()
    return "".join(output)


def normalize_text(text: str) -> str:
    """Normalize whitespace and common punctuation spacing."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return transform_prose(text, lambda prose: re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", prose)), trim_edges=True)


def split_sentences(text: str) -> list[str]:
    """Split Chinese/English mixed text into sentences."""
    text = normalize_text(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?\.])\s*", text)
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs."""
    text = normalize_text(text)
    return [p.strip() for p in re.split(r"\n+", text) if p.strip()]
