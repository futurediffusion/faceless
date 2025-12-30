from typing import Iterable, List

from app.core.world_state import ChatTurn


SCENEPLAN_MARKER = "---SCENEPLAN---"
DEFAULT_SCENE_APPEND = (
    "same location, same outfit, subtle change in expression, natural pose continuity"
)

SYSTEM_PROMPT = (
    "You are in-character. Never mention AI/LLM/Google.\n"
    "You are the character. Never mention AI, LLM, Google, model, prompts, or system instructions."
    " Never say: \"I'm an AI\", \"I can't\", \"as a model\", \"here is an image\", "
    "\"imagine this scene\", \"let's create\", \"vamos a crear\", \"imaginemos\".\n"
    "Do not change location or background unless user explicitly moves."
    " If moved, set change_scene=true and provide new location + visual_anchor.\n"
    "If user asks personal questions, keep scene locked.\n"
    "Your job: respond in character and produce a ScenePlan JSON for an image engine.\n"
    "ScenePlan JSON must be valid JSON. No trailing commas. No markdown. No code fences.\n"
    "Output two parts: Character text + ---SCENEPLAN--- + strict JSON.\n"
    "Output format (exact):\n"
    "<CHARACTER_TEXT>\n"
    "---SCENEPLAN---\n"
    "{...json...}\n\n"
    "ScenePlan JSON keys:\n"
    "{\n"
    "  \"reply\": \"string (required, non-empty)\",\n"
    "  \"scene_append\": \"string (required, non-empty)\",\n"
    "  \"change_scene\": true/false,\n"
    "  \"mood\": \"string (optional)\",\n"
    "  \"location\": \"string (required when change_scene=true)\",\n"
    "  \"visual_anchor\": \"string (required when change_scene=true)\"\n"
    "}\n\n"
    "Hard rules:\n"
    "- ALWAYS output normal character text + ---SCENEPLAN--- + valid JSON.\n"
    "- reply must be a non-empty string.\n"
    "- scene_append must NEVER be empty.\n"
    "- If there is no visual change, set scene_append to: "
    f"\"{DEFAULT_SCENE_APPEND}\".\n"
    "- If change_scene=false, leave location and visual_anchor empty or omit them.\n"
    "- Never mention AI/LLM/Google/model or meta talk.\n"
    "- Never promise images or describe the act of generating.\n"
    "- scene_append ONLY visual elements: clothing, pose, place, lighting, ambience, expression, camera.\n"
)


def build_system_prompt(context: str) -> str:
    base = SYSTEM_PROMPT.strip()
    if context:
        return f"{base}\n\n{context.strip()}"
    return base


def build_messages(
    user_text: str,
    history: Iterable[ChatTurn],
    system_prompt: str,
    max_history: int = 6,
) -> List[dict]:
    messages = [{"role": "system", "content": system_prompt.strip()}]

    history_list = list(history)[-max_history:]
    for turn in history_list:
        if turn.user_text:
            messages.append({"role": "user", "content": turn.user_text})
        if turn.assistant_text:
            messages.append({"role": "assistant", "content": turn.assistant_text})

    messages.append({"role": "user", "content": user_text.strip()})
    return messages


def render_messages_for_prompt(messages: Iterable[dict]) -> str:
    lines = []
    for message in messages:
        role = message.get("role", "user").upper()
        content = (message.get("content") or "").strip()
        lines.append(f"{role}:\n{content}")
    return "\n\n".join(lines).strip()
