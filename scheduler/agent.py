"""The scheduling agent: a simple tool-calling loop."""

import json
import re

from .model import Model
from .prompts import build_system_prompt
from .store import Store
from .tools import TOOLS

MAX_ITERATIONS = 8


def parse_action(raw: str) -> dict:
    """Safely parse the model output as a JSON object, stripping markdown if present."""
    trimmed = raw.strip()
    # Strip markdown code blocks if the model wrapped its output in ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", trimmed, re.DOTALL)
    if match:
        trimmed = match.group(1).strip()
    elif trimmed.startswith("{") and trimmed.endswith("}"):
        pass
    else:
        # Find outer braces if surrounded by conversational filler
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start != -1 and end != -1 and end > start:
            trimmed = trimmed[start : end + 1]

    data = json.loads(trimmed)
    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object.")
    return data


class SchedulingAgent:
    def __init__(self, model: Model, store: Store, today: str = "2026-11-02", max_iterations: int = MAX_ITERATIONS):
        self.model = model
        self.store = store
        self.today = today
        self.max_iterations = max_iterations

    def run(self, user_request: str) -> str:
        """Handle one user request and return the assistant's final answer."""
        messages = [
            {"role": "system", "content": build_system_prompt(self.store.people, self.today)},
            {"role": "user", "content": user_request},
        ]

        seen_tool_calls = set()

        for _ in range(self.max_iterations):
            raw = self.model.complete(messages)
            try:
                action = parse_action(raw)
            except Exception as e:
                # Malformed output from model
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "error": f"Invalid JSON format: {e}. You must return a single JSON object with either 'final' or 'tool' and 'args'."
                    }),
                })
                continue

            messages.append({"role": "assistant", "content": raw})

            if "final" in action:
                return str(action["final"])

            if "tool" not in action:
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"error": "Missing 'tool' or 'final' key in response."}),
                })
                continue

            tool_name = action["tool"]
            args = action.get("args")

            if not isinstance(args, dict):
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"error": f"'args' must be a JSON dictionary for tool '{tool_name}'."}),
                })
                continue

            # Detect repeated stuck loops (identical tool call with same arguments)
            call_sig = (tool_name, json.dumps(args, sort_keys=True))
            if call_sig in seen_tool_calls:
                # Cycle detected: model called the exact same tool with identical args
                messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "error": f"Tool '{tool_name}' was already called with these arguments. Provide a final response or call a different tool."
                    }),
                })
                continue
            seen_tool_calls.add(call_sig)

            tool = TOOLS.get(tool_name)
            if not tool:
                messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "error": f"Unknown tool '{tool_name}'. Available tools: {list(TOOLS.keys())}"
                    }),
                })
                continue

            try:
                result = tool(self.store, **args)
            except TypeError as te:
                result = {"error": f"Invalid arguments for '{tool_name}': {te}"}
            except Exception as ex:
                result = {"error": f"Tool execution failed: {ex}"}

            messages.append({"role": "tool", "content": json.dumps(result)})

        return "I apologize, but I could not complete your scheduling request within the allowed number of steps. Please try again with more details."
