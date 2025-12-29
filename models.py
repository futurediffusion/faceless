from dataclasses import dataclass
from typing import Optional


@dataclass
class GenParams:
    seed: Optional[int] = None
    steps: int = 8
    cfg: float = 2.2
    sampler: str = "euler_ancestral"
    scheduler: str = "simple"
    quality_tags: str = "masterpiece, best quality, high quality, detailed"
    negative: str = "worst aesthetic, worst quality, low quality, bad quality, lowres, signature, username, logo, bad hands, mutated hands, ambiguous form, feral"
    checkpoint: str = ""  # Empty = use workflow default


@dataclass
class CharacterParams:
    visual_base: str = ""
    identity_profile: str = ""
    lora_name: str = ""  # Empty = disabled
    lora_strength: float = 0.0  # 0.0 = disabled, 1.0 = default when enabled
    base_prompt: Optional[str] = None

    def __post_init__(self) -> None:
        if self.base_prompt and not self.visual_base:
            self.visual_base = self.base_prompt
