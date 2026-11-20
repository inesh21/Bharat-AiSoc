# DATASETS.md: Datasets and Licenses

This file documents all training, validation, and benchmark datasets used in the Offline Crop Disease Assistant, in accordance with Track A ownership and AGENTS.md rule 7.

## 1. Datasets Inventory

| Dataset | Source / URL | License | Intended Use | Split Strategy | Current Count |
|---|---|---|---|---|---|
| **PlantVillage** | Hughes, D. and Salathé, M. (2015), Penn State / Mendeley Data (`https://www.kaggle.com/datasets/emmarex/plantdisease`) | CC BY-SA 4.0 | Baseline crop & disease classification (lab condition: tomato, potato, maize) | 85% train / 15% val per class (deduplicated & capped at 600/class) | 6,152 images (5,230 train, 922 val) |
| **PlantDoc** | Singh et al. (2020), CoDS-COMAD / IIT Bombay (`https://github.com/pratikkayal/PlantDoc-Dataset`) | MIT | In-field disease evaluation (tomato, potato, maize) | 100% test split (field condition holdout) | 706 images (test) |
| **Rice Leaf Disease (Lab)** | Prajapati et al. (2017) / Kaggle (`https://www.kaggle.com/datasets/vbookshelf/rice-leaf-diseases`) | CC0: Public Domain | Lab classification of rice diseases (`bacterial_blight`, `blast`, `brown_spot`) | 85% train / 15% val (deduplicated & capped) | 1,365 images (1,161 train, 204 val) |
| **RiceLeafBD** | Rahman et al. (2020) / Kaggle (`Original Images.zip`) | CC BY 4.0 | Field-level rice disease test (`bacterial_blight`, `brown_spot`, `healthy`) + healthy train/val | Healthy: 70% train/val (`riceleafbd_train`), 30% test (`riceleafbd`). Diseases: 100% test | 945 images (150 train, 26 val, 769 test) |
| **Cotton Leaf Disease (Lab)** | Janmejay Bhoi / Kaggle (`https://www.kaggle.com/datasets/janmejaybhoi/cotton-disease-dataset`) | CC BY-SA 4.0 | Lab cotton classification (`cotton__bacterial_blight`, `cotton__healthy`) | 85% train / 15% val (deduplicated & capped) | 363 images (310 train, 53 val) |
| **SAR-CLD-2024** | SAR-CLD dataset (field cotton) | CC BY 4.0 | Field cotton evaluation (`bacterial_blight`, `healthy`) | 100% test | *Pending archive download* |
| **Field Maize Leaf 8 / MLD** | Field maize dataset | CC BY 4.0 | Field evaluation of maize & pest (`pest__fall_armyworm`) | 100% test / lab | *Pending FAW dataset* |
| **Unknown / Background Collection** | Real-world mobile photos (phone camera captures) | CC0 (Project internal) | In-field calibration, OOD detection, `unknown` class | 85% train / 15% val / locked test | *Pending user capture* |

## 2. Ingested Dataset Summary (Current `manifest.csv`)

Total images in `data/processed/manifest.csv`: **9,531**
- **Train:** 6,851 images
- **Val:** 1,205 images
- **Test:** 1,475 images (100% field condition holdout)

### Per-Class & Split Breakdown (17/19 classes populated)

| Label | Train | Val | Test (Field) | Total |
|---|---|---|---|---|
| `cotton__bacterial_blight` | 164 | 28 | 0 | 192 |
| `cotton__healthy` | 146 | 25 | 0 | 171 |
| `maize__common_rust` | 510 | 90 | 112 | 712 |
| `maize__healthy` | 510 | 90 | 0 | 600 |
| `maize__northern_leaf_blight` | 510 | 90 | 184 | 784 |
| `potato__early_blight` | 510 | 90 | 115 | 715 |
| `potato__healthy` | 130 | 22 | 0 | 152 |
| `potato__late_blight` | 510 | 90 | 103 | 703 |
| `rice__bacterial_blight` | 358 | 63 | 343 | 764 |
| `rice__blast` | 369 | 65 | 0 | 434 |
| `rice__brown_spot` | 434 | 76 | 351 | 861 |
| `rice__healthy` | 150 | 26 | 75 | 251 |
| `tomato__bacterial_spot` | 510 | 90 | 106 | 706 |
| `tomato__early_blight` | 510 | 90 | 86 | 686 |
| `tomato__healthy` | 510 | 90 | 0 | 600 |
| `tomato__late_blight` | 510 | 90 | 0 | 600 |
| `tomato__septoria_leaf_spot` | 510 | 90 | 0 | 600 |
| **All Classes** | **6,851** | **1,205** | **1,475** | **9,531** |

### Source Split Leakage Verification

| Source | Train | Val | Test | Total |
|---|---|---|---|---|
| `cotton_lab` | 310 | 53 | 0 | 363 |
| `plantvillage` | 5,230 | 922 | 0 | 6,152 |
| `rice_lab` | 1,161 | 204 | 0 | 1,365 |
| `riceleafbd_train` | 150 | 26 | 0 | 176 |
| `plantdoc` | 0 | 0 | 706 | 706 |
| `riceleafbd` | 0 | 0 | 769 | 769 |

*Zero cross-split leakage: all training sources are strictly contained in train/val; field sources (`plantdoc`, `riceleafbd`) are strictly isolated in test.*

## 3. Leakage Prevention and Splitting Rules (Task A4)

1. **No random per-image split on PlantVillage:** PlantVillage contains multiple camera shots of the exact same leaf specimen under identical lighting. Random splitting results in synthetic near-duplicate data leakage between train and test sets.
2. **Perceptual Hash Deduplication:** During ingestion via `vision/prepare_data.py`, difference hashing (dhash) with Hamming distance threshold ≤ 4 is applied to purge duplicate or near-duplicate frames.
3. **Dedicated Field Holdout:** In-field datasets (`plantdoc`, `riceleafbd`, `sar_cld_2024`, `own_field`) route 100% of samples to `test`, guaranteeing evaluation reflects real mobile camera conditions under varying natural illumination.
4. **Per-Split Group Capping:** Ingestion enforces `--max-per-class` independently per split group (`train_val` vs `test`), preventing field test sets from being blocked when training quotas are reached.

## 4. Unknown & Out-of-Distribution Strategy (Task A5 & A8)

- **Non-leaf / Background images:** Background textures, soil, hands, tools, clothes, non-agricultural items.
- **Unseen crops/weeds:** Crops outside the defined 5 crops (`tomato`, `potato`, `rice`, `maize`, `cotton`).
- Rejection threshold tuned on validation OOD set using Max-Softmax Probability (MSP) and energy-based OOD scoring.
