# 0002: Scope freeze
Date: 2026-11-19
Status: accepted
Deciders: all three humans

## Context
Depth beats breadth. Scope must be fixed before data collection and knowledge-base writing start.

## Decision
- Region: Pan-India (ICAR, TNAU, and State Agronomy standard)
- Crops (5): Tomato, Potato, Rice, Maize, Cotton
- Classes (19): 17 crop disease/healthy classes, 1 pest class (`pest__fall_armyworm`), and 1 `unknown` class as frozen in `labels.json`
- Languages (3 core): English (`en`), Hindi (`hi`), and Telugu (`te`)
- Primary device: Arm64 Android phone (>= 6GB RAM recommended, min Android 8.0 / SDK 26)
- Core innovations: structured hand-off, clarifying questions, uncertainty handling, rules-engine safety layer, offline retrieval with sources, voice-first local-language UI, lesion-based severity
- Success targets: vision macro-F1 >= 0.85 on field-style set; end-to-end latency < 3.0s; zero network calls at runtime

## Consequences
Any change to these needs all three humans to agree and a new decision record.
