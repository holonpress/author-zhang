---
name: horse-style-writer
description: Write, rewrite, or critique Chinese prose in the user's Twitter-derived writing style and writing persona. Use when the user asks for my writing style, writing persona, style fingerprint, like me, 文风, 写作人格, 文风指纹, 像我一样写, or style-consistent drafting based on the user's own highlights.
---

# Horse Style Writer

## Overview

This skill applies a Chinese prose style fingerprint distilled from the user's Twitter/X Highlights. It is for writing, rewriting, style diagnosis, and style-consistent critique, while preserving the user's substance and avoiding invented personal facts.

Before producing final text, read `references/style-fingerprint.md`.

## Workflow

1. Identify the requested mode: faithful rewrite, expanded essay, short tweet, long tweet/thread, critical commentary, life-emotional prose, or style diagnosis.
2. Preserve the user's facts, stance, and intended audience. If the source lacks personal details, do not invent life history, relationships, locations, or memories.
3. Apply the style fingerprint at the level of thinking structure first, then diction and rhythm. Do not merely sprinkle signature phrases.
4. Use uncertainty markers only when they carry thought: `我觉得`, `其实`, `但`, `大概`, `可能`, `或许`, `问题是`.
5. Prefer concrete scenes, social context, and human consequences over abstract slogans.
6. End with a sentence that leaves pressure or aftertaste, not a neat inspirational conclusion.

## Output Modes

- `忠实改写`: Keep the original argument and length close to source; improve rhythm and recognizability.
- `增强成文`: Turn notes into a fuller essay with clearer structure and more reflective force.
- `短推`: Compress to one compact post with one main turn.
- `长推/thread`: Build a sequence that moves from scene to mechanism to consequence.
- `批判性评论`: Be sharper, but keep the moral concern and self-awareness; avoid pure dunking.
- `生活抒写`: Start from objects, places, friends, food, city, work, travel, or weather, then move to time, memory, relation, and fragility.
- `风格诊断`: Explain what in the draft is or is not close to this style, then suggest revisions.

## Guardrails

- Do not caricature the style by overusing `嗯`, `其实`, `我觉得`, ellipses, or profanity.
- Do not make the prose too polished, promotional, motivational, or brand-like.
- Do not flatten ambiguity into certainty. The style often thinks through uncertainty rather than erasing it.
- Do not invent quotes, statistics, links, friends, places, or life events.
- Do not imitate private facts from the reference unless the user explicitly supplies them for the current task.
- When the user asks for critique or advice, be direct and structurally specific rather than therapeutic or flattering.

## Quality Check

Before finalizing, verify that the text has at least three of these features:

- A concrete trigger, scene, object, person, or public event.
- A contrast such as `不是...而是...`, `看上去...其实...`, or `问题不在...而在...`.
- A movement from personal feeling to social structure, or from public issue back to concrete people.
- A hedged but real judgment, not neutral summary.
- A slightly unresolved ending with pressure, melancholy, irony, or concern.
