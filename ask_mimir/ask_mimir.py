#!/usr/bin/env python3
"""
MIMIR BRIDGE: Local AI Task Handler
Connects Claude Code to local Ollama models for token-saving tasks.

Usage: 
  python3 ask_mimir.py "Instruction" --file "path/to/context.py"
  cat error.log | python3 ask_mimir.py "Summarize this error"
  
Purpose:
  - Generate docstrings (save tokens on documentation)
  - Summarize logs/errors (compress before sending to Claude)
  - Simple text transformations (no complex reasoning)

Model: qwen2.5-coder:1.5b (Fast, low-fidelity - Claude MUST review output)
"""
import sys
import argparse
import requests
import json

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mimir"  # Custom Ollama model with Norse Skald persona

def query_local_ai(prompt, context="", model=None):
    """Send a task to the local Ollama model."""
    selected_model = model if model else MODEL
    full_prompt = f"CONTEXT:\n{context}\n\nTASK:\n{prompt}\n\nRESPONSE (Concise):"

    payload = {
        "model": selected_model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,  # Low temp = less creative, more factual
            "num_ctx": 4096,     # Context window
            "num_predict": 512   # Max response length
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()['response'].strip()
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Is it running? (systemctl status ollama)"
    except requests.exceptions.Timeout:
        return "ERROR: Ollama request timed out. Model might be loading."
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

def main():
    parser = argparse.ArgumentParser(
        description="Ask Mimir (local Qwen model) a question.",
        epilog="Note: Output should be reviewed by Claude before use."
    )
    parser.add_argument("instruction", type=str, help="What do you want Mimir to do?")
    parser.add_argument("--file", type=str, help="File to read as context", required=False)
    parser.add_argument("--model", type=str, help="Override default model", default=MODEL)
    
    args = parser.parse_args()

    file_content = ""
    
    # Read context from file if provided
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except FileNotFoundError:
            print(f"ERROR: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Cannot read file: {e}", file=sys.stderr)
            sys.exit(1)

    # Read from stdin if piping (e.g., cat error.log | ask_mimir.py)
    if not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read()
            if file_content:
                file_content += "\n\n--- STDIN ---\n" + stdin_content
            else:
                file_content = stdin_content
        except Exception as e:
            print(f"ERROR: Cannot read stdin: {e}", file=sys.stderr)
            sys.exit(1)

    # Query the local model
    result = query_local_ai(args.instruction, file_content, args.model)
    print(result)

if __name__ == "__main__":
    main()
