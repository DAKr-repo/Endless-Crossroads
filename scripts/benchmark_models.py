#!/usr/bin/env python3
"""
benchmark_models.py — Head-to-head comparison of Ollama models on Pi 5.
Uses chat API with think=false for direct responses.
Measures: inference speed, output quality, RAM, thermals.
"""

import json
import subprocess
import time
import sys
import os

# ── Config ──────────────────────────────────────────────────────────────
MODELS = ["qwen3:1.7b", "qwen3.5:2b"]
NUM_CTX = 4096
NUM_PREDICT = 200
TEMPERATURE = 0.7
WARMUP_ROUNDS = 1
BENCHMARK_ROUNDS = 3

PROMPTS = [
    {
        "name": "Narrative (short)",
        "system": "You are a fantasy RPG narrator. Be vivid and concise.",
        "prompt": "Describe a ruined dwarven forge deep underground. 2-3 sentences.",
    },
    {
        "name": "Narrative (medium)",
        "system": "You are a fantasy RPG narrator. Be vivid and concise.",
        "prompt": "A party of adventurers enters a haunted library. The shelves whisper. Describe the scene, the atmosphere, and one supernatural event that occurs. 4-6 sentences.",
    },
    {
        "name": "Game mechanics",
        "system": "You are a tabletop RPG game master. Be precise and mechanical.",
        "prompt": "Generate a random encounter for a tier 2 dungeon. Include: enemy name, HP, attack description, and one special ability. Format as a stat block.",
    },
    {
        "name": "NPC dialogue",
        "system": "You are Mimir, a sassy Norse Skald. Respond in 1-2 sentences. Use Norse idioms.",
        "prompt": "The player just rolled a natural 1 on their attack. Comment on it.",
    },
    {
        "name": "Quest generation",
        "system": "You are a quest designer for a dark fantasy RPG. Respond in JSON only, no other text.",
        "prompt": 'Create a side quest. Return JSON with keys: quest_name, description, objective_type (one of: kill_count, search_count, loot_count, reach), target_count (1-5), reward_text.',
    },
]


def get_thermal():
    """Read Pi 5 CPU temperature."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return -1.0


def get_ram_usage_mb():
    """Get RSS of ollama-related processes."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        total_rss = 0.0
        for line in result.stdout.splitlines():
            if "ollama" in line.lower() and "grep" not in line:
                parts = line.split()
                if len(parts) >= 6:
                    total_rss += float(parts[5]) / 1024.0
        return total_rss if total_rss > 0 else -1.0
    except Exception:
        return -1.0


def run_ollama(model, system, prompt, num_predict=NUM_PREDICT, num_ctx=NUM_CTX):
    """Call ollama chat API with think=false and measure timing."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": TEMPERATURE,
            "num_thread": 4,
        },
    }

    start = time.time()
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=180
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            return None, elapsed, f"curl error: {result.stderr}"

        data = json.loads(result.stdout)
        message = data.get("message", {})
        response_text = message.get("content", "")

        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        prompt_eval_duration_ns = data.get("prompt_eval_duration", 0)
        total_duration_ns = data.get("total_duration", 0)

        tokens_per_sec = (
            eval_count / (eval_duration_ns / 1e9)
            if eval_duration_ns > 0 else 0
        )
        prompt_tokens_per_sec = (
            prompt_eval_count / (prompt_eval_duration_ns / 1e9)
            if prompt_eval_duration_ns > 0 else 0
        )

        stats = {
            "response": response_text,
            "eval_count": eval_count,
            "tokens_per_sec": round(tokens_per_sec, 2),
            "prompt_tokens": prompt_eval_count,
            "prompt_tokens_per_sec": round(prompt_tokens_per_sec, 2),
            "total_duration_s": round(total_duration_ns / 1e9, 2),
            "wall_time_s": round(elapsed, 2),
        }
        return stats, elapsed, None

    except subprocess.TimeoutExpired:
        return None, 180, "TIMEOUT (180s)"
    except json.JSONDecodeError as e:
        return None, time.time() - start, f"JSON parse error: {e}"


def main():
    print("=" * 70, flush=True)
    print("  CODEX MODEL BENCHMARK — Pi 5", flush=True)
    print(f"  Models: {', '.join(MODELS)}", flush=True)
    print(f"  Prompts: {len(PROMPTS)} | Rounds: {BENCHMARK_ROUNDS}", flush=True)
    print(f"  num_ctx={NUM_CTX}, num_predict={NUM_PREDICT}, temp={TEMPERATURE}", flush=True)
    print(f"  API: /api/chat with think=false", flush=True)
    print("=" * 70, flush=True)

    results = {model: [] for model in MODELS}

    for model in MODELS:
        print(f"\n{'─' * 70}", flush=True)
        print(f"  MODEL: {model}", flush=True)
        print(f"{'─' * 70}", flush=True)

        # Warmup — load model into memory
        if WARMUP_ROUNDS > 0:
            print(f"  Warming up ({WARMUP_ROUNDS} round)...", flush=True)
            run_ollama(model, "You are helpful.", "Say hello.", num_predict=20)
            print(f"  Warmup complete. RAM: {get_ram_usage_mb():.0f} MB", flush=True)

        for pi, prompt_cfg in enumerate(PROMPTS):
            print(f"\n  Prompt {pi+1}/{len(PROMPTS)}: {prompt_cfg['name']}", flush=True)
            round_stats = []

            for r in range(BENCHMARK_ROUNDS):
                temp_before = get_thermal()
                ram = get_ram_usage_mb()

                stats, elapsed, error = run_ollama(
                    model, prompt_cfg["system"], prompt_cfg["prompt"]
                )

                temp_after = get_thermal()

                if error:
                    print(f"    Round {r+1}: ERROR - {error}", flush=True)
                    continue

                stats["temp_before"] = temp_before
                stats["temp_after"] = temp_after
                stats["temp_delta"] = round(temp_after - temp_before, 1)
                stats["ram_mb"] = ram
                stats["prompt_name"] = prompt_cfg["name"]
                stats["round"] = r + 1
                round_stats.append(stats)

                print(f"    Round {r+1}: {stats['tokens_per_sec']} tok/s, "
                      f"{stats['eval_count']} tok, "
                      f"{stats['total_duration_s']}s, "
                      f"temp={temp_after:.1f}°C ({stats['temp_delta']:+.1f})", flush=True)

            if round_stats:
                avg_tps = sum(s["tokens_per_sec"] for s in round_stats) / len(round_stats)
                avg_tokens = sum(s["eval_count"] for s in round_stats) / len(round_stats)
                print(f"    AVG: {avg_tps:.1f} tok/s, {avg_tokens:.0f} tokens", flush=True)

            results[model].extend(round_stats)

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70, flush=True)
    print("  SUMMARY", flush=True)
    print("=" * 70, flush=True)

    for model in MODELS:
        all_stats = results[model]
        if not all_stats:
            print(f"\n  {model}: No valid results", flush=True)
            continue

        avg_tps = sum(s["tokens_per_sec"] for s in all_stats) / len(all_stats)
        avg_prompt_tps = sum(s["prompt_tokens_per_sec"] for s in all_stats) / len(all_stats)
        avg_tokens = sum(s["eval_count"] for s in all_stats) / len(all_stats)
        avg_duration = sum(s["total_duration_s"] for s in all_stats) / len(all_stats)
        max_temp = max(s["temp_after"] for s in all_stats)
        avg_temp_delta = sum(s["temp_delta"] for s in all_stats) / len(all_stats)
        avg_ram = sum(s["ram_mb"] for s in all_stats if s["ram_mb"] > 0) / max(1, sum(1 for s in all_stats if s["ram_mb"] > 0))

        print(f"\n  {model}:", flush=True)
        print(f"    Avg generation speed:  {avg_tps:.1f} tok/s", flush=True)
        print(f"    Avg prompt eval speed: {avg_prompt_tps:.1f} tok/s", flush=True)
        print(f"    Avg tokens generated:  {avg_tokens:.0f}", flush=True)
        print(f"    Avg total duration:    {avg_duration:.1f}s", flush=True)
        print(f"    Max temperature:       {max_temp:.1f}°C", flush=True)
        print(f"    Avg temp delta:        {avg_temp_delta:+.1f}°C", flush=True)
        print(f"    Avg RAM (ollama):      {avg_ram:.0f} MB", flush=True)

    # ── Sample outputs ──────────────────────────────────────────────────
    print("\n" + "=" * 70, flush=True)
    print("  SAMPLE OUTPUTS (Round 1 of each prompt)", flush=True)
    print("=" * 70, flush=True)

    for model in MODELS:
        print(f"\n  ── {model} ──", flush=True)
        seen_prompts = set()
        for s in results[model]:
            pname = s["prompt_name"]
            if pname not in seen_prompts:
                seen_prompts.add(pname)
                response = s["response"][:500]
                if len(s["response"]) > 500:
                    response += "..."
                print(f"\n  [{pname}]", flush=True)
                print(f"  {response}", flush=True)

    # Save full results
    out_path = os.path.join(os.path.dirname(__file__), "..", "logs", "benchmark_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Full results saved to: {out_path}", flush=True)


if __name__ == "__main__":
    main()
