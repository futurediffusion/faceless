import json
from typing import Any, List, Optional

from llm_contract import DEFAULT_SCENE_APPEND, SCENEPLAN_MARKER
from scene_plan import ScenePlan


DEFAULT_REPLY = "..."


def _extract_reply_text(raw: str) -> str:
    if not raw:
        return ""
    head, _, _ = raw.partition(SCENEPLAN_MARKER)
    return head.strip()


def _find_json_blocks(text: str) -> List[str]:
    blocks: List[str] = []
    start: Optional[int] = None
    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(text[start : idx + 1])
                start = None

    return blocks


def _parse_last_json(text: str) -> Optional[dict]:
    for block in reversed(_find_json_blocks(text)):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_sceneplan(llm_text: str) -> ScenePlan:
    if not llm_text:
        return ScenePlan(
            reply=DEFAULT_REPLY,
            scene_append=DEFAULT_SCENE_APPEND,
            mood="neutral",
            location="",
            visual_anchor="",
            change_scene=False,
        )

    _, sep, tail = llm_text.partition(SCENEPLAN_MARKER)
    data: Optional[dict] = None
    if sep:
        data = _parse_last_json(tail)

    reply_text = _extract_reply_text(llm_text)
    reply = reply_text.strip() or DEFAULT_REPLY

    if isinstance(data, dict):
        reply_val = data.get("reply")
        if isinstance(reply_val, str) and reply_val.strip():
            reply = reply_val.strip()

        scene_append_val = data.get("scene_append")
        scene_append = (
            scene_append_val.strip()
            if isinstance(scene_append_val, str) and scene_append_val.strip()
            else DEFAULT_SCENE_APPEND
        )

        mood_val = data.get("mood")
        mood = mood_val.strip() if isinstance(mood_val, str) and mood_val.strip() else "neutral"

        location_val = data.get("location")
        location = location_val.strip() if isinstance(location_val, str) and location_val.strip() else ""

        visual_anchor_val = data.get("visual_anchor")
        visual_anchor = (
            visual_anchor_val.strip()
            if isinstance(visual_anchor_val, str) and visual_anchor_val.strip()
            else ""
        )

        change_scene_val = data.get("change_scene")
        change_scene = change_scene_val is True

        return ScenePlan(
            reply=reply,
            scene_append=scene_append,
            mood=mood,
            location=location,
            visual_anchor=visual_anchor,
            change_scene=change_scene,
        )

    return ScenePlan(
        reply=reply,
        scene_append=DEFAULT_SCENE_APPEND,
        mood="neutral",
        location="",
        visual_anchor="",
        change_scene=False,
    )
