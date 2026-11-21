# Knowledge Base Safety Review Log

> **Phase 3 of Runbook** – every entry in `rules.yaml` and `kb.json` must be
> verified against an official source before `verified: true` is set.

**Review status:** 🔴 Draft — human verification required before release.

---

## Instructions for the reviewer

1. For every chemical in `rules.yaml`: find the dose, PHI (pre-harvest interval)
   and approved crops on **an official label or government extension source**
   (ICAR, TNAU, CIBRC, state agriculture department, national plant protection
   registry for India).  Fill in the table below.
2. Cross-check `kb.json` citations: open each `sources` URL and confirm it
   exists and supports the claim.  Spot-check at least **30%** of entries; do
   all entries with chemical advice.
3. Check the **restricted chemicals** list in `rules.yaml` against the current
   CIBRC / CIB&RC banned-pesticides list for India.
4. Confirm that every chemical in `kb.json` → `chemical_options` exists in
   `rules.yaml` → `chemicals` **and** that `approved_targets` includes the
   condition ID.
5. Run the safety test: `python -m pytest knowledge/test_safety.py -v`
6. Update the table, record your name and date, and set `review_complete: true`
   in this file when done.

---

## Review table: chemicals in rules.yaml

| Chemical key | Active ingredient | Dose in rules.yaml | Official source checked | PHI match | Approved targets correct | Reviewer | Date | Status |
|---|---|---|---|---|---|---|---|---|
| `copper_oxychloride` | Copper Oxychloride 50% WP | 2.5 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `mancozeb` | Mancozeb 75% WP | 2.0 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `chlorothalonil` | Chlorothalonil 75% WP | 2.0 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `metalaxyl_mancozeb` | Metalaxyl 8% + Mancozeb 64% WP | 2.5 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `tricyclazole` | Tricyclazole 75% WP | 0.6 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `propiconazole` | Propiconazole 25% EC | 1.0 mL/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `streptocycline_copper` | Streptomycin sulphate 90% + Tetracycline HCl 10% SP | 0.1 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `emamectin_benzoate` | Emamectin Benzoate 5% SG | 0.4 g/L | TODO | TODO | TODO | — | — | 🔴 Unverified |
| `chlorantraniliprole` | Chlorantraniliprole 18.5% SC | 0.4 mL/L | TODO | TODO | TODO | — | — | 🔴 Unverified |

## Review table: organic / biopesticide options

| Key | Product | Dose | Source checked | Reviewer | Date | Status |
|---|---|---|---|---|---|---|
| `neem_oil` | NSKE 5% / Neem Oil 10,000 ppm | 5.0 mL/L | TODO | — | — | 🔴 Unverified |
| `trichoderma` | T. viride / T. harzianum | 5.0 g/L | TODO | — | — | 🔴 Unverified |
| `pseudomonas_fluorescens` | P. fluorescens | 5.0 g/L | TODO | — | — | 🔴 Unverified |
| `bacillus_thuringiensis` | Bt kurstaki | 2.0 g/L | TODO | — | — | 🔴 Unverified |

## kb.json citation spot-check (≥30% required)

| KB entry id | Source URL checked | Claim supported | Reviewer | Date |
|---|---|---|---|---|
| `tomato__early_blight` | TODO | TODO | — | — |
| `tomato__late_blight` | TODO | TODO | — | — |
| `potato__late_blight` | TODO | TODO | — | — |
| `rice__blast` | TODO | TODO | — | — |
| `rice__bacterial_blight` | TODO | TODO | — | — |
| `pest__fall_armyworm` | TODO | TODO | — | — |
| *(add remaining ≥30% here)* | | | | |

## Restricted chemicals check (India CIBRC list)

| Chemical | In rules.yaml restricted list | Current CIBRC status | Action needed |
|---|---|---|---|
| monocrotophos | ✅ | Restricted for vegetables | None |
| endosulfan | ✅ | Banned | None |
| paraquat | ✅ | Restricted | None |
| carbofuran | ✅ | Restricted | None |
| *(check full CIBRC list for any missing entries)* | | | |

## Language review

| Language | Reviewer (native speaker) | Date reviewed | Status |
|---|---|---|---|
| English (en) | TODO | — | 🔴 Pending |
| Hindi (hi) | TODO | — | 🔴 Pending |
| Telugu (te) | TODO | — | 🔴 Pending |
| Tamil (ta) | TODO | — | 🔴 Pending |
| Kannada (kn) | TODO | — | 🔴 Pending |

> [!IMPORTANT]
> Per AGENTS.md §12: wrong advice can destroy a harvest or poison people.
> Do NOT set a language to "reviewed" without a native speaker checking every
> phrase, including chemical safety text.
> Remove languages without a confirmed native-speaker reviewer before release.

## Review completion sign-off

```
review_complete: false
reviewed_by: —
review_date: —
safety_test_result: not run
```

When all rows are verified and `python -m pytest knowledge/test_safety.py -v`
passes, update this block and commit as:
`docs(knowledge): complete Phase 3 safety review — Checkpoint 3`
