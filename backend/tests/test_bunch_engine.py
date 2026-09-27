from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching, deviation_min, upgrade_legacy_event

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

def test_deviation_signs():
    base = datetime(2026, 1, 1, 8, 0)
    assert deviation_min(base, base + timedelta(minutes=5)) == -5.0   # 早到为负
    assert deviation_min(base + timedelta(minutes=3), base) == 3.0    # 晚到为正
    assert deviation_min(base, base) == 0.0                            # 正点
    assert deviation_min(base, None) is None                           # 无计划参照

def test_detect_carries_deviations():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base,
         "scheduled_arrive": base + timedelta(minutes=1)},            # 早到 1
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2),
         "scheduled_arrive": base + timedelta(minutes=2)},            # 正点
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert events[0].earlier_deviation_min == -1.0
    assert events[0].later_deviation_min == 0.0
    assert events[0].earlier_scheduled is not None

def test_detect_without_scheduled_is_none():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert events[0].earlier_deviation_min is None
    assert events[0].later_deviation_min is None

def test_upgrade_legacy_event_backfills():
    base = datetime(2026, 1, 1, 8, 0)
    legacy = {"stop_name": "A", "earlier_trip": "T1", "later_trip": "T2",
              "gap_min": 2.0, "planned_headway_min": 8.0, "status": "bunching", "suggestion": ""}
    refs = {
        ("A", "T1"): (base, base + timedelta(minutes=2)),   # 早到 2
        ("A", "T2"): (base + timedelta(minutes=2), base),   # 晚到 2
    }
    upgraded = upgrade_legacy_event(legacy, refs)
    assert upgraded["earlier_deviation_min"] == -2.0
    assert upgraded["later_deviation_min"] == 2.0
    assert upgraded["status"] == "bunching"  # 判定等原字段不被改动

def test_upgrade_legacy_event_passthrough():
    event = {"stop_name": "A", "earlier_trip": "T1", "later_trip": "T2",
             "earlier_deviation_min": -1.0, "later_deviation_min": 4.0}
    assert upgrade_legacy_event(event, {}) == event
