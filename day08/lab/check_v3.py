import json
log = json.load(open("logs/grading_run_v3.json", encoding="utf-8"))
for q in log:
    print(f"[{q['id']}]")
    print(q["answer"])
    print()
