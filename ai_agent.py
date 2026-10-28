"""
ai_agent.py - LLM layer with a 3-tier fallback:
    1. Google Gemini  ->  2. OpenRouter (free auto-routing)  ->  3. Offline rule-based analyzer

Public functions used by the dashboard:
    analyze_schedule(...)      free-form Q&A ("Why is P5 starved?")
    get_recommendation(...)    structured JSON tuning suggestion (powers "Apply Suggestion")
    generate_report(...)       human-readable Markdown report
    provider_status()          which keys are configured
"""
import json
import os
import re

from dotenv import load_dotenv

from analysis import (find_bottlenecks, detect_starvation, heuristic_recommendation,
                      rule_based_answer, rule_based_report)
from simulator import ALGORITHMS

try:  # optional: the app still works offline if these are missing
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = types = None
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

load_dotenv()

SYSTEM_INSTRUCTION = (
    "You are an expert Operating Systems professor and scheduler debugger. "
    "You are given the configuration, metrics and execution log of a CPU scheduler simulation. "
    "Ground every claim in the numbers provided. Explain concepts clearly, point out process starvation "
    "or excessive context switching, and suggest specific parameter tweaks (algorithm, quantum, aging interval). "
    "Be concise and use Markdown."
)


class LLMUnavailable(Exception):
    pass


def provider_status():
    return {"gemini": bool(os.environ.get("GEMINI_API_KEY")) and genai is not None,
            "openrouter": bool(os.environ.get("OPENROUTER_API_KEY")) and OpenAI is not None}


def _call_llm(prompt, temperature=0.3):
    """Try Gemini, then OpenRouter. Returns (text, provider). Raises LLMUnavailable if both fail."""
    errors = []
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if gemini_key and genai is not None:
        try:
            client = genai.Client(api_key=gemini_key)
            resp = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION,
                                                   temperature=temperature))
            return resp.text, "Gemini"
        except Exception as e:
            errors.append(f"Gemini: {e}")
            print(f"Gemini API failed: {e}. Trying OpenRouter...")

    if openrouter_key and OpenAI is not None:
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
            resp = client.chat.completions.create(
                model=os.environ.get("OPENROUTER_MODEL", "openrouter/free"),
                messages=[{"role": "system", "content": SYSTEM_INSTRUCTION},
                          {"role": "user", "content": prompt}],
                temperature=temperature)
            return resp.choices[0].message.content, "OpenRouter Backup"
        except Exception as e:
            errors.append(f"OpenRouter: {e}")

    raise LLMUnavailable("; ".join(errors) or "No API keys configured")


def _context(result, starved, findings, threshold, max_segments=150):
    logs = result.logs[["Process", "Start", "End"]].head(max_segments).to_dict(orient="records")
    return (
        f"CONFIG: {json.dumps(result.config)}\n"
        f"STARVATION_THRESHOLD_MS: {threshold}\n"
        f"SYSTEM_METRICS: {json.dumps(result.summary)}\n"
        f"PER_PROCESS_METRICS: {result.metrics.to_json(orient='records')}\n"
        f"RULE_BASED_STARVATION_FLAGS: {json.dumps(starved)}\n"
        f"RULE_BASED_FINDINGS: {json.dumps([t for _, t in findings])}\n"
        f"EXECUTION_LOG (Process/Start/End, 'Context Switch' and 'Idle' are non-process rows): {json.dumps(logs)}\n"
    )


def _diagnostics(result, threshold):
    starved = detect_starvation(result.metrics, threshold)
    findings = find_bottlenecks(result, starved)
    return starved, findings, heuristic_recommendation(result, starved)


# ----------------------------------------------------------------------------------------
def analyze_schedule(result, user_query, threshold=10):
    """Answer a free-form question about the schedule. `result` is a simulator.SimResult."""
    starved, findings, rec = _diagnostics(result, threshold)
    prompt = (f"{_context(result, starved, findings, threshold)}\n"
              f"USER QUESTION: \"{user_query}\"\n\n"
              "Answer the question using the data above. If a process is delayed/starved, explain the exact "
              "mechanism (who held the CPU, why the algorithm chose them) and end with a concrete parameter tweak.")
    try:
        text, provider = _call_llm(prompt)
        return f"**[Powered by {provider}]**\n\n{text}"
    except LLMUnavailable as e:
        note = f"*(AI providers unavailable: {e}. Showing the offline rule-based analyzer.)*"
        return f"**[Offline rule-based analyzer]**\n\n{rule_based_answer(user_query, result, starved, findings, rec)}\n\n{note}"


def get_recommendation(result, threshold=10):
    """Structured tuning suggestion: {algorithm, quantum, aging_interval, reason, source}."""
    starved, findings, fallback = _diagnostics(result, threshold)
    prompt = (f"{_context(result, starved, findings, threshold)}\n"
              "Recommend the best scheduler parameters to fix the biggest problem in this schedule. "
              "Reply with ONLY a JSON object, no prose and no code fences, with exactly these keys:\n"
              f'{{"algorithm": one of {json.dumps(ALGORITHMS)}, "quantum": integer 1-10, '
              '"aging_interval": integer 0-30 (0 = off, only matters for Priority algorithms), '
              '"reason": one or two sentences}')
    try:
        text, provider = _call_llm(prompt, temperature=0.1)
        data = json.loads(re.search(r"\{.*\}", text, re.S).group())
        algo = next((a for a in ALGORITHMS if a.lower() == str(data["algorithm"]).strip().lower()), None) \
            or next((a for a in ALGORITHMS if str(data["algorithm"]).lower() in a.lower()), None)
        if algo is None:
            raise ValueError("unknown algorithm in LLM reply")
        return {"algorithm": algo,
                "quantum": int(min(10, max(1, int(data["quantum"])))),
                "aging_interval": int(min(30, max(0, int(data["aging_interval"])))),
                "reason": str(data.get("reason", "")), "source": provider}
    except Exception:
        fallback["source"] = "Offline rule-based analyzer"
        return fallback


def generate_report(result, threshold=10):
    """Human-readable Markdown report of the whole run."""
    starved, findings, rec = _diagnostics(result, threshold)
    prompt = (f"{_context(result, starved, findings, threshold)}\n"
              "Write a professional scheduling report in Markdown with these sections: "
              "1) Summary, 2) Key Metrics, 3) Bottlenecks & Starvation (predict where it will get worse if more "
              "processes arrive), 4) Recommended Parameter Changes (concrete values), 5) Conclusion. "
              "Keep it under 450 words and cite numbers from the data.")
    try:
        text, provider = _call_llm(prompt, temperature=0.3)
        return f"{text}\n\n---\n*Report generated by {provider}.*"
    except LLMUnavailable:
        return rule_based_report(result, starved, findings, rec, threshold) + \
            "\n\n---\n*Report generated by the offline rule-based analyzer.*"
