import json
import random
from typing import Any, Dict, Optional, Tuple

from models import CharacterParams, GenParams
from prompt_builder import build_positive_prompt


def find_node_by_title(prompt_graph: Dict[str, Any], title: str) -> Optional[str]:
    """Find node ID by _meta.title"""
    for node_id, node in prompt_graph.items():
        if not isinstance(node, dict):
            continue
        if node.get("_meta", {}).get("title", "") == title:
            return node_id
    return None


def detect_cliptext_nodes(prompt_graph: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Detect positive/negative CLIPTextEncode nodes by _meta.title."""
    pos_id = None
    neg_id = None

    for node_id, node in prompt_graph.items():
        if not isinstance(node, dict):
            continue

        meta_title = node.get("_meta", {}).get("title", "")

        if meta_title == "__PROMPT_POS__":
            pos_id = node_id
        elif meta_title == "__PROMPT_NEG__":
            neg_id = node_id

    print(f"[DEBUG] Detected nodes by title: pos={pos_id}, neg={neg_id}")

    return pos_id, neg_id


def patch_workflow(
    prompt_graph: Dict[str, Any],
    char_params: CharacterParams,
    append_text: str,
    gen_params: GenParams,
) -> Dict[str, Any]:
    """Patch workflow with character, prompts and parameters."""
    g = json.loads(json.dumps(prompt_graph))
    pos_id, neg_id = detect_cliptext_nodes(g)

    if pos_id is None:
        raise ValueError("No __PROMPT_POS__ node found.")

    # === POSITIVE PROMPT: QUALITY_TAGS + BASE + APPEND ===
    current = (g[pos_id].get("inputs") or {}).get("text", "") or ""
    base = char_params.visual_base.strip() if char_params.visual_base else current
    extra = append_text.strip()
    quality = gen_params.quality_tags.strip()
    final_positive = build_positive_prompt(quality, base, extra)

    print(f"[DEBUG] POSITIVE - Quality: {quality[:60]}...")
    print(f"[DEBUG] POSITIVE - Visual Base: {base[:60]}...")
    print(f"[DEBUG] POSITIVE - Append: {extra}")
    if char_params.identity_profile:
        print(f"[DEBUG] Identity profile (ignored for images): {char_params.identity_profile[:60]}...")
    print(f"[DEBUG] POSITIVE - Final: {final_positive[:120]}...")

    g[pos_id]["inputs"]["text"] = final_positive

    # === NEGATIVE PROMPT ===
    if neg_id and gen_params.negative:
        print(f"[DEBUG] NEGATIVE: {gen_params.negative[:80]}...")
        g[neg_id]["inputs"]["text"] = gen_params.negative

    # === CHARACTER LORA (__LORA_CHARACTER__) ===
    lora_char_id = find_node_by_title(g, "__LORA_CHARACTER__")
    if lora_char_id and g[lora_char_id].get("class_type") == "LoraLoader":
        if char_params.lora_name:
            g[lora_char_id]["inputs"]["lora_name"] = char_params.lora_name
            g[lora_char_id]["inputs"]["strength_model"] = char_params.lora_strength
            g[lora_char_id]["inputs"]["strength_clip"] = char_params.lora_strength
            print(f"[DEBUG] Character LoRA: {char_params.lora_name} @ {char_params.lora_strength}")
        else:
            # Disable LoRA by setting strength to 0
            g[lora_char_id]["inputs"]["strength_model"] = 0.0
            g[lora_char_id]["inputs"]["strength_clip"] = 0.0
            print("[DEBUG] Character LoRA: disabled")
    else:
        print("[WARN] __LORA_CHARACTER__ node not found")

    # === CHECKPOINT (__CHECKPOINT_BASE__) ===
    if gen_params.checkpoint:
        ckpt_id = find_node_by_title(g, "__CHECKPOINT_BASE__")
        if ckpt_id and g[ckpt_id].get("class_type") == "CheckpointLoaderSimple":
            g[ckpt_id]["inputs"]["ckpt_name"] = gen_params.checkpoint
            print(f"[DEBUG] Checkpoint: {gen_params.checkpoint}")

    # === KSAMPLER (__SAMPLER_MAIN__) ===
    sampler_id = find_node_by_title(g, "__SAMPLER_MAIN__")
    if sampler_id and g[sampler_id].get("class_type") in ["KSampler", "KSamplerAdvanced"]:
        inputs = g[sampler_id].get("inputs", {})

        if gen_params.seed is None:
            new_seed = random.randint(1, 2**31 - 1)
            print(f"[DEBUG] KSampler: Random seed = {new_seed}")
        else:
            new_seed = gen_params.seed
            print(f"[DEBUG] KSampler: Fixed seed = {new_seed}")

        if "seed" in inputs:
            inputs["seed"] = new_seed
        if "steps" in inputs:
            inputs["steps"] = gen_params.steps
        if "cfg" in inputs:
            inputs["cfg"] = gen_params.cfg
        if "sampler_name" in inputs:
            inputs["sampler_name"] = gen_params.sampler
        if "scheduler" in inputs:
            inputs["scheduler"] = gen_params.scheduler

        print(f"[DEBUG] KSampler: steps={gen_params.steps}, cfg={gen_params.cfg}, sampler={gen_params.sampler}")
    else:
        print("[WARN] __SAMPLER_MAIN__ node not found")

    return g
