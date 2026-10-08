"""Shared editorial layout catalog and source-preserving local packaging."""

import json
import re
from pathlib import Path


CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'rules/platform_layouts.json').read_text(encoding='utf-8'))
PROFILES = {key: {**CATALOG['families'][item['family']], **item}
            for key, item in CATALOG['platforms'].items()}


def layout_content(platform: str, text: str, mode: str | None = None) -> dict:
    profile = PROFILES[platform]
    mode = mode or profile['default_format']
    if mode not in profile['formats']:
        raise ValueError(f'Unsupported format {mode} for {platform}')
    style = {'thread': 'thread', 'spoken': 'spoken', 'script': 'spoken',
             'carousel': 'short', 'short_post': 'short'}.get(mode, 'preserve')
    warnings = ['Local packaging does not rewrite meaning, create visuals, validate native limits, or guarantee rendering.']
    # Keep fenced code intact; prose reflow must not damage examples or logs.
    protected = bool(re.search(r'^\s*(```|~~~)', text, re.M))
    if protected:
        pieces = [text] if text.strip() else []
        warnings.append('Fenced code preserved as one block; manually adapt it for feed, card or video surfaces.')
    elif style == 'preserve':
        pieces = [part.strip() for part in re.split(r'\n\s*\n', text) if part.strip()]
    else:
        pieces = [part.strip() for part in re.split(r'\n\s*\n|(?<=[。！？])|(?<=[.!?])\s+(?=[A-Z])', text) if part.strip()]
    kind = {'thread': 'post', 'spoken': 'speech', 'short': 'paragraph'}.get(style, 'section')
    if mode == 'carousel':
        kind = 'card'
    blocks = [{'index': i + 1, 'kind': kind, 'text': part} for i, part in enumerate(pieces)]
    if style == 'thread' and not protected:
        body = '\n'.join(f'{block["index"]}. {block["text"]}' for block in blocks)
    else:
        body = ('\n' if style == 'spoken' else '\n\n').join(pieces)
    return {'platform': platform, 'label': profile['label'], 'format': mode,
            'body': body, 'blocks': blocks, 'content_order': profile['content_order'],
            'paragraph_method': profile['paragraph_method'], 'emphasis_method': profile['emphasis_method'],
            'media_method': profile['media_method'], 'publishing_steps': profile['publishing_steps'],
            'native_note': profile['native_note'], 'semantic_adaptation': 'not_evaluated',
            'warnings': warnings}
