# 🧠 Mimir Bridge - Usage Guide

## What Is This?

`ask_mimir.py` is a bridge script that lets Claude Code delegate simple tasks to your local Qwen model to **save tokens**. Think of it as hiring a "Junior Intern" (Qwen 1.5B) to handle grunt work while the "Senior Architect" (Claude) focuses on complex reasoning.

## Installation

1. **Download** `ask_mimir.py` to your project directory
2. **Make it executable:**
   ```bash
   chmod +x ask_mimir.py
   ```
3. **Verify Ollama is running:**
   ```bash
   systemctl status ollama
   ```

## Basic Usage

### Option 1: Direct Question
```bash
python3 ask_mimir.py "Write a docstring for a function that calculates fibonacci numbers"
```

### Option 2: With File Context
```bash
python3 ask_mimir.py "Generate docstrings for all functions" --file my_code.py
```

### Option 3: Pipe Input
```bash
cat error.log | python3 ask_mimir.py "Summarize this error in one line"
```

### Option 4: Use Different Model
```bash
python3 ask_mimir.py "Explain this code" --file code.py --model qwen2.5:1.5b
```

## Real-World Examples

### Example 1: Generate Docstrings (Token Saver!)

**Before (Claude does everything - costs tokens):**
```bash
# Claude reads the file, understands it, writes docstrings
# Cost: ~500-1000 tokens
```

**After (Mimir does grunt work):**
```bash
# Step 1: Claude writes the complex code logic
# Step 2: Use Mimir to generate docstrings
python3 ask_mimir.py "Write Python docstrings for each function" --file my_module.py

# Step 3: Claude reviews Mimir's output and applies it
# Cost: ~100-200 tokens (80% savings!)
```

### Example 2: Summarize Error Logs

**Before:**
```bash
# Paste 200-line error trace into Claude
# Cost: 2000+ tokens just to read it
```

**After:**
```bash
# Compress first
cat error.log | python3 ask_mimir.py "What's the root cause? One sentence."

# Output: "KeyError: 'doom_clock' in render_view() at line 45"
# Send ONLY this to Claude
# Cost: ~50 tokens (97% savings!)
```

### Example 3: Git Diff Narrator

**Before:**
```bash
# Paste entire git diff to Claude
# Cost: 1000+ tokens
```

**After:**
```bash
git diff | python3 ask_mimir.py "Summarize what changed in this commit"

# Output: "Changed dungeon_depth default to 1, added try/except to save loader"
# Cost: ~100 tokens (90% savings!)
```

## Integration with Claude Code Agents

When working with your C.O.D.E.X. agents, you can tell Claude about this tool:

```
@codex-mechanic

I have a local AI tool available: ask_mimir.py

Usage: python3 ask_mimir.py "instruction" --file "filename"

This is a 1.5B model - fast but low-fidelity. You MUST review its output before using it.

Good uses:
- Generate docstrings
- Summarize logs
- Simple text transformations

Bad uses:
- Complex logic
- Architectural decisions
- Anything requiring deep reasoning

Please use this tool to save tokens when writing documentation.
```

## Testing the Bridge

Use the included `test_functions.py` to verify everything works:

```bash
# Test 1: Generate docstrings
python3 ask_mimir.py "Write Python docstrings for these functions" --file test_functions.py

# Test 2: Explain code
python3 ask_mimir.py "Explain what calculate_damage() does in one sentence" --file test_functions.py

# Test 3: Find issues
python3 ask_mimir.py "Are there any bugs in this code?" --file test_functions.py
```

## Expected Output Quality

**✅ Good for:**
- Docstrings (mostly accurate)
- Simple summaries
- Code explanations
- Pattern identification

**⚠️ Review Carefully:**
- May hallucinate parameter names
- May miss edge cases
- May write generic descriptions

**❌ Don't use for:**
- Architectural decisions
- Complex refactoring
- Security analysis
- Anything mission-critical

## Configuration Options

Edit the script to customize:

```python
# Line 18-19: Change the model
MODEL = "qwen2.5-coder:1.5b"  # Your current model

# Line 36-38: Adjust generation settings
"temperature": 0.2,    # Lower = more factual (0.0-1.0)
"num_ctx": 4096,       # Context window size
"num_predict": 512     # Max response length
```

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Check if Ollama is running
systemctl status ollama

# If not, start it
sudo systemctl start ollama
```

### "Model not found"
```bash
# List available models
ollama list

# Pull the model if needed
ollama pull qwen2.5-coder:1.5b
```

### "Request timed out"
The model might be loading into memory for the first time. Wait 30 seconds and try again.

### Slow responses
The 1.5B model should respond in 2-5 seconds on a Pi 5. If it's slower, check:
```bash
# CPU usage
top

# Model loaded in RAM
ollama ps
```

## Token Savings Estimate

| Task | Without Mimir | With Mimir | Savings |
|------|---------------|------------|---------|
| Docstrings (10 functions) | 1000 tokens | 200 tokens | 80% |
| Error log summary | 2000 tokens | 100 tokens | 95% |
| Git diff summary | 1500 tokens | 150 tokens | 90% |
| Code explanation | 800 tokens | 200 tokens | 75% |

**Average savings: 85% on grunt work tasks**

## The Workflow

1. **Claude writes complex code** (uses its intelligence where needed)
2. **Mimir generates documentation** (grunt work)
3. **Claude reviews Mimir's output** (quality control)
4. **Claude applies approved content** (final integration)

This "Senior Architect + Junior Intern" pattern maximizes efficiency!

## Available Models on Your System

From your `ollama list`:
- `qwen2.5-coder:1.5b` - **Recommended** (code-focused)
- `qwen2.5:1.5b` - General purpose
- `deepseek-r1:1.5b` - Reasoning model
- `qwen3:1.7b` - Slightly larger
- `codex:latest` - Custom model (1.4GB)
- `mimir:latest` - Custom model (397MB)

You can switch models with `--model` flag:
```bash
python3 ask_mimir.py "task" --file code.py --model deepseek-r1:1.5b
```

## Next Steps

1. Test the bridge with `test_functions.py`
2. Try it on a real file from your Codex project
3. Integrate into your Claude Code workflow
4. Monitor token usage and adjust as needed

---

**Remember:** Mimir is fast but not smart. Claude is smart but costs tokens. Use each for what they're good at! 🧠⚡
