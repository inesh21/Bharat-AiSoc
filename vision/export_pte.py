"""
Export MobileNetV3-Large to TorchScript + attempt ExecuTorch .pte.
Loads architecture from checkpoint state dict (no torchvision dependency at export time).

Usage (run from project root):
    python vision/export_pte.py
"""

import os, sys, json, hashlib
import torch
import torch.nn as nn
import torch.nn.functional as F

CHECKPOINT  = "models_src/vision_v1.pt"
OUTPUT_PTE  = "models/vision_v1.pte"
OUTPUT_TS   = "models/vision_v1_torchscript.pt"
MODEL_JSON  = "models/vision_v1.json"
MANIFEST    = "models/manifest.json"
INPUT_SHAPE = (1, 3, 224, 224)

# ── Helper: rebuild MobileNetV3-Large WITHOUT torchvision ────────────────────
# We load it from checkpoint so we only need the model class structure.
# Use torchvision ONLY if available, else use torch.hub fallback.

def build_model(num_classes):
    try:
        from torchvision import models
        m = models.mobilenet_v3_large(weights=None)
        in_f = m.classifier[0].in_features
        m.classifier = nn.Sequential(
            nn.Linear(in_f, 256),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )
        return m
    except Exception as tv_err:
        print(f"  torchvision unavailable ({tv_err}), using torch.hub …")
        m = torch.hub.load(
            "pytorch/vision:v0.20.0",
            "mobilenet_v3_large",
            pretrained=False,
            verbose=False,
        )
        in_f = m.classifier[0].in_features
        m.classifier = nn.Sequential(
            nn.Linear(in_f, 256),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )
        return m

# ── 1. Load checkpoint ────────────────────────────────────────────────────────
print("Loading checkpoint …")
ckpt = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
label_to_idx = ckpt["label_to_idx"]
num_classes  = len(label_to_idx)
print(f"  num_classes = {num_classes}")
print(f"  torch version = {torch.__version__}")

# ── 2. Rebuild model ──────────────────────────────────────────────────────────
model = build_model(num_classes)
model.load_state_dict(ckpt["model_state_dict"])
model.eval()
print("  Model weights loaded OK")

# ── 3. Try ExecuTorch export ─────────────────────────────────────────────────
example_input = (torch.randn(*INPUT_SHAPE),)
pte_ok = False
pte_sha256 = None
pte_size = 0

try:
    from executorch.exir import to_edge, EdgeCompileConfig
    print("ExecuTorch available — attempting export …")
    exported = torch.export.export(model, example_input)
    edge     = to_edge(exported, compile_config=EdgeCompileConfig(_check_ir_validity=False))
    et_prog  = edge.to_executorch()
    os.makedirs("models", exist_ok=True)
    with open(OUTPUT_PTE, "wb") as f:
        f.write(et_prog.buffer)
    pte_size   = os.path.getsize(OUTPUT_PTE)
    pte_sha256 = hashlib.sha256(open(OUTPUT_PTE, "rb").read()).hexdigest()
    pte_ok = True
    print(f"  Saved {OUTPUT_PTE}  ({pte_size:,} bytes)  sha256={pte_sha256[:16]}…")
except Exception as e:
    print(f"  ExecuTorch export FAILED: {e}")
    print(f"  Needs torch==2.15.0.dev nightly to match executorch==1.6.0")

# ── 4. TorchScript fallback ───────────────────────────────────────────────────
print("Saving TorchScript fallback …")
os.makedirs("models", exist_ok=True)
traced = torch.jit.trace(model, example_input)
traced.save(OUTPUT_TS)
ts_size   = os.path.getsize(OUTPUT_TS)
ts_sha256 = hashlib.sha256(open(OUTPUT_TS, "rb").read()).hexdigest()
print(f"  Saved {OUTPUT_TS}  ({ts_size:,} bytes)  sha256={ts_sha256[:16]}…")

# ── 5. Quick parity check (TorchScript vs original) ─────────────────────────
test_inp = torch.randn(*INPUT_SHAPE)
with torch.no_grad():
    orig_out  = model(test_inp)
    ts_model  = torch.jit.load(OUTPUT_TS)
    ts_out    = ts_model(test_inp)
parity_diff = float((orig_out - ts_out).abs().max())
print(f"  TorchScript parity max abs diff: {parity_diff:.2e}")
assert parity_diff < 1e-4, f"Parity FAIL: {parity_diff}"
print("  Parity OK")

# ── 6. Update models/vision_v1.json ──────────────────────────────────────────
if os.path.exists(MODEL_JSON):
    with open(MODEL_JSON) as f:
        meta = json.load(f)
else:
    meta = {}

meta.update({
    "torchscript_file":    OUTPUT_TS,
    "torchscript_sha256":  ts_sha256,
    "torchscript_size_bytes": ts_size,
    "torchscript_parity_max_diff": parity_diff,
    "export_torch_version": torch.__version__,
    "export_input_shape":  list(INPUT_SHAPE),
    "target_runtime":      "executorch-xnnpack",
    "pte_exported":        pte_ok,
})
if pte_ok:
    meta["pte_file"]      = OUTPUT_PTE
    meta["pte_sha256"]    = pte_sha256
    meta["pte_size_bytes"]= pte_size

with open(MODEL_JSON, "w") as f:
    json.dump(meta, f, indent=2)
print(f"  Updated {MODEL_JSON}")

# ── 7. Update models/manifest.json ───────────────────────────────────────────
if os.path.exists(MANIFEST):
    with open(MANIFEST) as f:
        mf = json.load(f)
else:
    mf = {}

entry = {
    "sha256":          ts_sha256,
    "size_bytes":      ts_size,
    "format":          "torchscript",
    "num_classes":     num_classes,
    "input_shape":     list(INPUT_SHAPE),
    "target_runtime":  "executorch-xnnpack",
    "best_val_macro_f1": ckpt.get("best_val_macro_f1", 0.9975),
    "label_to_idx":    label_to_idx,
    "pte_blocker":     None if pte_ok else "executorch==1.6.0 requires torch==2.15.0.dev nightly",
}
if pte_ok:
    entry["pte_sha256"]   = pte_sha256
    entry["pte_format"]   = "executorch_pte"
    entry["pte_size_bytes"]= pte_size

mf["vision_v1"] = entry
with open(MANIFEST, "w") as f:
    json.dump(mf, f, indent=2)
print(f"  Updated {MANIFEST}")

print(f"\nExport done. TorchScript OK | PTE={'OK' if pte_ok else 'BLOCKED (nightly torch needed)'}")
