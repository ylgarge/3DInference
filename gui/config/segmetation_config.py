# segmentation_config.py

import json, pathlib

SEGMENTATION_CONFIG_FILE = pathlib.Path(__file__).resolve().parent / "../../config/segmentations.json"

# Varsayılan değerler
DEFAULT_CONFIG = {
    "source_mode": "offline",        # "offline" veya "online"
    "ply_file_path": "",             # offline .ply dosyası
    "algorithm": "RANSAC",           # "RANSAC" veya "SAM3D" vs.
    "ransac_params": {
        "distance_threshold": 0.1,
        "num_iterations": 1000,
        "eps": 0.01,
        "min_points": 10
    }
}

def load_segmentation_config() -> dict:
    """segmentations.json varsa yükler, yoksa varsayılanı döner."""
    if not SEGMENTATION_CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(SEGMENTATION_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # JSON içinde olmayan alanlar varsa default ile birleştir
        cfg = dict(DEFAULT_CONFIG)
        # ransac_params’ın altını da birleştirmek gerekebilir
        cfg.update(data)
        rp = dict(DEFAULT_CONFIG["ransac_params"])
        rp.update(cfg.get("ransac_params", {}))
        cfg["ransac_params"] = rp
        return cfg
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)

def save_segmentation_config(cfg: dict):
    """cfg sözlüğünü segmentations.json’a kaydeder."""
    with open(SEGMENTATION_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
