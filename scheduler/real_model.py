"""Optional adapter for any OpenAI-compatible chat completions endpoint.

Works with OpenAI, Azure OpenAI (v1-compatible endpoints), Ollama
(http://localhost:11434/v1) and similar. Configure with environment variables:

    LLM_BASE_URL   e.g. http://localhost:11434/v1
    LLM_API_KEY    optional for local servers
    LLM_MODEL      e.g. llama3.1

You do NOT need this to complete the assignment. All grading uses FakeModel.
"""

import json
import os
import time
import urllib.error
import urllib.request


class ModelServiceUnavailableError(Exception):
    """Raised when the remote model provider cannot be reached or is down."""
    pass


def send_http_request_with_retry(
    request: urllib.request.Request,
    provider_name: str,
    max_retries: int = 4,
    base_backoff_sec: float = 2.0,
) -> dict:
    """Send an HTTP request with exponential backoff on rate-limits (429), server errors (5xx), and network timeouts."""
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            last_error = e
            status_code = e.code
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                body_text = str(e)

            # 429 = Rate Limited, 500/502/503/504 = Server temporarily down/overloaded
            if status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries:
                    wait_time = base_backoff_sec * (2 ** (attempt - 1))
                    print(f"[{provider_name}] Received HTTP {status_code}. Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                raise ModelServiceUnavailableError(
                    f"{provider_name} model service appears to be down or rate-limited (HTTP {status_code}).\n"
                    f"Details from provider: {body_text}\n"
                    f"Please check your endpoint status or retry in a few moments."
                ) from e

            # Other 4xx client errors (e.g. 401 Unauthorized, 404 Model Not Found)
            raise ModelServiceUnavailableError(
                f"{provider_name} returned client error (HTTP {status_code}):\n{body_text}\n"
                f"Please verify your endpoint configuration and model name."
            ) from e

        except (urllib.error.URLError, TimeoutError, ConnectionError) as net_err:
            last_error = net_err
            if attempt < max_retries:
                wait_time = base_backoff_sec * (2 ** (attempt - 1))
                print(f"[{provider_name}] Connection error: {net_err}. Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue
            raise ModelServiceUnavailableError(
                f"Could not connect to {provider_name} service: {net_err}.\n"
                f"Please ensure you are connected to the network or the local server is running."
            ) from net_err

    raise ModelServiceUnavailableError(f"Failed to reach {provider_name} after {max_retries} attempts: {last_error}")


class OpenAICompatibleModel:
    def __init__(self):
        self.base_url = os.environ["LLM_BASE_URL"].rstrip("/")
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.model = os.environ["LLM_MODEL"]

    def complete(self, messages: list[dict]) -> str:
        # Most endpoints don't accept a bare "tool" role without tool_call ids,
        # so tool results are sent back as user messages.
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
        payload = send_http_request_with_retry(request, provider_name="OpenAI / Ollama")
        return payload["choices"][0]["message"]["content"]
