# versions.md: Pinned versions

Everything here is pinned across all machines and the app. Change only through a decision record (`docs/decisions/`) and agreement of all three tracks. Fill in on Day 1.

| Item | Version / value | Notes |
|---|---|---|
| ExecuTorch | TODO (git tag or commit) | App runtime and all exported models must use this |
| PyTorch | TODO | Match what ExecuTorch requires |
| Python | 3.10 to 3.12 | |
| Android Studio | TODO | |
| Android SDK / NDK | TODO | NDK exactly as the ExecuTorch Android README requires |
| Android minSdk / targetSdk | TODO | |
| Target phone | TODO (model, RAM, Android version) | |
| Llama base model | Llama-3.2-1B-Instruct (3B under evaluation) | Check license and attribution |
| Vision backbone | TODO | |
| STT engine | TODO | |
| TTS engine | TODO | |

## Working export commands (copy exactly what worked)

### Llama export
```
TODO(track-b): exact command, flags, quantization scheme, and the ExecuTorch version it was run on
```

### Vision export
```
TODO(track-a): exact command and quantization/calibration details
```

### Android build
```
TODO(track-c): exact build and install steps
```
