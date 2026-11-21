"""Phase 4.1 – Export data files for the Android app.

Converts the Python-side knowledge and config files into JSON assets that
the app can read from its `assets/` directory.  Run this whenever the Python
source files change.

Output files (written to app_android/app/src/main/assets/):
  kb.json            – flat knowledge base entries
  rules.json         – chemical / organic rules
  clarifications.json – clarifying-question pairs
  phrases.json        – localised phrase table
  labels.json         – class label list (copy of root labels.json)

A SHA-256 hash of each output is written to tools/asset_hashes.json so the
app unit test can detect drift.
"""

import hashlib
import json
import os
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(REPO_ROOT, "app_android", "app", "src", "main", "assets")
HASH_FILE = os.path.join(REPO_ROOT, "tools", "asset_hashes.json")

SOURCES = {
    "kb.json": os.path.join(REPO_ROOT, "knowledge", "kb.json"),
    "rules.json": os.path.join(REPO_ROOT, "knowledge", "rules.yaml"),
    "clarifications.json": os.path.join(REPO_ROOT, "knowledge", "clarifications.yaml"),
    "labels.json": os.path.join(REPO_ROOT, "labels.json"),
}

# Phrases come from the language_layer module directly
LANGUAGE_LAYER_PATH = os.path.join(REPO_ROOT, "llm", "language_layer.py")

os.makedirs(ASSETS_DIR, exist_ok=True)


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data) -> str:
    """Writes data as indented JSON and returns the SHA-256 of the written bytes."""
    encoded = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    with open(path, "wb") as f:
        f.write(encoded)
    return sha256_of_bytes(encoded)


def export_kb() -> str:
    src = SOURCES["kb.json"]
    data = load_json(src)
    dst = os.path.join(ASSETS_DIR, "kb.json")
    sha = write_json(dst, data)
    print(f"  kb.json        -> {dst}  (sha256: {sha[:16]}…)")
    return sha


def export_rules() -> str:
    """Convert rules.yaml to a flat JSON structure the app can parse."""
    src = SOURCES["rules.json"]
    raw = load_yaml(src)

    # Build a normalised structure
    rules_out = {
        "version": raw.get("version", "1.0"),
        "region_scope": raw.get("region_scope", ""),
        "chemicals": {},
        "organic_options": {},
        "severity_thresholds": raw.get("severity_thresholds", {}),
        "restricted_chemicals": raw.get("restricted_chemicals", []),
        "extension_officer_triggers": raw.get("extension_officer_triggers", []),
    }

    for key, val in raw.get("chemicals", {}).items():
        rules_out["chemicals"][key] = val  # keep all fields

    for key, val in raw.get("organic_options", {}).items():
        rules_out["organic_options"][key] = val

    dst = os.path.join(ASSETS_DIR, "rules.json")
    sha = write_json(dst, rules_out)
    print(f"  rules.json     -> {dst}  (sha256: {sha[:16]}…)")
    return sha


def export_clarifications() -> str:
    src = SOURCES["clarifications.json"]
    raw = load_yaml(src)
    dst = os.path.join(ASSETS_DIR, "clarifications.json")
    sha = write_json(dst, raw)
    print(f"  clarifications.json -> {dst}  (sha256: {sha[:16]}…)")
    return sha


def export_labels() -> str:
    src = SOURCES["labels.json"]
    data = load_json(src)
    dst = os.path.join(ASSETS_DIR, "labels.json")
    sha = write_json(dst, data)
    print(f"  labels.json    -> {dst}  (sha256: {sha[:16]}…)")
    return sha


def export_phrases() -> str:
    """Extract LOCALIZED_PHRASES from language_layer.py and export as JSON."""
    # We import the module from the repo
    sys.path.insert(0, REPO_ROOT)
    from llm.language_layer import LOCALIZED_PHRASES  # noqa: PLC0415

    # Also add English "phrases" so the app always has a complete table
    phrases_out = dict(LOCALIZED_PHRASES)
    phrases_out["en"] = {
        "diagnosis_prefix": "Diagnosis:",
        "actions_prefix": "Immediate actions:",
        "prevention_prefix": "Long-term prevention:",
        "unknown_warning": (
            "The condition could not be identified. "
            "Please consult your local agricultural extension officer (KVK)."
        ),
        "healthy_msg": "Your crop appears healthy. Continue routine care.",
    }

    dst = os.path.join(ASSETS_DIR, "phrases.json")
    sha = write_json(dst, phrases_out)
    print(f"  phrases.json   -> {dst}  (sha256: {sha[:16]}…)")
    return sha


def main() -> None:
    print("export_for_android.py – exporting knowledge assets to Android assets/")
    print(f"  Target: {ASSETS_DIR}\n")

    hashes = {
        "kb.json": export_kb(),
        "rules.json": export_rules(),
        "clarifications.json": export_clarifications(),
        "labels.json": export_labels(),
        "phrases.json": export_phrases(),
    }

    with open(HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"\nHash manifest written to {HASH_FILE}")
    print("Done. Run `./gradlew testDebugUnitTest` to verify drift detection.")


if __name__ == "__main__":
    main()
