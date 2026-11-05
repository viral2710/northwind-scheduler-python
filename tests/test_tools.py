from scheduler.store import Store
from scheduler.tools import (
    find_free_slots,
    find_slots_multi_day,
    get_busy_times,
    get_continuous_free_times,
)


def test_get_busy_times():
    store = Store.load()
    busy = get_busy_times(store, "sam", "2026-11-04")
    assert busy == [{"start": "09:00", "end": "09:30", "title": "Standup"}]


def test_find_free_slots_for_two_people_in_the_afternoon():
    store = Store.load()
    slots = find_free_slots(
        store,
        attendees=["priya", "sam"],
        date="2026-11-03",
        duration_minutes=30,
        earliest="13:00",
    )
    assert slots == [
        {"start": "13:00", "end": "13:30"},
        {"start": "13:30", "end": "14:00"},
        {"start": "15:00", "end": "15:30"},
        {"start": "16:00", "end": "16:30"},
        {"start": "16:30", "end": "17:00"},
    ]


def test_find_free_slots_hour_long_meeting():
    store = Store.load()
    slots = find_free_slots(
        store, attendees=["priya", "sam"], date="2026-11-03", duration_minutes=60
    )
    assert {"start": "13:00", "end": "14:00"} in slots


def test_find_free_slots_unknown_person():
    store = Store.load()
    res = find_free_slots(
        store, attendees=["priya", "batman"], date="2026-11-03", duration_minutes=30
    )
    assert "error" in res
    assert "batman" in res["error"]


def test_get_busy_times_unknown_person():
    store = Store.load()
    res = get_busy_times(store, "batman", "2026-11-03")
    assert "error" in res
    assert "batman" in res["error"]


def test_find_free_slots_with_scores():
    store = Store.load()
    slots = find_free_slots(
        store, attendees=["priya", "sam"], date="2026-11-03", duration_minutes=30, earliest="12:00", with_scores=True
    )
    assert len(slots) > 0
    assert "score" in slots[0]
    # Lunch slot (12:00-13:00) should have lower score than afternoon slot with buffers
    lunch_slot = next((s for s in slots if s["start"] == "12:00"), None)
    afternoon_slot = next((s for s in slots if s["start"] == "13:00"), None)
    if lunch_slot and afternoon_slot:
        assert afternoon_slot["score"] > lunch_slot["score"]


def test_get_continuous_free_times():
    store = Store.load()
    # On Wednesday Nov 4, Priya is free from 12:00 to 17:00 and Mei is free all afternoon
    blocks = get_continuous_free_times(
        store, attendees=["priya", "mei"], date="2026-11-04", earliest="12:00"
    )
    assert len(blocks) == 1
    assert blocks[0]["start"] == "12:00"
    assert blocks[0]["end"] == "17:00"
    assert blocks[0]["duration_minutes"] == 300


def test_find_free_slots_duration_rounding():
    store = Store.load()
    # 45 minutes needs 2 slots (60 mins reserved on grid) but ends after 45 minutes
    slots_45 = find_free_slots(
        store, attendees=["priya", "sam"], date="2026-11-03", duration_minutes=45
    )
    for s in slots_45:
        start_h, start_m = map(int, s["start"].split(":"))
        end_h, end_m = map(int, s["end"].split(":"))
        assert (end_h * 60 + end_m) - (start_h * 60 + start_m) == 45
