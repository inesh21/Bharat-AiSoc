You are working on **Track A (Vision and Severity)** of the Offline Crop Disease Assistant.
Before doing anything, read `AGENTS.md`, `HANDOFF.md`, `docs/handoffs/track-a.md`, `docs/tracks/TRACK_A_VISION.md`, `docs/CONTRACTS.md`, and `labels.json`, and follow every governance, branching, handoff, and verification rule strictly.

### Context & Current State
1. `data/processed/manifest.csv` already has **6,858 processed images** (`train=5230, val=922, test=706`) from `plantvillage` (lab) and `plantdoc` (field test).
2. I have now downloaded all the remaining dataset archives/folders into `data/raw/`.
3. **CRITICAL DISK SPACE RULE:** Do NOT extract everything at once. Process **one source at a time**: extract -> strip any `Augmented` folders and classes outside `labels.json` -> ingest via `vision/prepare_data.py` -> verify `data/processed/manifest.csv` -> delete the archive and raw extracted files immediately before moving to the next source.

---

### Step 1: Fix `vision/prepare_data.py` & `FIELD_SOURCES` First
1. Inspect `vision/prepare_data.py` and ensure `--max-per-class` caps **per split** (`train_val` vs `test`) rather than globally across splits, so `test_only` field datasets are never skipped when `train_val` already has 600 images.
2. Update `FIELD_SOURCES` in `vision/prepare_data.py` so all field-style sources automatically route 100% of their images to the `test` split:
   - `own_field`, `plantdoc`, `riceleafbd`, `sar_cld_2024`, `field_maize_8`, `unknown_test`
   (Any `_train` variant such as `riceleafbd_train` must NOT be in `FIELD_SOURCES` so it routes 85/15 to `train`/`val`.)

---

### Step 2: Inspect, Extract, Process, and Clean Up `data/raw/` (One by One)
List everything currently in `data/raw/`. For each archive/dataset found, map it to its target source name and process it sequentially:

1. **Rice — Lab (`rice_lab` | `Rice Leaf Disease Images.7z`):**
   - Extract `Bacterialblight`, `Blast`, and `Brownspot` directly into `data/raw/rice_lab/` (skip `Tungro`, not in `labels.json`; ensure no extra wrapper subfolder).
   - Map in `vision/class_map.yaml`: `rice_lab/Bacterialblight -> rice__bacterial_blight`, `rice_lab/Blast -> rice__blast`, `rice_lab/Brownspot -> rice__brown_spot`.
   - Run `.\.venv-et\Scripts\python.exe vision/prepare_data.py --source rice_lab --max-per-class 600 --max-side 256`.
   - Delete the `.7z` archive and `data/raw/rice_lab/*` once verified in `manifest.csv`.

2. **Rice — Field Test & Healthy (`riceleafbd` & `riceleafbd_train` | `Original Images.zip` / RiceLeafBD):**
   - Extract `Bacterial Leaf Blight`, `Brown Spot`, and `Healthy Rice Leaf` (skip `Tungro`).
   - Because `rice_lab` had no healthy class, split `Healthy Rice Leaf` (~70% into `data/raw/riceleafbd_train/Healthy Rice Leaf/` for `train/val`, and ~30% into `data/raw/riceleafbd/Healthy Rice Leaf/` for `test`). Keep `Bacterial Leaf Blight` and `Brown Spot` in `data/raw/riceleafbd/` for `test`.
   - Map exact subfolder names in `vision/class_map.yaml`.
   - Run `prepare_data.py` on `riceleafbd_train` (`--max-side 256 --max-per-class 600`) and `riceleafbd` (`--max-side 512 --max-per-class 2000`).
   - Delete the zip and raw folders once verified.

3. **Cotton — Lab (`cotton_lab` | `Cotton_Original_Dataset.zip`):**
   - Extract **only** `Bacterial Blight` and `Healthy Leaf` into `data/raw/cotton_lab/` (delete any `Augmented` files/folders if present; skip Alternaria/Fusarium/Verticillium).
   - Map exact subfolder names in `vision/class_map.yaml` to `cotton__bacterial_blight` and `cotton__healthy`.
   - Run `prepare_data.py --source cotton_lab --max-per-class 600 --max-side 256`.
   - Delete the zip and `data/raw/cotton_lab/*` once verified.

4. **Cotton — Field Test (`sar_cld_2024` | SAR-CLD-2024 archive):**
   - Extract **only** `Original` subfolders for `Bacterial Blight` and `Healthy` into `data/raw/sar_cld_2024/` (delete any `Augmented` folder immediately; skip `Curl Virus`).
   - Map exact subfolder names in `vision/class_map.yaml` to `cotton__bacterial_blight` and `cotton__healthy`.
   - Run `prepare_data.py --source sar_cld_2024 --max-per-class 2000 --max-side 512`.
   - Delete the archive and `data/raw/sar_cld_2024/*` once verified.

5. **Fall Armyworm & Maize — Lab (`mld_maize` | MLD archive):**
   - Extract into `data/raw/mld_maize/`. Map `Fall Armyworm -> pest__fall_armyworm` (and `Blight -> maize__northern_leaf_blight`, `Healthy -> maize__healthy` if needed).
   - Run `prepare_data.py --source mld_maize --max-per-class 600 --max-side 256`.
   - Delete the archive and `data/raw/mld_maize/*` once verified.

6. **Fall Armyworm & Maize — Field Test (`field_maize_8` | FieldMaizeLeaf-8 archive):**
   - Extract into `data/raw/field_maize_8/`. Map Fall Armyworm (`pest__fall_armyworm`) and matching Maize classes (`maize__northern_leaf_blight`, `maize__common_rust`, `maize__healthy` if present) in `vision/class_map.yaml`.
   - Run `prepare_data.py --source field_maize_8 --max-per-class 2000 --max-side 512`.
   - Delete the archive and `data/raw/field_maize_8/*` once verified.

7. **Unknown Class (`unknown` & `unknown_test`):**
   - Check if `data/raw/unknown` or `data/raw/unknown_test` already has images; if present, ingest them (`unknown` @ 256px for `train_val`, `unknown_test` @ 512px for `test`). If empty, flag in the handoff that user phone photos for `unknown` / `unknown_test` are still needed before final training.

---

### Step 3: Verify Manifest, Update Docs, and Continue Track A Pipeline
Once all downloaded datasets are processed and raw files are deleted:
1. Print the full cross-tabulation (`pd.crosstab(df['label'], df['split'])`) and per-source breakdown of `data/processed/manifest.csv`, verifying zero source leakage across `train/val` vs `test`.
2. Update `docs/DATASETS.md` with exact URLs, DOIs, licenses (CC BY 4.0 / CC0), and class counts for every ingested dataset.
3. Proceed directly with the remaining **Track A** tasks from `docs/tracks/TRACK_A_VISION.md`:
   - Build/verify `vision/train.py` and `vision/evaluate.py` (if missing or incomplete), using the GPU venv (`.\.venv-et\Scripts\python.exe`).
   - Run a fast sanity check first, then train MobileNetV3 on the full dataset, reporting **lab vs field-only** metrics separately (macro-F1, per-class precision/recall, confusion matrix).
   - Run temperature calibration & OOD threshold tuning (`vision/calibration.py`), saving `models/vision_v1.json` sidecar.
   - Export and quantize the vision model to `models/vision_v1.pte` using the pinned ExecuTorch version in `docs/versions.md`, verify parity against PyTorch on 50 test images, generate `test_vectors/vision/`, and record SHA-256 + metadata in `models/manifest.json`.
4. Update `docs/handoffs/track-a.md` using the exact session-entry template from `HANDOFF.md` with real command outputs, metrics, and any open requests/blockers, and commit cleanly on the Track A branch.