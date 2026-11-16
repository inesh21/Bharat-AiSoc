# HANDOFF.md: How agents and teammates hand work to each other

We run several agents (Codex, Antigravity, Claude Code) and three people on **separate local branches and worktrees**. Nothing is shared in memory between sessions or between agents. The only thing that survives is what is written in the repo. This file defines how to write it down.

## 1. Design rules

1. **One live handoff file per track**, owned by that track only: `docs/handoffs/track-a.md`, `track-b.md`, `track-c.md`. Because only one track edits each file, branches merge without conflicts.
2. **This root file is the protocol and index.** It changes rarely and only through the shared-file process in `docs/BRANCHING.md`.
3. **Newest session entry goes at the top** of the track file, under the "Session log" heading.
4. **Evidence over claims.** "Done" means a command was run and its result is recorded.
5. **Cross-track needs go in "Requests to other tracks"**, never as edits to someone else's files.
6. **Keep it short.** Each session entry should fit on one screen (about 40 lines). When a track file passes roughly 300 lines, compact old entries into a short "Archive summary" block at the bottom.

## 2. Who is active

Each track file starts with an **Active agent** line. Before you start, set it to your agent name and the date; when you stop, set it back to `none`. If it already names another agent and was set recently, stop and ask your human. Two agents must never work in the same worktree.

## 3. Start-of-session protocol

1. Open your worktree and branch. Run `git status` (must be clean) and `git merge integration`.
2. Read `AGENTS.md`, then your track file's latest entry, then your track brief in `docs/tracks/`.
3. Read the "Requests to other tracks" sections of the other two tracks for anything addressed to you. Other tracks' latest files are visible after they merge to `integration`, or directly with:
   ```
   git show track-b/main:docs/handoffs/track-b.md
   ```
4. Set **Active agent** in your track file.
5. State your plan for the session in two to five lines before editing code.

## 4. End-of-session protocol

1. Run the tests and checks for what you changed.
2. Add a new entry at the top of your track's session log using the template below.
3. Set **Active agent** back to `none`.
4. Commit code and the handoff (`docs(handoff): track-x session summary`). Do not leave uncommitted work.
5. Tell your human: branch name, last commit, and whether anything is ready to merge to `integration`.

## 5. Session entry template

Copy this block to the top of the session log.

```
### Session YYYY-MM-DD HH:MM | agent: codex|antigravity|claude | branch: track-x/topic
Task IDs: A6, A7

**Summary** (max 3 lines)

**Done** (with evidence)
- <what> | verified by: `<command>` -> <result>

**In progress / not done**
- <what, and exact state: file, function, what remains>

**Next steps** (ordered, concrete, so the next agent can start immediately)
1.
2.

**Decisions made**
- <decision> | why | ADR link if it affects other tracks

**Files touched**
- path/one
- path/two

**How to verify** (exact commands, expected output)
- `<command>` -> expect <result>

**Blockers**
- <what blocks, who can unblock>

**Requests to other tracks**
- To Track B: <what you need> | contract section | needed by <milestone>

**Assumptions / could not verify**
- <anything not run or not checked, e.g. no device, no GPU, no Llama access>
```

## 6. Requests to other tracks

Format: `To Track <X>: <request> | contract/section | needed for <milestone> | status: open|done`.
- The requesting track writes the request in its own file.
- The receiving track marks it handled in **its own** file's entry ("Handled request from Track C: ...").
- If a request needs a contract change, follow the contract change process in `docs/BRANCHING.md`. Do not work around it.

## 7. Artifact handoffs (models, data, test vectors)

A model or dataset handoff is complete only when all of these exist:
1. The file is in the shared location (team drive or Git LFS), not in plain git.
2. `models/manifest.json` has the entry: name, version, SHA-256, input size, normalization, date, ExecuTorch version used to export.
3. The sidecar JSON (`models/<name>.json`) has labels/tokenizer info, normalization, thresholds, and the verification tolerance.
4. Test vectors are committed in `test_vectors/` and the producer ran them on a laptop.
5. The producer's handoff entry lists the manifest entry and the exact command that created the file.

The receiving track's first action is to run the test vectors, to decide whose side a bug is on.

## 8. Milestones (integration points)

| ID | Meaning | Tracks | Exit check |
|---|---|---|---|
| I0 | Contracts frozen, mocks committed | all | each track runs against mocks |
| I1 | Runtime proven: stock Llama 1B on laptop and on the phone | B + C | TTFT and tokens/s recorded; versions pinned |
| I2 | Vision `.pte` runs in the app | A + C | 50/50 test vectors match on device |
| I3 | Advisory runs in the app from a vision JSON | B + C | 30/30 test prompts valid |
| I4 | End to end in airplane mode | all | 20 real photos, no crash |
| I5 | Voice and clarifying-question loop | B + C | works on 5 ambiguous photos |
| I6 | Freeze and polish | all | release APK, report, video |

Update the milestone status in your track file whenever it changes. A milestone is reached only when its exit check has been run and recorded.

## 9. Index of live files

- Track A (Vision): `docs/handoffs/track-a.md`
- Track B (Knowledge, Rules, Llama): `docs/handoffs/track-b.md`
- Track C (App, Voice, Integration): `docs/handoffs/track-c.md`
