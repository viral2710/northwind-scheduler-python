# NOTES.md

## Problems Found & Fixes Made

### 1. Off-by-one Error in Slot Window Search (`scheduler/slots.py`)
- **What it was**: In `find_free_windows()`, the loop range was written as `range(start_slot, end_slot - slots_needed)`. Because Python's `range(start, stop)` is half-open (excluding `stop`), the last valid starting index `end_slot - slots_needed` was skipped. For example, for an end-of-day search where `end_slot = 16` and a meeting takes 2 slots (1 hour), slot 14 (16:00 to 17:00) was never evaluated, even when completely free.
- **How I found it**: Found during manual code review of boundary conditions against the working day limits (`DAY_END = 17:00`, `SLOTS_PER_DAY = 16`).
- **What I changed**: Updated the upper bound to `range(start_slot, end_slot - slots_needed + 1)`. Added boundary unit tests in `tests/test_slots.py`.
- **Existing test modified**: Updating this boundary exposed a latent bug in `tests/test_tools.py::test_find_free_slots_for_two_people_in_the_afternoon`. On Tuesday afternoon, both Priya and Sam are free from 16:30 to 17:00, but the original test asserted only 4 slots ending at 16:30 because the original implementation missed the final slot of the day. The test expectation was updated to include `{"start": "16:30", "end": "17:00"}`.

### 2. Duration Truncation & Precise End Time Calculation (`scheduler/tools.py`)
- **What it was**: `slots_needed` was calculated as `duration_minutes // 30` (integer floor division), which caused a 45-minute request to round down to 30 minutes, underallocating time. Additionally, previously returned window end times were strictly snapped to slot boundaries rather than reflecting the precise requested meeting duration.
- **How I found it**: Reviewing requirement 1: *"Every time the assistant offers must actually work for every attendee, and it must not miss times that do work."*
- **What I changed**: Used ceiling division `-(-duration_minutes // 30)` to ensure sufficient contiguous free blocks on the 30-minute calendar grid while calculating the exact meeting end time (`start_time + duration_minutes`). For instance, a 45-minute meeting starting at 13:00 now blocks 13:00 to 13:45 (requiring two 30-min free slots on the grid), accurately preserving the attendee's remaining 15 minutes of buffer.

### 3. Ghost / Invented Attendees Treated as 100% Free (`scheduler/tools.py`)
- **What it was**: `find_free_slots` and `get_busy_times` performed `store.calendars.get(person, {}).get(date, [])`. When an unknown person (e.g., someone not in `people.json`) was supplied, `store.calendars.get(...)` returned `[]` (no busy blocks), marking that imaginary person as completely free for the entire day.
- **How I found it**: Reviewing requirement 2: *"No invented people. The assistant must never propose a meeting that includes someone who isn't in the directory. If a request names someone it can't find, the user should hear about it."*
- **What I changed**: Added explicit validation in `find_free_slots` and `get_busy_times` against `store.people`. If an unknown person is queried, the tools immediately return a clear error dict: `{"error": "Attendee(s) not found in employee directory: ..."}`. Added system prompt instructions guiding the model to alert the user.

### 4. Agent Fragility & Infinite Loop Risk (`scheduler/agent.py`)
- **What it was**:
  - The agent loop did `json.loads(raw)` with `while True:`. If the language model produced markdown code blocks (e.g. ` ```json ... ``` `), conversational preamble, or malformed JSON, the application crashed with an unhandled exception.
  - If the model called a non-existent tool or supplied malformed/non-dict arguments, it crashed with `KeyError` or `TypeError`.
  - There was no upper iteration limit or cycle detection, allowing an uncooperative or looping model to run indefinitely.
- **How I found it**: Reviewing requirements 3 & 4: *"Graceful failure"* and *"It always finishes. No request should be able to keep the assistant running indefinitely."*
- **What I changed**:
  - Implemented `parse_action()` to strip markdown syntax and extract JSON objects safely.
  - Replaced `while True:` with a bounded iteration counter (`max_iterations = 8`).
  - Added cycle detection to intercept repeated identical tool calls.
  - Captured tool exceptions and JSON decoding errors, returning actionable feedback into the agent conversation so the model can self-correct or report failures cleanly.

---

## Part B: Meaningful Addition

### Multi-Day Availability Search & Smart Slot Quality Scoring (`find_slots_multi_day` & `score_window`)
- **What was built**:
  1. **`score_window(free, start_slot, slots_needed)`**: Scores each candidate meeting window based on real-world employee preferences:
     - **Protects lunch hour** (12:00 to 13:00, slots 6 & 7) with a penalty so users aren't booked during lunch when alternative slots exist.
     - **Focus buffer bonus**: Rewards slots that leave free buffer time before or after, reducing back-to-back meeting fatigue.
     - **Late-day penalty**: Deprecates booking meetings ending right at 17:00 when earlier options exist.
  2. **`find_slots_multi_day(...)`**: A multi-day search tool allowing the assistant to inspect multiple dates in a single tool call when a user asks for "sometime next week" or when a single day is completely full.
- **Who it helps**: Employees and managers trying to find optimal meeting windows across busy team calendars without disruptive back-to-back crunches or lunch interruptions.
- **Why I chose it over other options**: In real workplace scheduling, simply returning the first raw slot often produces poor outcomes (like 12:00 lunch meetings or back-to-back crunches). Providing objective quality scoring and multi-day aggregation directly enhances assistant utility while keeping the deterministic scheduling core clean and testable.

---

## How I Used AI Tools

- **What was delegated**:
  - Used AI to explore potential edge-case patterns in calendar slot intervals and suggest unit test test cases.
  - Delegated scaffolding of initial boilerplate for error handling and test skeletons.
- **Specific case where an AI suggestion was rejected or corrected**:
  - An initial AI suggestion proposed modifying `find_free_slots` to automatically discard slots during 12:00–13:00 entirely.
  - **Reason for rejection**: Hardcoding 12:00–13:00 as completely unavailable breaks valid requests where an employee *specifically* asks for a lunch meeting or when lunch is the only time everyone is available. Instead, I introduced soft scoring (`score_window`) and optional parameters, preserving deterministic availability while enabling preference-based recommendations.

---

## What I'd Do Next

1. **Attendee Working Hours & Timezone Support**: Support individuals working differing schedules (e.g. 08:00–16:00 vs 10:00–18:00) and timezones.
2. **Calendar Conflict Resolution & Optional Attendees**: Distinguish between mandatory attendees and optional attendees when no slot satisfies the entire group.
3. **Natural Language Date Parsing**: Enhance prompt / tool support for relative natural phrases like "next Tuesday", "in two days", or "end of week" directly mapped to ISO date ranges.
4. **Deliberately Left Alone**: Writing invitations, sending calendar invites, and external database persistence were kept strictly out of scope per assignment instructions.

