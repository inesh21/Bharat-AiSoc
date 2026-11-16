# AGENT_PROMPTS.md: Prompts to paste into Codex, Antigravity and Claude Code

Replace the text in `<angle brackets>`. These work with any agent. Agents that load `AGENTS.md` automatically still benefit from the explicit start prompt.

## 0. Which agent does what (fill in)

| Track | Human | Main agent | Second agent (reviews) |
|---|---|---|---|
| A | | | |
| B | | | |
| C | | | |

Suggestion: use one agent as the builder and a different one as the reviewer per track, so mistakes are caught by a second pair of eyes. Never run two agents in one worktree at the same time.

## 1. Session start prompt

```
You are working on Track <A|B|C> of the Offline Crop Disease Assistant.
Your worktree is <path>, branch <branch>.

Before doing anything:
1. Run git status (it must be clean) and git merge integration.
2. Read AGENTS.md fully, then HANDOFF.md, then docs/handoffs/track-<x>.md (latest entry first),
   then docs/tracks/TRACK_<X>_<NAME>.md, then docs/CONTRACTS.md.
3. Read the "Requests to other tracks" sections of the other two track handoff files for
   anything addressed to Track <X>.
4. Set "Active agent" in your handoff file to <agent name> and today's date.

Then tell me, in 5 lines or fewer, what you understand the current state to be and your plan for
this session. Wait for my go-ahead before editing code.

Today's task: <task IDs and a sentence, for example "A7 augmentation pipeline">.

Rules: stay inside your track's owned paths; do not change contracts, labels, or pinned versions;
never fabricate results; say what you could not run.
```

## 2. Session end prompt

```
Wrap up this session.
1. Run the tests and checks for everything you changed and show me the commands and results.
2. Add a new entry at the top of the session log in docs/handoffs/track-<x>.md using the template in
   HANDOFF.md section 5 (summary, done with evidence, in progress, next steps, decisions, files touched,
   how to verify, blockers, requests to other tracks, assumptions you could not verify).
3. Set "Active agent" back to none and update the milestone table if something changed.
4. Commit the code and the handoff separately with conventional commit messages.
5. Tell me the branch, the last commit hash, and whether anything is ready to merge into integration.
```

## 3. Cross-review prompt (a different agent reviews the builder's branch)

```
Review branch <track-x/topic> against AGENTS.md and docs/CONTRACTS.md. You are read-only: do not edit code.
Check: (1) only owned paths changed, (2) contracts and labels untouched, (3) no network calls or secrets or model files committed,
(4) tests exist and actually run, (5) claims in the handoff match what the code does, (6) safety rules for advisories
(rules.yaml only, validator, fallback). Output a list of findings ordered by severity, each with file and line,
and a one-line verdict: ready to merge into integration or not.
```

## 4. Integration prompt (run in the track that receives artifacts)

```
Track <X> received new artifacts from Track <Y>: <manifest entries>.
1. Merge integration into this branch.
2. Verify the SHA-256 values against models/manifest.json.
3. Run the producer's test vectors and report exact pass/fail numbers.
4. If they pass, integrate behind the existing interface (VisionEngine or AdvisoryEngine) without changing the contract.
5. If they fail, do not patch around it. Write the failing vector, expected vs actual, and your hypothesis in the handoff
   under "Requests to other tracks".
```

## 5. Contract change draft prompt (a human asks an agent to draft only)

```
We need to change <contract and field>. Create branch contracts/<topic> from integration. Draft the change in
docs/CONTRACTS.md, bump schema_version, update the affected files in mocks/, and write docs/decisions/NNNN-<topic>.md
using the template. Do not merge. List which tracks must change code and what exactly.
```

## 6. Track-specific starter tasks

**Track A, first session:** "Read the brief. Do A1 and A2 only: list candidate datasets with licenses in docs/DATASETS.md and propose a labels.json for crops <list>. Do not download anything over 5 GB without asking."

**Track B, first session:** "Do B1 only. Help me request Llama 3.2 access, then export the stock Llama 3.2 1B Instruct to ExecuTorch using the official example for the version in docs/versions.md and run one prompt on the laptop. Record the exact working commands and any errors in the handoff. Do not guess flags; read the README of the pinned version."

**Track C, first session:** "Do C1 and C2 only. Guide me through the Android toolchain and building the ExecuTorch Android reference Llama app, then record time to first token, tokens per second and RAM in the handoff. Do not start the real app yet."

## 7. Tool notes

- **Codex:** reads `AGENTS.md` from the repo root (and from subfolders if you add nested ones). Run it from the track's worktree.
- **Claude Code:** reads `CLAUDE.md`, which imports `AGENTS.md`. Use plan mode before touching interfaces or exports.
- **Antigravity:** reads `GEMINI.md` and, depending on version, `AGENTS.md`. If it does not load either automatically, paste the start prompt above. Copy any plan or summary it produces into the handoff file so other agents can read it.
- **Optional:** add a short `AGENTS.md` inside `vision/`, `knowledge/` and `app_android/` repeating only that folder's rules; agents that support nested instruction files will pick the nearest one.
