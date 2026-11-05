"""Optional adapter for LLMs (OpenAI-compatible endpoints or Google Gemini).

Works with:
- Google Gemini API (GEMINI_API_KEY, GEMINI_MODEL)
- OpenAI-compatible endpoints (LLM_BASE_URL, LLM_MODEL, optional LLM_API_KEY)
- Local Ollama servers (http://localhost:11434/v1)

You do NOT need this to complete the assignment. All evaluation tests use FakeModel.
"""

import json
import os
import time
import urllib.request


class GeminiModel:
    """Adapter for Google Gemini's OpenAI-compatible v1beta endpoint or direct REST."""

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

    def complete(self, messages: list[dict]) -> str:
        # Convert tool results to user messages with explicit labeling
        converted = [
            {"role": "user", "content": f"Tool result: {m['content']}"}
            if m["role"] == "tool"
            else m
            for m in messages
        ]
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        body = json.dumps({
            "model": self.model,
            "messages": converted,
            "temperature": 0.1,
        }).encode()

        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        # Handle transient rate limits or 429 with exponential backoff
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request) as response:
                    payload = json.load(response)
                return payload["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8")
                if e.code in (429, 503) and attempt < 3:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise RuntimeError(f"Gemini API request failed ({e.code}): {err_msg}") from e


class OpenAICompatibleModel:
    def __init__(self):
        self.base_url = os.environ["LLM_BASE_URL"].rstrip("/")
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.model = os.environ["LLM_MODEL"]

    def complete(self, messages: list[dict]) -> str:
        converted = [
            {"role": "user", "content": f"Tool result: {m['content']}"}
            if m["role"] == "tool"
            else m
            for m in messages
        ]
        body = json.dumps({"model": self.model, "messages": converted}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(request) as response:
            payload = json.load(response)
        return payload["choices"][0]["message"]["content"]
