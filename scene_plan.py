import json
from dataclasses import dataclass
from typing import Any


SCENEPLAN_MARKER = "---SCENEPLAN---"


@dataclass
class ScenePlan:
    reply: str
    scene_append: str
    mood: str = "neutral"
    location: str = "unspecified"
    change_scene: bool = False


def extract_character_text(raw: str) -> str:
    if not raw:
        return ""
    head, _, _ = raw.partition(SCENEPLAN_MARKER)
    return head.strip()


def extract_sceneplan_json(raw: str) -> str:
    if not raw:
        return ""
    _, sep, tail = raw.partition(SCENEPLAN_MARKER)
    if not sep:
        return ""
    return tail.strip()


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return False


def parse_scene_plan(raw: str, user_text_fallback: str) -> ScenePlan:
    scene_json = extract_sceneplan_json(raw)
    data: Any = None
    if scene_json:
        try:
            data = json.loads(scene_json)
        except json.JSONDecodeError:
            data = None

    if isinstance(data, dict):
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = extract_character_text(raw)

        scene_append = data.get("scene_append")
        if not isinstance(scene_append, str) or not scene_append.strip():
            scene_append = user_text_fallback

        mood = data.get("mood")
        if not isinstance(mood, str) or not mood.strip():
            mood = "neutral"

        location = data.get("location")
        if not isinstance(location, str) or not location.strip():
            location = "unspecified"

        change_scene = _coerce_bool(data.get("change_scene"))
        return ScenePlan(
            reply=reply.strip(),
            scene_append=scene_append.strip(),
            mood=mood.strip(),
            location=location.strip(),
            change_scene=change_scene,
        )

    return ScenePlan(
        reply=extract_character_text(raw),
        scene_append=user_text_fallback.strip(),
        mood="neutral",
        location="unspecified",
        change_scene=False,
    )


def has_strong_scene_change(scene_append: str) -> bool:
    if not scene_append:
        return False
    tokens = scene_append.lower()
    keywords = (
        "outfit",
        "clothes",
        "dress",
        "uniform",
        "hoodie",
        "jacket",
        "pose",
        "standing",
        "sitting",
        "lying",
        "kneeling",
        "crouching",
        "running",
        "walking",
        "close-up",
        "wide shot",
        "camera",
        "angle",
        "lighting",
        "sunset",
        "night",
        "day",
        "indoors",
        "outdoors",
        "room",
        "bedroom",
        "cafe",
        "street",
        "park",
        "beach",
        "rooftop",
        "forest",
        "city",
        "bar",
        "office",
        "school",
        "table",
        "window",
    )
    return any(keyword in tokens for keyword in keywords)
