import os
import json
import time
import requests
from datetime import datetime, date
from dateutil import tz
from typing import Dict, Any, Optional


pip install openai
from openai import OpenAI
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if you like
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
client = OpenAI(api_key=OPENAI_API_KEY)


CITY = "Chennai"
LAT, LON = 13.0827, 80.2707
TIMEZONE = "Asia/Kolkata" 


memory: Dict[str, Any] = {
    "city": CITY,
    "timezone": TIMEZONE,
    "last_api": None,
    "observations": [],   
    "decisions": [],      
    "log": []             
}

def log(msg: str):
    print(msg)
    memory["log"].append(f"{datetime.now().isoformat()} {msg}")


def fetch_weather(lat: float, lon: float, tz: str) -> Dict[str, Any]:
    """
    Gets today's daily precipitation sum + weather code for the location.
    See weather codes: https://open-meteo.com/en/docs
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=weathercode,precipitation_sum"
        f"&timezone={tz}"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()

  
    daily = data.get("daily", {})
    times = daily.get("time", [])
    wcodes = daily.get("weathercode", [])
    precips = daily.get("precipitation_sum", [])

    today_str = date.today().isoformat()
    idx = times.index(today_str) if today_str in times else 0

    today_info = {
        "date": times[idx] if times else today_str,
        "weathercode": int(wcodes[idx]) if wcodes else None,
        "precipitation_sum_mm": float(precips[idx]) if precips else 0.0,
        "source": "open-meteo",
    }
    return today_info


def ask_llm(system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def perceive() -> Dict[str, Any]:
    """Observe the world via tools (APIs)."""
    obs = fetch_weather(LAT, LON, TIMEZONE)
    memory["last_api"] = obs["source"]
    memory["observations"].append(obs)
    log(f"Observed weather: {obs}")
    return obs

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "umbrella": {"type": "boolean"},
        "outfit_hint": {"type": "string"},
        "activity": {"type": "string"},
        "reason": {"type": "string"}
    },
    "required": ["umbrella", "reason"]
}

def think(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ask the LLM to interpret the observation and pick actions.
    We instruct it to return strict JSON so we can parse/action reliably.
    """
    system = (
        "You are a concise weather decision agent. "
        "You MUST return STRICT JSON that validates against this JSON Schema: "
        f"{json.dumps(DECISION_SCHEMA)}. No prose."
    )
    user = (
        "Given today's observation, make a decision:\n"
        f"{json.dumps(observation, ensure_ascii=False)}\n\n"
        "Guidelines:\n"
        "- umbrella: true if precipitation_sum_mm > 0 or rainy/storm codes (>=51 and <=77, or >=80).\n"
        "- outfit_hint: short practical suggestion (e.g., 'light rain jacket').\n"
        "- activity: optional single suggestion (e.g., 'indoor gym').\n"
        "- reason: one sentence.\n"
        "Return ONLY JSON."
    )
    raw = ask_llm(system, user)
    try:
        decision = json.loads(raw)
    except json.JSONDecodeError:
        fix_system = "Fix the following into STRICT valid JSON only. No comments, no extra text."
        fixed = ask_llm(fix_system, raw)
        decision = json.loads(fixed)
    return decision

def act(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take actions (this is where you'd call downstream APIs).
    Here we just simulate: e.g., push notification, calendar note, etc.
    """
    actions_taken = []

    if decision.get("umbrella"):
        actions_taken.append("notify_user:Carry umbrella")

    outfit = decision.get("outfit_hint")
    if outfit:
        actions_taken.append(f"notify_user:Outfit hint -> {outfit}")

    activity = decision.get("activity")
    if activity:
        actions_taken.append(f"suggest_activity:{activity}")

    log(f"Actions taken: {actions_taken}")
    return {"actions": actions_taken}

def remember(observation: Dict[str, Any], decision: Dict[str, Any], actions: Dict[str, Any]) -> None:
    """Persist what matters to drive the next iteration."""
    memory["decisions"].append({
        "ts": datetime.now(tz=tz.gettz(TIMEZONE)).isoformat(),
        "observation": observation,
        "decision": decision,
        "actions": actions,
    })
  
    memory["last_umbrella"] = bool(decision.get("umbrella"))

def summarize() -> str:
    """Ask LLM to summarize state for the user (optional)."""
    system = "You are a helpful assistant. Be concise and practical."
    user = (
        "Summarize today's plan for the user based on this memory. "
        "Keep it under 60 words and concrete:\n"
        f"{json.dumps(memory.get('decisions', [])[-1], ensure_ascii=False)}"
    )
    return ask_llm(system, user)

def agent_loop(iterations: int = 1, sleep_secs: int = 0):
    for i in range(iterations):
        log(f"--- Iteration {i+1} ---")
        obs = perceive()
        decision = think(obs)
        actions = act(decision)
        remember(obs, decision, actions)

        # Optional: show a user-friendly summary
        user_msg = summarize()
        print("\n=== USER SUMMARY ===")
        print(user_msg)
        print("====================\n")

        if sleep_secs and i < iterations - 1:
            time.sleep(sleep_secs)

    print("\n--- FINAL MEMORY SNAPSHOT ---")
    print(json.dumps(memory, indent=2))
    print("------------------------------")

if __name__ == "__main__":
    agent_loop(iterations=1)
