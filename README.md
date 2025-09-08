🔍 How this forms an “Agent Loop”

Perceive (Tool/API call)
fetch_weather() hits Open-Meteo and returns today’s precipitation sum + weather code for Chennai.

Think (LLM decision)
We pass the raw observation to the LLM with strict instructions to output valid JSON (umbrella, outfit, activity, reason).

This is programmatic prompting: the program, not a human, sends the prompt and parses the result.

Act (side effects)
Based on the JSON, we take actions (today just simulated notifications, but you can replace with Slack, SMS, calendar, etc.).

Remember (memory management)
We persist what matters (observation, decision, actions), plus a few derived fields like last_umbrella.

Next iterations could use last_umbrella to plan tomorrow’s bag, commute mode, etc.

Repeat
The loop can run every hour / morning via a scheduler or a service.
