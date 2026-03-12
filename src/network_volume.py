"""
Network Volume diagnostics for worker-comfyui.

This module provides tools to debug network volume model path issues.
Enable diagnostics by setting NETWORK_VOLUME_DEBUG=true.
"""

import os

# Expected model types and recognized file extensions.
MODEL_TYPES = {
    "checkpoints": [".safetensors", ".ckpt", ".pt", ".pth", ".bin"],
    "clip": [".safetensors", ".pt", ".bin"],
    "clip_vision": [".safetensors", ".pt", ".bin"],
    "configs": [".yaml", ".json"],
    "controlnet": [".safetensors", ".pt", ".pth", ".bin"],
    "diffusion_models": [".safetensors", ".pt", ".pth", ".bin"],
    "embeddings": [".safetensors", ".pt", ".bin"],
    "loras": [".safetensors", ".pt"],
    "model_patches": [".safetensors", ".pt", ".pth", ".bin"],
    "text_encoders": [".safetensors", ".pt", ".bin"],
    "upscale_models": [".safetensors", ".pt", ".pth"],
    "vae": [".safetensors", ".pt", ".bin"],
    "unet": [".safetensors", ".pt", ".bin"],
}


def is_network_volume_debug_enabled():
    """Check if network volume debug mode is enabled."""
    return os.environ.get("NETWORK_VOLUME_DEBUG", "false").lower() == "true"


def run_network_volume_diagnostics():
    """
    Run network volume diagnostics.
    Only runs when NETWORK_VOLUME_DEBUG=true.
    """
    print("=" * 70)
    print("NETWORK VOLUME DIAGNOSTICS (NETWORK_VOLUME_DEBUG=true)")
    print("=" * 70)

    extra_model_paths_file = "/comfyui/extra_model_paths.yaml"
    print("\n[1] Checking extra_model_paths.yaml configuration...")
    if os.path.isfile(extra_model_paths_file):
        print(f"    FOUND: {extra_model_paths_file}")
        with open(extra_model_paths_file, "r", encoding="utf-8") as f:
            content = f.read()
            print("\n    Configuration content:")
            for line in content.split("\n"):
                print(f"      {line}")
    else:
        print(f"    NOT FOUND: {extra_model_paths_file}")
        print("    This file is required for ComfyUI to find network volume models.")

    runpod_volume = "/runpod-volume"
    print(f"\n[2] Checking network volume mount at {runpod_volume}...")
    if os.path.isdir(runpod_volume):
        print(f"    MOUNTED: {runpod_volume}")
    else:
        print(f"    NOT MOUNTED: {runpod_volume}")
        print("    Attach a network volume to your serverless endpoint.")
        print("=" * 70)
        return

    print("\n[3] Resolving configured model roots...")
    model_roots = get_model_roots(extra_model_paths_file)
    if not model_roots:
        model_roots = [os.path.join(runpod_volume, "models")]

    for model_root in model_roots:
        if os.path.isdir(model_root):
            print(f"    FOUND: {model_root}")
        else:
            print(f"    NOT FOUND: {model_root}")

    print("\n[4] Scanning model directories...")
    found_any_models = False
    found_zero_byte_models = False
    seen_models = {}
    for model_root in model_roots:
        print(f"\n    Root: {model_root}")
        for model_type, extensions in MODEL_TYPES.items():
            model_path = os.path.join(model_root, model_type)
            if not os.path.isdir(model_path):
                print(f"      {model_type}/: (directory not found)")
                continue

            files = []
            try:
                for filename in os.listdir(model_path):
                    file_path = os.path.join(model_path, filename)
                    if not os.path.isfile(file_path):
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in extensions:
                        size = os.path.getsize(file_path)
                        if size == 0:
                            files.append(
                                f"{filename} ({format_size(size)}) <- PROBLEM: empty file"
                            )
                            found_zero_byte_models = True
                        else:
                            files.append(f"{filename} ({format_size(size)})")
                        found_any_models = True
                        seen_models.setdefault((model_type, filename), []).append(file_path)
                    else:
                        files.append(f"{filename} (ignored - invalid extension)")
            except Exception as e:
                print(f"      {model_type}/: Error reading directory - {e}")
                continue

            if files:
                print(f"      {model_type}/:")
                for entry in files:
                    print(f"        - {entry}")
            else:
                print(f"      {model_type}/: (empty)")

    print("\n[5] Summary")
    if found_any_models:
        print("    Models found on network volume.")
    else:
        print("    No valid model files found on network volume.")
        print("    Check file extensions and model folder placement.")
    if found_zero_byte_models:
        print("    PROBLEM: One or more model files are zero bytes and will fail to load.")
        print("    Re-upload or delete the empty files so the baked image models can be used.")
    duplicate_models = {
        key: paths for key, paths in seen_models.items() if len(paths) > 1
    }
    if duplicate_models:
        print("    WARNING: Duplicate model filenames were found across model roots.")
        print("    Remove duplicates to avoid loading the wrong copy.")
        for (model_type, filename), paths in duplicate_models.items():
            print(f"    {model_type}/{filename}")
            for path in paths:
                print(f"      - {path}")

    print_expected_structure()
    print("=" * 70)


def get_model_roots(extra_model_paths_file):
    """Read extra model path roots from ComfyUI config."""
    if not os.path.isfile(extra_model_paths_file):
        return []

    try:
        with open(extra_model_paths_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        print(f"    WARNING: Could not parse {extra_model_paths_file}: {exc}")
        return []

    roots = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped.startswith("base_path:"):
            continue
        base_path = stripped.split(":", 1)[1].strip()
        if not base_path:
            continue
        roots.append(os.path.join(base_path, "models"))

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(roots))


def print_expected_structure():
    """Print the expected network volume directory structure."""
    print("\n    Expected directory structure:")
    print("    /runpod-volume/")
    print("    └── models/")
    print("        ├── checkpoints/      <- Put checkpoint files here")
    print("        ├── loras/            <- Put LoRA files here")
    print("        ├── vae/              <- Put VAE files here")
    print("        ├── clip/             <- Put CLIP files here")
    print("        ├── clip_vision/      <- Put CLIP vision files here")
    print("        ├── controlnet/       <- Put ControlNet files here")
    print("        ├── diffusion_models/ <- Put diffusion model files here")
    print("        ├── embeddings/       <- Put embedding files here")
    print("        ├── model_patches/    <- Put model patch files here")
    print("        ├── text_encoders/    <- Put text encoder files here")
    print("        ├── upscale_models/   <- Put upscaler files here")
    print("        ├── unet/             <- Put UNet files here")
    print("        └── configs/          <- Put config files here")


def format_size(size_bytes):
    """Format bytes into a readable size string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
