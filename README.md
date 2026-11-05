# Northwind Scheduling Assistant (Python)

A small agentic assistant that helps employees find meeting times. A user
types a request in plain English ("find 45 minutes with Priya and Sam next
Tuesday afternoon"); a language model turns it into tool calls; the tools
look up calendars and compute when everyone is free.

This codebase was written quickly by an AI coding agent. Treat it the way you
would treat code you inherited from a teammate: it runs, and the tests pass,
but nobody has reviewed it carefully.

## Layout

```
data/                 Sample directory (people.json) and calendars (calendars.json)
scheduler/
  slots.py            Working-day slot model and free-window search
  tools.py            Tools the agent can call
  agent.py            The tool-calling loop
  prompts.py          System prompt construction
  model.py            Model interface + FakeModel for tests
  real_model.py       Optional adapter for OpenAI-compatible endpoints
  store.py            Loads the JSON data
main.py               CLI entry point
tests/                pytest suite
```

## Running

Requires Python 3.10+.

### Using uv (recommended)
```bash
uv sync --extra dev
uv run pytest
uv run python main.py "Find an hour for Priya and Sam on Tuesday afternoon"
```

### Using standard pip/python
```bash
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
python main.py "Find an hour for Priya and Sam on Tuesday afternoon"
```

Sample calendar data covers Monday 2 November to Wednesday 4 November 2026.
"Today" is Monday 2 November 2026.

## Models

`FakeModel` returns scripted responses, so you can test the agent without any
API access. Script responses are raw strings, which lets you simulate
malformed or unexpected model output as well as well-formed JSON. The helpers
`tool_call(...)` and `final(...)` build well-formed responses.

You do not need a real model for this assignment, and using one earns no extra
credit. If you want to try one anyway, `real_model.py` works with any
OpenAI-compatible endpoint, including a local server such as Ollama:

```bash
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=llama3.1
python main.py "Find 30 minutes with Mei and Luis on Tuesday"
```

You can also copy `.env.example` to `.env` to configure your environment variables.
The adapter includes automatic exponential retry backoff and clean error diagnostics if the endpoint is offline or rate-limited.
