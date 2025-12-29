from dataclasses import dataclass, field
from typing import List

from scene_plan import ScenePlan


@dataclass
class ChatTurn:
    user_text: str
    assistant_text: str
    scene_plan: ScenePlan


@dataclass
class WorldState:
    identity_profile: str = ""
    location: str = "unspecified"
    mood: str = "neutral"
    visual_anchor: str = ""
    last_scene_append: str = ""
    turn_id: int = 0
    history: List[ChatTurn] = field(default_factory=list)
    history_max: int = 10

    def update_identity_profile(self, profile: str) -> None:
        self.identity_profile = profile.strip()
        self.turn_id += 1
        print("[STATE] identity_profile updated")

    def apply_sceneplan(self, sceneplan: ScenePlan) -> None:
        if sceneplan.mood:
            self.mood = sceneplan.mood
        if sceneplan.scene_append:
            self.last_scene_append = sceneplan.scene_append
        if sceneplan.change_scene:
            if sceneplan.location:
                self.location = sceneplan.location
            if sceneplan.visual_anchor:
                self.visual_anchor = sceneplan.visual_anchor

    def add_turn(self, user_text: str, assistant_text: str, scene_plan: ScenePlan) -> None:
        self.history.append(
            ChatTurn(
                user_text=user_text.strip(),
                assistant_text=assistant_text.strip(),
                scene_plan=scene_plan,
            )
        )
        if len(self.history) > self.history_max:
            self.history = self.history[-self.history_max :]

    def build_llm_context(self) -> str:
        identity = self.identity_profile.strip() or "(empty)"
        location = self.location.strip() or "(unspecified)"
        visual_anchor = self.visual_anchor.strip() or "(unspecified)"
        lines = [
            f"Identity profile: {identity}",
            f"World State (LOCKED): Location={location}. VisualAnchor={visual_anchor}.",
            f"Current location is LOCKED: {location}",
            f"Current visual anchor is LOCKED: {visual_anchor}",
            "Rule: Do not change location or visual_anchor unless change_scene=true.",
        ]
        if self.history:
            last_turn = self.history[-1]
            scene = last_turn.scene_plan
            lines.append(
                "Previous turn summary: "
                f"user='{last_turn.user_text}', assistant='{last_turn.assistant_text}', "
                f"change_scene={scene.change_scene}, scene_append='{scene.scene_append}'"
            )
        return "\n".join(lines)
