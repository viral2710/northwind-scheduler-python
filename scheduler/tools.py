"""Tools the agent can call. Each tool takes the Store plus keyword arguments
and returns JSON-serialisable data."""

from .slots import (
    availability_from_busy,
    combine_availability,
    find_free_windows,
    minutes_to_time,
    score_window,
    slot_to_time,
    time_to_minutes,
    time_to_slot,
    time_to_slot_ceil,
)
from .store import Store


def list_people(store: Store) -> list[dict]:
    """Return everyone in the directory."""
    return store.people


def get_busy_times(store: Store, person: str, date: str) -> list[dict] | dict:
    """Return a person's busy blocks on a date (YYYY-MM-DD)."""
    known_ids = {p["id"] for p in store.people}
    if person not in known_ids:
        return {"error": f"Person '{person}' not found in employee directory."}
    return store.calendars.get(person, {}).get(date, [])


def find_free_slots(
    store: Store,
    attendees: list[str],
    date: str,
    duration_minutes: int,
    earliest: str | None = None,
    latest: str | None = None,
    with_scores: bool = False,
) -> list[dict] | dict:
    """Find every time on `date` when all attendees are free for `duration_minutes`.

    `earliest` and `latest` optionally narrow the search to part of the day
    (e.g. earliest="12:00" for "afternoon").
    If `with_scores` is True, each slot includes an objective quality score.
    """
    known_ids = {p["id"] for p in store.people}
    missing = [p for p in attendees if p not in known_ids]
    if missing:
        missing_str = ", ".join(f"'{p}'" for p in missing)
        return {"error": f"Attendee(s) not found in employee directory: {missing_str}."}

    if duration_minutes <= 0:
        return {"error": "duration_minutes must be greater than 0."}

    calendars = []
    for person in attendees:
        busy = store.calendars.get(person, {}).get(date, [])
        calendars.append(availability_from_busy(busy))

    free = combine_availability(calendars)
    # Ceiling division ensures a 45 min meeting requires 2 slots (60 mins), not 1 (30 mins)
    slots_needed = -(-duration_minutes // 30)

    try:
        start_slot = max(0, time_to_slot(earliest)) if earliest else 0
        end_slot = min(16, time_to_slot_ceil(latest)) if latest else None
    except Exception as e:
        return {"error": f"Invalid earliest/latest time format: {e}"}

    starts = find_free_windows(free, slots_needed, start_slot, end_slot)
    res = []
    for s in starts:
        start_min = time_to_minutes(slot_to_time(s))
        end_min = start_min + duration_minutes
        item = {
            "start": slot_to_time(s),
            "end": minutes_to_time(end_min),
        }
        if with_scores:
            item["score"] = score_window(free, s, slots_needed)
        res.append(item)
    return res


def find_slots_multi_day(
    store: Store,
    attendees: list[str],
    dates: list[str],
    duration_minutes: int,
    earliest: str | None = None,
    latest: str | None = None,
) -> dict:
    """Search for free slots across multiple dates, returning options grouped by date."""
    results = {}
    for d in dates:
        day_res = find_free_slots(store, attendees, d, duration_minutes, earliest, latest)
        if isinstance(day_res, dict) and "error" in day_res:
            return day_res
        results[d] = day_res
    return results


TOOLS = {
    "list_people": list_people,
    "get_busy_times": get_busy_times,
    "find_free_slots": find_free_slots,
    "find_slots_multi_day": find_slots_multi_day,
}
