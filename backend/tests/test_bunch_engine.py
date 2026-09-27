from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching
from app.services.schedule import deviation_min, planned_arrive_at

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def test_detect_events_carry_deviations():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base - timedelta(minutes=2),
         "planned_arrive": base},                                  # 早到 2 分
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=4),
         "planned_arrive": base + timedelta(minutes=1)},           # 晚到 3 分
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 1
    assert events[0].earlier_dev_min == -2.0
    assert events[0].later_dev_min == 3.0

def test_detect_events_without_planned_reference():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert events[0].earlier_dev_min is None
    assert events[0].later_dev_min is None

def test_deviation_sign_convention():
    planned = datetime(2026, 1, 1, 9, 0)
    assert deviation_min(planned - timedelta(minutes=5), planned) == -5.0  # 早到为负
    assert deviation_min(planned + timedelta(minutes=7), planned) == 7.0   # 晚到为正
    assert deviation_min(planned, planned) == 0.0

def test_planned_arrive_at_uses_stop_seq():
    depart = datetime(2026, 1, 1, 7, 0)
    assert planned_arrive_at(depart, 0) == depart
    assert planned_arrive_at(depart, 3) == depart + timedelta(minutes=18)
