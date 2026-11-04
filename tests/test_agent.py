import json

from scheduler.agent import SchedulingAgent
from scheduler.model import FakeModel, final, tool_call
from scheduler.store import Store


def test_agent_returns_final_answer():
    model = FakeModel([final("Happy to help!")])
    agent = SchedulingAgent(model, Store.load())
    assert agent.run("hello") == "Happy to help!"


def test_agent_calls_tool_and_returns_result_to_model():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya", "sam"],
                  date="2026-11-03", duration_minutes=60, earliest="12:00"),
        final("13:00 works for both."),
    ])
    agent = SchedulingAgent(model, Store.load())

    answer = agent.run("Find an hour for Priya and Sam on Tuesday afternoon")

    assert answer == "13:00 works for both."
    second_call = model.calls[1]
    assert second_call[-1]["role"] == "tool"
    assert {"start": "13:00", "end": "14:00"} in json.loads(second_call[-1]["content"])


def test_system_prompt_includes_directory():
    model = FakeModel([final("ok")])
    SchedulingAgent(model, Store.load()).run("hi")
    system = model.calls[0][0]["content"]
    assert "Priya Raman" in system


def test_agent_handles_markdown_wrapped_json():
    wrapped_json = "```json\n" + final("Found a time!") + "\n```"
    model = FakeModel([wrapped_json])
    agent = SchedulingAgent(model, Store.load())
    assert agent.run("Find time") == "Found a time!"


def test_agent_recovers_from_malformed_json():
    model = FakeModel([
        "Not valid json at all",
        final("Recovered after error message!"),
    ])
    agent = SchedulingAgent(model, Store.load())
    answer = agent.run("Find time")
    assert answer == "Recovered after error message!"
    assert "Invalid JSON format" in model.calls[1][-1]["content"]


def test_agent_handles_unknown_tool_gracefully():
    model = FakeModel([
        tool_call("non_existent_tool", foo="bar"),
        final("Understood, proceeding."),
    ])
    agent = SchedulingAgent(model, Store.load())
    answer = agent.run("Find time")
    assert answer == "Understood, proceeding."
    assert "Unknown tool" in model.calls[1][-1]["content"]


def test_agent_handles_bad_arguments_gracefully():
    model = FakeModel([
        json.dumps({"tool": "find_free_slots", "args": "not-a-dict"}),
        final("Fixed args."),
    ])
    agent = SchedulingAgent(model, Store.load())
    answer = agent.run("Find time")
    assert answer == "Fixed args."
    assert "'args' must be a JSON dictionary" in model.calls[1][-1]["content"]


def test_agent_always_finishes_on_infinite_loop():
    # Simulate a model looping indefinitely on the same tool call
    model = FakeModel(
        [tool_call("find_free_slots", attendees=["priya"], date="2026-11-03", duration_minutes=30)],
        loop_last=True,
    )
    agent = SchedulingAgent(model, Store.load(), max_iterations=4)
    result = agent.run("Stuck query")
    assert "could not complete your scheduling request within the allowed number of steps" in result


def test_agent_handles_unknown_person_feedback():
    model = FakeModel([
        tool_call("find_free_slots", attendees=["priya", "superman"], date="2026-11-03", duration_minutes=30),
        final("I could not find Superman in the directory. Would you like to schedule with Priya only?"),
    ])
    agent = SchedulingAgent(model, Store.load())
    answer = agent.run("Schedule with Priya and Superman")
    assert "not found in employee directory" in model.calls[1][-1]["content"]
    assert "Superman" in answer
