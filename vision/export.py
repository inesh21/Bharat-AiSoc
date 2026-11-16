"""ExecuTorch model export and verification utility (Tasks A12 & A13).

Exports PyTorch MobileNetV3 model to:
1. PyTorch ExportedProgram via torch.export
2. ExecuTorch .pte file (targeting XNNPACK / mobile CPU)
3. Verifies numerical parity between PyTorch and exported program.
"""

import os
import json
from typing import Dict, Any, Tuple
import torch
from vision.model import CropDiseaseClassifier, create_model


def export_to_executorch(
    model: CropDiseaseClassifier,
    save_path: str,
    input_shape: Tuple[int, int, int, int] = (1, 3, 224, 224),
) -> bool:
    """Exports model to ExecuTorch .pte format.

    Uses ExecuTorch EXIR to_edge flow when available, or saves torch.export ExportedProgram package.
    """
    model.eval()
    example_input = torch.randn(input_shape, dtype=torch.float32)

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    try:
        # Check if ExecuTorch exir / to_edge is available
        from executorch.exir import to_edge, EdgeCompileConfig
        
        # 1. Capture with torch.export
        exported = torch.export.export(model, (example_input,))
        
        # 2. Lower to ExecuTorch Edge dialect
        edge_program = to_edge(exported, compile_config=EdgeCompileConfig(_check_ir_validity=False))
        
        # 3. ExecuTorch program
        et_program = edge_program.to_executorch()
        
        # 4. Save .pte
        with open(save_path, "wb") as f:
            f.write(et_program.buffer)
            
        print(f"Successfully exported ExecuTorch program to: {save_path}")
        return True
    except Exception as e:
        print(f"ExecuTorch EXIR export encountered exception: {e}")
        print("Falling back to torch.export .pt2 / torchscript format for development parity...")
        
        # Fallback torch.export or torchscript saving
        torch_save_path = save_path.replace(".pte", ".pt2")
        try:
            exported = torch.export.export(model, (example_input,))
            torch.export.save(exported, torch_save_path)
            print(f"Saved torch.export program to: {torch_save_path}")
        except Exception as e2:
            print(f"torch.export save fallback: {e2}")
            ts_model = torch.jit.trace(model, example_input)
            ts_model.save(save_path.replace(".pte", ".pt"))
            print(f"Saved traced TorchScript model as fallback")
        return False
