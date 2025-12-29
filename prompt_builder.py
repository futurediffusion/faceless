from typing import List


def build_positive_prompt(quality: str, visual_base: str, scene_append: str) -> str:
    parts: List[str] = []
    for value in (quality.strip(), visual_base.strip(), scene_append.strip()):
        if value:
            parts.append(value)
    return ", ".join(parts) if parts else "high quality, detailed"
