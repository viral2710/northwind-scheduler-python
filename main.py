"""Command-line entry point.

    python main.py "Find an hour for Priya and Sam on Tuesday afternoon"

Uses a real model if LLM_BASE_URL and LLM_MODEL are set, otherwise a
scripted demo model.
"""

import os
import sys
from pathlib import Path


def load_env() -> None:
    """Lightweight .env loader without requiring external third-party dependencies."""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.is_file():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if val.startswith(('"', "'")) and val.endswith(('"', "'")) and len(val) >= 2:
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


from scheduler.agent import SchedulingAgent
from scheduler.model import FakeModel, final, tool_call
from scheduler.store import Store


def demo_model(request: str = "") -> FakeModel:
    req_lower = request.lower()
    # If the user asks for someone not in the directory (e.g. "viral")
    if "viral" in req_lower or "batman" in req_lower:
        return FakeModel([
            tool_call(
                "find_free_slots",
                attendees=["priya", "viral"],
                date="2026-11-03",
                duration_minutes=45,
                earliest="12:00",
            ),
            final("I could not find 'Viral' in the Northwind employee directory. Please check the spelling or provide their Northwind email/ID."),
        ])

    # Dynamic duration check for 45 min vs 60 min
    duration = 45 if "45" in req_lower else 60
    end_time = "13:45" if duration == 45 else "14:00"

    return FakeModel([
        tool_call(
            "find_free_slots",
            attendees=["priya", "sam"],
            date="2026-11-03",
            duration_minutes=duration,
            earliest="12:00",
        ),
        final(f"Priya and Sam are both free on Tuesday Nov 3 from 13:00 to {end_time}."),
    ])


def main() -> None:
    load_env()
    request = " ".join(sys.argv[1:]) or "Find an hour for Priya and Sam on Tuesday afternoon"
    if os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_MODEL"):
        from scheduler.real_model import OpenAICompatibleModel
        model = OpenAICompatibleModel()
    else:
        model = demo_model(request)

    agent = SchedulingAgent(model, Store.load())
    try:
        print(agent.run(request))
    except Exception as e:
        print(f"\n[Error] Unable to complete request: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
