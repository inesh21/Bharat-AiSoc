"""Generate the local Android parity bundle from the processed test manifest."""

import argparse
import csv
import json
import logging
import random
from collections import defaultdict
from io import BytesIO
from pathlib import Path, PureWindowsPath
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import torch
from executorch.runtime import Runtime
from PIL import Image, ImageOps
from torchvision.transforms.functional import normalize, to_tensor

LOG = logging.getLogger(__name__)
SEED = 42
CASE_COUNT = 50
UNKNOWN_COUNT = 8


def resolve_image(path: str, manifest: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() and candidate.is_file():
        return candidate
    # prepare_data.py writes absolute paths. Rebase a moved dataset at images/.
    parts = PureWindowsPath(path).parts
    if "images" in parts:
        return manifest.parent.joinpath(*parts[parts.index("images") :])
    return manifest.parent / candidate


def select_cases(manifest: Path, labels: list[str]) -> list[tuple[str, Path]]:
    by_crop: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    with manifest.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            label = row["label"]
            if row["split"] == "test" and label in labels:
                by_crop[label.split("__")[0]].append(
                    (label, resolve_image(row["path"], manifest))
                )

    rng = random.Random(SEED)
    crops = sorted({label.split("__")[0] for label in labels if "__" in label})
    selected = rng.sample(by_crop["unknown"], UNKNOWN_COUNT)
    remaining = []
    for crop in crops:
        samples = sorted(by_crop[crop])
        if not samples:
            raise ValueError(f"No test images for {crop}")
        selected.append(samples.pop(rng.randrange(len(samples))))
        remaining.extend(samples)
    selected.extend(rng.sample(remaining, CASE_COUNT - len(selected)))
    rng.shuffle(selected)
    return selected


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    config = json.loads((root / "models/vision_v1.json").read_text(encoding="utf-8"))
    parity = root / "test_vectors/vision/parity_test_vectors.json"
    tolerance = config.get("verification", {}).get("max_abs_diff")
    if tolerance is None:
        tolerance = json.loads(parity.read_text(encoding="utf-8"))["tolerance"]
    labels = config["labels"]
    width, height = config["image_size"]
    norm = config["normalization"]
    manifest = root / "data/processed/manifest.csv"
    selected = select_cases(manifest, labels)

    torch.set_num_threads(4)
    reference = torch.jit.load(str(root / config["torchscript_file"]), map_location="cpu")
    reference.eval()
    program = Runtime.get().load_program(root / config["pte_file"])
    forward = program.load_method("forward")

    output = root / "test_vectors/vision/device_vectors.zip"
    temporary = output.with_suffix(".zip.tmp")
    cases = []
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED) as bundle, torch.inference_mode():
            for index, (label, path) in enumerate(selected):
                with Image.open(path) as original:
                    image = ImageOps.exif_transpose(original).convert("RGB")
                    image = image.resize((width, height), Image.Resampling.BILINEAR)
                tensor = normalize(to_tensor(image), norm["mean"], norm["std"]).unsqueeze(0)
                pt = reference(tensor).numpy()[0]
                et = forward.execute([tensor])[0].numpy()[0]
                error = float(np.max(np.abs(pt - et)))
                if not np.isfinite(error) or error > tolerance or pt.argmax() != et.argmax():
                    raise ValueError(f"Host parity failed for case {index}: max error {error}")

                image_bytes = BytesIO()
                image.save(image_bytes, "PNG")
                image_name = f"img_{index:03d}.png"
                tensor_name = f"input_{index:03d}.bin"
                bundle.writestr(f"device/{image_name}", image_bytes.getvalue())
                bundle.writestr(
                    f"device/{tensor_name}", tensor.numpy().astype("<f4").tobytes()
                )
                cases.append(
                    {
                        "test_id": index,
                        "true_label": label,
                        "input_bin": tensor_name,
                        "image": image_name,
                        "pt_logits": pt.tolist(),
                        "et_logits": et.tolist(),
                        "et_top1_idx": int(et.argmax()),
                        "max_abs_diff": error,
                    }
                )
            bundle.writestr(
                "device/expected.json",
                json.dumps(
                    {
                        "model": Path(config["pte_file"]).name,
                        "n_cases": len(cases),
                        "shape": [1, 3, height, width],
                        "tolerance": tolerance,
                        "cases": cases,
                    },
                    allow_nan=False,
                ),
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    LOG.info("Wrote %s. %d cases, max host error %.3g (tolerance %.3g).",
             output, len(cases), max(case["max_abs_diff"] for case in cases), tolerance)


if __name__ == "__main__":
    main()

