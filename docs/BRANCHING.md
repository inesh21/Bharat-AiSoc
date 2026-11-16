# BRANCHING.md: Git workflow for three people and several agents on local branches

## 1. Principles

1. **One agent per worktree, one worktree per branch.** Agents never share a working directory. Git worktrees give each track its own folder on the same local repo.
2. **Each track edits only its own paths** (see `AGENTS.md` section 4), so merges rarely conflict.
3. **Shared files change only through a `contracts/` branch** approved by all three humans.
4. **No force-push, no history rewriting** on any shared branch. Merge, do not rebase, when updating from `integration`.
5. **Integration happens on `integration`**, tested, and only then promoted to `main`.

## 2. Branches

| Branch | Purpose | Who commits |
|---|---|---|
| `main` | Working, demo-ready state. Updated only from `integration` at milestones. | Human owner of Track C (or whoever the team picks), by merge only |
| `integration` | Where the three tracks meet and are tested together. | Humans, by merge only |
| `track-a/main`, `track-b/main`, `track-c/main` | Long-lived track branches. | The track's agent and human |
| `track-a/<topic>` etc. | Short-lived topic branches (for example `track-a/severity`), merged into the track's `main` branch. | The track's agent |
| `contracts/<topic>` | Proposed changes to shared files. | A human (agents may draft) |

## 3. One-time setup (a human does this)

```bash
git init crop-assistant && cd crop-assistant
# copy the agent kit files in, add .gitignore (see section 9), then:
git add -A && git commit -m "chore: project skeleton and agent kit"
git branch integration
git branch track-a/main integration
git branch track-b/main integration
git branch track-c/main integration

mkdir -p ../crop-wt
git worktree add ../crop-wt/track-a track-a/main
git worktree add ../crop-wt/track-b track-b/main
git worktree add ../crop-wt/track-c track-c/main
git worktree list
```

If each teammate has their own clone instead of one shared local repo, the same branch names apply; share branches by pushing to a remote or by `git fetch` from each other's repo.

Each agent is started **inside its own worktree folder** (for example `../crop-wt/track-a`). Open that folder in Antigravity, run Codex or Claude Code from it.

## 4. Daily rhythm

**Start of an agent session (inside the worktree):**
```bash
git status                # must be clean
git merge integration     # bring in everything the other tracks merged
```

**During:** small commits on the track branch or a topic branch.

**End of session:** tests, handoff entry, commit.

**Promote to integration (the track's human does this when the work is tested):**
```bash
cd <main repo or any worktree with integration checked out>
git switch integration
git merge --no-ff track-a/main -m "merge(track-a): <what changed>"
# run the integration checks from docs/tracks and the milestone exit check
```
Do this at least once a day while tracks are actively exchanging artifacts. After merging, tell the other tracks (a line in your handoff file is enough).

**Promote to main:** only at a milestone (I1 to I6) after its exit check passed.
```bash
git switch main && git merge --no-ff integration -m "release: milestone I<N>"
```

## 5. Commit messages

Format: `<type>(<scope>): <summary>`

- Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `merge`, `release`.
- Scopes: `vision`, `severity`, `kb`, `rules`, `llm`, `app`, `speech`, `bench`, `contracts`, `handoff`.
- Examples: `feat(vision): add temperature scaling`, `fix(app): use sidecar normalization`, `docs(handoff): track-b session summary`.
- One logical change per commit. Never commit generated models, datasets or secrets.

## 6. File ownership matrix (avoid conflicts)

| Path | A | B | C | Change via |
|---|---|---|---|---|
| `vision/`, `labels.json`, `test_vectors/vision/`, `docs/DATASETS.md` | edit | read | read | track branch |
| `knowledge/`, `llm/`, `test_vectors/llm/` | read | edit | read | track branch |
| `app_android/`, `speech/`, `benchmarks/`, `app_pi/` | read | read | edit | track branch |
| `docs/handoffs/track-x.md` | own file only | own file only | own file only | track branch |
| `models/manifest.json` | own entries | own entries | read | track branch (separate keys, so merges are clean) |
| `docs/CONTRACTS.md`, `docs/ARCHITECTURE.md`, `docs/versions.md`, `docs/decisions/`, `mocks/`, `AGENTS.md`, `HANDOFF.md`, `CLAUDE.md`, `GEMINI.md` | read | read | read | `contracts/` branch |

## 7. Contract change process

1. Anyone who needs a change writes the request in their handoff file with the reason and the proposed new shape.
2. A human opens `contracts/<topic>` from `integration` and makes the change in `docs/CONTRACTS.md`, bumps `schema_version`, updates `mocks/`, and records a decision in `docs/decisions/`.
3. All three humans approve (a message in the team chat is enough, recorded in the decision file).
4. Merge `contracts/<topic>` into `integration`. Every track then runs `git merge integration` before continuing.
5. Affected tracks update their code and test vectors within one working day and note it in their handoff.

Agents may draft the change on the `contracts/` branch if a human asks, but never merge it.

## 8. Conflict handling

- If a merge conflicts in a file you own, resolve it carefully, run tests, and note it in your handoff.
- If it conflicts in a file you do **not** own, stop. Abort the merge (`git merge --abort`), write the conflict in your handoff, and ask your human.
- Never resolve a conflict by deleting the other side's work without reading it.

## 9. Suggested `.gitignore` entries

```
data/
*.pte
*.pth
*.pt
*.onnx
*.hef
*.gguf
*.safetensors
tokenizer.model
.venv/
__pycache__/
.env
*.keystore
*.jks
app_android/**/build/
```
Model files and datasets are shared through the team drive or Git LFS and recorded in `models/manifest.json`.

## 10. Useful commands

```bash
git worktree list                              # see all worktrees
git branch -vv                                 # branches and last commits
git log --oneline --graph --all --decorate -20 # picture of the branches
git show track-b/main:docs/handoffs/track-b.md # read another track's handoff without switching
git diff integration...track-a/main --stat     # what Track A would add to integration
```
