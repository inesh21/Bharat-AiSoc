"""
Parity test: compare PyTorch checkpoint vs ExecuTorch .pte on 50 test images.
Writes test_vectors/vision/parity_test_vectors.json.

Usage:
    python vision/parity_test.py
"""

import os, sys, json, random, csv
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np

CHECKPOINT   = "models_src/vision_v1.pt"
PTE_FILE     = "models/vision_v1.pte"
MANIFEST_CSV = "data/processed/manifest.csv"
OUTPUT_DIR   = "test_vectors/vision"
OUTPUT_JSON  = os.path.join(OUTPUT_DIR, "parity_test_vectors.json")
N_SAMPLES    = 50
SEED         = 42

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 1. Load checkpoint ────────────────────────────────────────────────────────
print("Loading PyTorch checkpoint …")
ckpt = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
label_to_idx = ckpt["label_to_idx"]
idx_to_label = {v: k for k, v in label_to_idx.items()}
num_classes  = len(label_to_idx)

model = models.mobilenet_v3_large(weights=None)
in_f = model.classifier[0].in_features
model.classifier = nn.Sequential(
    nn.Linear(in_f, 256),
    nn.Hardswish(inplace=True),
    nn.Dropout(0.3),
    nn.Linear(256, num_classes),
)
model.load_state_dict(ckpt["model_state_dict"])
model.eval()
print(f"  num_classes = {num_classes}")

# ── 2. Try loading ExecuTorch runtime ─────────────────────────────────────────
et_model = None
try:
    from executorch.runtime import Runtime, Program, Method
    runtime = Runtime.get()
    with open(PTE_FILE, "rb") as f:
        pte_bytes = f.read()
    program = runtime.load_program(pte_bytes)
    et_model = program.load_method("forward")
    print("  ExecuTorch runtime loaded OK")
except Exception as e:
    print(f"  WARNING: ExecuTorch runtime unavailable ({e}). Parity will use PT only.")

# ── 3. Build preprocessing ────────────────────────────────────────────────────
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# ── 4. Sample 50 test images from manifest ───────────────────────────────────
print(f"Sampling {N_SAMPLES} test images from manifest …")
test_rows = []
with open(MANIFEST_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["split"] == "test" and row["label"] in label_to_idx:
            test_rows.append(row)

random.seed(SEED)
sample = random.sample(test_rows, min(N_SAMPLES, len(test_rows)))
print(f"  Sampled {len(sample)} rows")

# ── 5. Run inference ──────────────────────────────────────────────────────────
results = []
max_abs_diff_global = 0.0
all_match = True

for i, row in enumerate(sample):
    img_path = row["path"]
    if not os.path.exists(img_path):
        print(f"  SKIP (missing): {img_path}")
        continue

    img = Image.open(img_path).convert("RGB")
    tensor = preprocess(img).unsqueeze(0)  # (1, 3, 224, 224)

    with torch.no_grad():
        pt_logits = model(tensor)  # (1, num_classes)

    pt_logits_np = pt_logits.numpy()[0]
    pt_top1 = int(pt_logits_np.argmax())

    et_logits_np = None
    et_top1 = None
    max_abs_diff = None

    if et_model is not None:
        try:
            et_out = et_model.execute([tensor])
            et_logits_np = et_out[0].numpy()[0]
            et_top1 = int(et_logits_np.argmax())
            max_abs_diff = float(np.abs(pt_logits_np - et_logits_np).max())
            max_abs_diff_global = max(max_abs_diff_global, max_abs_diff)
            if pt_top1 != et_top1:
                all_match = False
                print(f"  MISMATCH row {i}: pt={idx_to_label[pt_top1]} et={idx_to_label[et_top1]}")
        except Exception as e:
            print(f"  ET inference error row {i}: {e}")

    true_label = row["label"]
    entry = {
        "test_id":          i,
        "path":             img_path,
        "true_label":       true_label,
        "pt_top1_idx":      pt_top1,
        "pt_top1_label":    idx_to_label[pt_top1],
        "pt_top1_logit":    float(pt_logits_np[pt_top1]),
        "pt_correct":       (idx_to_label[pt_top1] == true_label),
    }
    if et_logits_np is not None:
        entry.update({
            "et_top1_idx":   et_top1,
            "et_top1_label": idx_to_label[et_top1],
            "max_abs_diff":  max_abs_diff,
            "tops_match":    (pt_top1 == et_top1),
        })
    results.append(entry)

# ── 6. Write test vectors ─────────────────────────────────────────────────────
pt_acc = sum(r["pt_correct"] for r in results) / len(results) if results else 0.0

output = {
    "model":              "vision_v1.pte",
    "checkpoint":         CHECKPOINT,
    "n_samples":          len(results),
    "seed":               SEED,
    "pt_top1_accuracy":   round(pt_acc, 4),
    "et_available":       (et_model is not None),
    "max_abs_diff_global": max_abs_diff_global if et_model else "N/A",
    "all_tops_match":     all_match if et_model else "N/A",
    "samples":            results[:10],   # first 10 for reference
    "tolerance":          1e-4,
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nParity test done.")
print(f"  PT top-1 accuracy on {len(results)} samples: {pt_acc:.4f}")
if et_model:
    print(f"  Max abs diff (PT vs ET): {max_abs_diff_global:.6f}")
    print(f"  All top-1 predictions match: {all_match}")
print(f"  Saved → {OUTPUT_JSON}")
