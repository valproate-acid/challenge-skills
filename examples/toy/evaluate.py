"""A tiny trusted evaluator: only integral candidates in [-100, 100] are valid."""
import json
from pathlib import Path

x = json.loads(Path("candidate.json").read_text()).get("x")
valid = type(x) is int and -100 <= x <= 100
print(json.dumps({"valid": valid, "metrics": {"loss": (x - 7) ** 2} if valid else {}}))
