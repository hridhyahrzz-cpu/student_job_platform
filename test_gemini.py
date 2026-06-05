import json

log_path = "/Users/hridhyaraj/.gemini/antigravity-ide/brain/c8c13b6a-a9b5-49ca-83e0-9b5a7d2c1357/.system_generated/logs/transcript.jsonl"

steps_to_inspect = [116, 117, 127, 128]
with open(log_path, 'r') as f:
    for line in f:
        try:
            data = json.loads(line)
            step = data.get("step_index")
            if step in steps_to_inspect:
                print(f"--- STEP {step} ---")
                print(json.dumps(data, indent=2)[:2000])
        except Exception:
            pass
