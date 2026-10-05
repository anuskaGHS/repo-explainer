"""Test script to verify Ollama connectivity and ask_llm execution."""

import sys
from pathlib import Path

# Add project root and backend to sys.path so the module can be run directly
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

try:
    from backend.llm_service import ask_llm
except ImportError:
    from llm_service import ask_llm

if __name__ == "__main__":
    prompt = "Explain what an API is in 3 simple lines"
    try:
        result = ask_llm(prompt)
        print(result)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
