# AGENTS.md — Project Guide for Coding Agents (Codex)

## Project Summary
This repo contains a minimal desktop app (PySide6) that connects to a local ComfyUI server and triggers image generation using a fixed ComfyUI workflow exported in **API format**.

The app is currently a **Dev Engine Test**:
- No LLM/chat orchestration yet
- No “installer” yet
- The goal is stable workflow execution + clean patching + UI responsiveness

## Core Goal (MVP Dev)
1) Load ComfyUI workflow (API JSON).
2) Patch workflow inputs (prompts, sampler params, optional character LoRA).
3) Queue prompt to ComfyUI and wait for output image.
4) Display the generated image in the UI.

## Non-goals (Not now)
- Building an .exe installer
- Auto-downloading ComfyUI
- Payment systems
- Multi-workflow “modes”
- Full chat/LLM brain orchestration

## Current Files
- `faceless.py` (or current main file): UI + worker + workflow patching (monolithic for now)
- `facelessbase.json`: ComfyUI workflow exported as **API format**
- `requirements.txt`: Python deps

## ComfyUI Requirements
- ComfyUI server must be running locally:
  - Default URL: `http://127.0.0.1:8188`
- Workflow file must be **API format** (not the UI “nodes” format).

## Workflow Contract (Markers)
The workflow uses node title markers so the app can reliably find nodes without hardcoding node IDs.

Required node title markers:
- `__LORA_ACCEL__` (LoRA loader for DMD2/acceleration, usually fixed)
- `__LORA_CHARACTER__` (LoRA loader slot for character LoRA, optional)
- `__PROMPT_POS__` (CLIPTextEncode for positive prompt)
- `__PROMPT_NEG__` (CLIPTextEncode for negative prompt)
- `__SAMPLER_MAIN__` (KSampler node to patch seed/steps/cfg/sampler/scheduler)
- `__CHECKPOINT_BASE__` (CheckpointLoaderSimple node, optional)

Agent must **not** reintroduce fixed node IDs (e.g. "88", "83"). Always detect by title marker first.

### Prompt Composition Rules
Final positive prompt is:
- `quality_tags` + `base_character_prompt` + `append_text`

- `base_character_prompt` is stored in app settings (Character settings).
- `append_text` is typed by the user (scene/action/emotion).

Negative prompt is patched into `__PROMPT_NEG__` (if present).

### LoRA Rules
- `__LORA_ACCEL__` remains always enabled (default; not controlled by UI for MVP).
- `__LORA_CHARACTER__` is optional:
  - If no LoRA selected: set strengths to `0.0` (disabled)
  - If selected: set `lora_name` + strengths (model/clip)

## Coding Rules / Constraints
- Keep UI responsive:
  - All ComfyUI calls must be off the UI thread (use worker thread).
- Prefer clarity over cleverness:
  - No complex dependency injection frameworks.
- Avoid breaking changes:
  - Keep current behavior intact while refactoring.

## Roadmap (Next Steps)
### Step 1 — Stabilize Node Detection
- Replace all hardcoded node IDs with marker-based detection.
- Add fallback heuristics only if marker missing.

### Step 2 — Modularize
Split monolithic script into modules, minimal structure:
- `app.py` (UI)
- `comfy_client.py`
- `workflow_patch.py`
- `dialogs.py`
- `models.py`

### Step 3 — Add Favorites (Like button) + Cache policy
- Save liked images + metadata (prompt + params) to `favorites.json`
- Add cache limit for non-liked images (optional)

## How to Run (Dev)
1) Start ComfyUI (server on port 8188).
2) Put `facelessbase.json` next to the app entry script.
3) Install deps:
   - `pip install -r requirements.txt`
4) Run:
   - `python faceless.py`
