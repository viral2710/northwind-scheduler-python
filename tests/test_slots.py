from scheduler.slots import (
    availability_from_busy,
    combine_availability,
    find_free_windows,
    slot_to_time,
    time_to_slot,
)


def test_slot_to_time():
    assert slot_to_time(0) == "09:00"
    assert slot_to_time(3) == "10:30"


def test_time_to_slot():
    assert time_to_slot("09:00") == 0
    assert time_to_slot("10:45") == 3


def test_availability_marks_partial_overlap_busy():
    free = availability_from_busy([{"start": "10:00", "end": "10:45"}])
    assert free[2] is False  # 10:00-10:30
    assert free[3] is False  # 10:30-11:00, partially busy
    assert free[4] is True


def test_combine_availability():
    a = [True, True, False, True]
    b = [True, False, True, True]
    assert combine_availability([a, b])[:4] == [True, False, False, True]


def test_find_free_windows():
    free = [False, True, True, True, False, True] + [False] * 10
    assert find_free_windows(free, 2) == [1, 2]


def test_find_free_windows_reaches_end_of_day():
    # Last two slots (slots 14 and 15, corresponding to 16:00-17:00) free
    free = [False] * 14 + [True, True]
    assert find_free_windows(free, 2) == [14]
    # Single slot at the very end
    assert find_free_windows(free, 1) == [14, 15]


def test_find_free_windows_with_end_slot_boundary():
    # Only slots 0, 1, 2 free, end_slot = 2, slots_needed = 2 -> window [0, 1] ends at slot 2
    free = [True] * 4 + [False] * 12
    assert find_free_windows(free, slots_needed=2, start_slot=0, end_slot=2) == [0]


def test_find_continuous_free_blocks():
    from scheduler.slots import find_continuous_free_blocks
    # Slot 0 busy, slots 1..3 free, slot 4 busy, slots 5..7 free
    free = [False, True, True, True, False, True, True, True] + [False] * 8
    blocks = find_continuous_free_blocks(free)
    assert len(blocks) == 2
    assert blocks[0] == {"start": "09:30", "end": "11:00", "duration_minutes": 90}
    assert blocks[1] == {"start": "11:30", "end": "13:00", "duration_minutes": 90}
