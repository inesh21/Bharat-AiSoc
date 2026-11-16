# Agent kit: Offline Crop Disease Assistant

Drop these files into the root of the project repo.

```
AGENTS.md                      single source of truth for every agent
CLAUDE.md                      imports AGENTS.md (Claude Code)
GEMINI.md                      points to AGENTS.md (Antigravity)
HANDOFF.md                     handoff protocol, template, milestones
docs/
  handoffs/track-a.md          live handoff, Track A (Vision)
  handoffs/track-b.md          live handoff, Track B (Knowledge, Rules, Llama)
  handoffs/track-c.md          live handoff, Track C (App, Voice, Integration)
  tracks/TRACK_A_VISION.md     task list and definition of done, Track A
  tracks/TRACK_B_LLM.md        task list and definition of done, Track B
  tracks/TRACK_C_APP.md        task list and definition of done, Track C
  CONTRACTS.md                 frozen JSON interfaces between tracks
  ARCHITECTURE.md              pipeline, flows, failure paths
  BRANCHING.md                 worktrees, branches, merge and contract-change process
  versions.md                  pinned tool versions and working export commands
  decisions/                   one file per cross-track decision
  AGENT_PROMPTS.md             start, end, review, integration prompts
```

First steps:
1. Follow the one-time setup in `docs/BRANCHING.md` section 3.
2. Fill `docs/decisions/0002-scope-freeze.md` and `docs/versions.md` as a team.
3. Fill in the human owner names in each `docs/handoffs/track-*.md` and the table in `docs/AGENT_PROMPTS.md`.
4. Start each agent inside its own worktree with the session start prompt.
