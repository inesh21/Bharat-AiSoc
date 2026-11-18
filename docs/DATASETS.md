# DATASETS.md: Datasets and Licenses

This file documents all training, validation, and benchmark datasets used in the Offline Crop Disease Assistant, in accordance with Track A ownership and AGENTS.md rule 7.

## 1. Datasets Inventory

| Dataset | Source / URL | License | Intended Use | Split Strategy |
|---|---|---|---|---|
| **PlantVillage** | Hughes, D. and Salathé, M. (2015), Penn State / Mendeley Data | CC-BY 4.0 | Baseline crop & disease classification (lab condition) | Grouped split by plant/batch (prevent near-duplicate leakage) |
| **PlantDoc** | Singh et al. (2020), CoDS-COMAD / IIT Bombay | MIT | In-field disease classification & generalization | Stratified train/val/test by field instance |
| **IP102** | Wu et al. (2019), CVPR / Pest Recognition | CC BY-NC-SA 4.0 | Agricultural pest classification (`pest__fall_armyworm`, etc.) | Pre-defined train/val/test splits |
| **Field Leaf & Non-Leaf Collection** | Real-world mobile photos (phone camera captures) | CC0 (Project internal) | In-field calibration, OOD detection, `unknown` class, image quality testing | 70% val / 30% locked test |

## 2. Leakage Prevention and Splitting Rules (Task A4)

1. **No random per-image split on PlantVillage:** PlantVillage contains multiple camera shots of the exact same leaf specimen under identical lighting. Random splitting results in synthetic near-duplicate data leakage between train and test sets.
2. **Batch / Leaf Grouping:** Splitting is performed at the leaf/shoot cluster level or folder/acquisition batch level.
3. **Locked Test Set:** A dedicated holdout set composed of 100% field-condition images (PlantDoc + field captures) is locked for final metric validation (Macro-F1, ECE, OOD rejection rate). No tuning or early stopping is performed against this locked set.

## 3. Unknown & Out-of-Distribution Strategy (Task A5 & A8)

- **Non-leaf / Background images:** Background textures, soil, hands, tools, clothes, non-agricultural items.
- **Unseen crops/weeds:** Crops outside the defined 5 crops (`tomato`, `potato`, `rice`, `maize`, `cotton`).
- Rejection threshold tuned on validation OOD set using Max-Softmax Probability (MSP) and energy-based OOD scoring.
