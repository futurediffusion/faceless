# Faceless Dev

Minimal PySide6 UI that connects to a local ComfyUI server and runs a fixed workflow (API format).

## Setup
1. Run ComfyUI (default: http://127.0.0.1:8188)
2. Put `facelessbase.json` (API format) in the same folder as `faceless.py`
3. Install deps:
   pip install -r requirements.txt
4. Add your Gemini API key via ⚙ → API Keys
5. Run:
   python faceless.py
