import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "llm_provider": "gemini",
    "gemini_api_key": "",
    "ollama_model": "qwen2.5:7b-instruct",
    "prefer_ollama_while_busy": True,
}


def load_config(base_dir: Path) -> Dict[str, Any]:
    path = base_dir / "config.json"
    if not path.exists():
        save_config(path, DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        save_config(path, DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    if not isinstance(data, dict):
        save_config(path, DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k in merged})
    if merged != data:
        save_config(path, merged)
    return merged


def save_config(path: Path, config: Dict[str, Any]) -> None:
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
