# Decision records

Cross-track decisions are recorded here as one file per decision (`NNNN-short-title.md`), so branches never edit the same file. A decision that affects more than one track (tooling, versions, contracts, scope) needs a record and the agreement of all three humans. Shared-file changes go through the `contracts/` branch process in `docs/BRANCHING.md`.

## Template

```
# NNNN: Title
Date: YYYY-MM-DD
Status: proposed | accepted | superseded by NNNN
Deciders: names

## Context
What problem or choice, and constraints.

## Options considered
1. ...
2. ...

## Decision
What we chose.

## Consequences
What changes for Track A / B / C. What must be updated (contracts, versions, mocks).
```

## Index

| ID | Title | Status |
|---|---|---|
| 0001 | Vision runtime | proposed |
| 0002 | Scope freeze | proposed |
