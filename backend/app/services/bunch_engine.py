"""Bus bunching: planned headway vs actual arrival gaps."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime

@dataclass
class GapEvent:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    planned_headway_min: float
    status: str
    suggestion: str
    earlier_scheduled: str | None = None
    later_scheduled: str | None = None
    earlier_deviation_min: float | None = None
    later_deviation_min: float | None = None

def classify_gap(gap_min: float, planned_headway_min: float, bunch_threshold: float, large_threshold: float) -> tuple[str, str]:
    if gap_min < bunch_threshold:
        return ("bunching", f"间隔 {gap_min:.1f} 分钟低于串车阈值 {bunch_threshold}，建议后车缓行或抽稀。")
    if gap_min > large_threshold:
        return ("large_gap", f"间隔 {gap_min:.1f} 分钟超过大间隔阈值 {large_threshold}，建议前车减速或加发。")
    return ("normal", f"间隔接近计划 {planned_headway_min:.1f} 分钟，保持即可。")

def deviation_min(actual_arrive: datetime, scheduled_arrive: datetime | None) -> float | None:
    """相对计划到站的偏离分钟：实际 − 计划，早到为负、晚到为正；无计划参照时为 None。"""
    if scheduled_arrive is None:
        return None
    return round((actual_arrive - scheduled_arrive).total_seconds() / 60.0, 2)

def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

def detect_bunching(arrivals: list[dict], planned_headway_min: float, bunch_threshold: float, large_threshold: float) -> list[GapEvent]:
    by_stop: dict[str, list[dict]] = {}
    for a in arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)
    events: list[GapEvent] = []
    for stop, items in by_stop.items():
        items = sorted(items, key=lambda x: x["actual_arrive"])
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            status, suggestion = classify_gap(gap_min, planned_headway_min, bunch_threshold, large_threshold)
            events.append(GapEvent(
                stop, prev["trip_no"], cur["trip_no"], round(gap_min, 2), planned_headway_min, status, suggestion,
                earlier_scheduled=_iso(prev.get("scheduled_arrive")),
                later_scheduled=_iso(cur.get("scheduled_arrive")),
                earlier_deviation_min=deviation_min(prev["actual_arrive"], prev.get("scheduled_arrive")),
                later_deviation_min=deviation_min(cur["actual_arrive"], cur.get("scheduled_arrive")),
            ))
    return events

def upgrade_legacy_event(event: dict, refs: dict[tuple[str, str], tuple[datetime, datetime | None]]) -> dict:
    """旧事件结构（无偏离字段）读时升级：按 (站点, 班次) 从计划到站参照回填。
    refs: {(stop_name, trip_no): (actual_arrive, scheduled_arrive)}。已是新结构则原样透传。"""
    upgraded = dict(event)
    if "earlier_deviation_min" not in upgraded:
        actual, scheduled = refs.get((event.get("stop_name"), event.get("earlier_trip")), (None, None))
        upgraded["earlier_scheduled"] = _iso(scheduled)
        upgraded["earlier_deviation_min"] = deviation_min(actual, scheduled) if actual is not None else None
    if "later_deviation_min" not in upgraded:
        actual, scheduled = refs.get((event.get("stop_name"), event.get("later_trip")), (None, None))
        upgraded["later_scheduled"] = _iso(scheduled)
        upgraded["later_deviation_min"] = deviation_min(actual, scheduled) if actual is not None else None
    return upgraded

def events_to_dicts(events: list[GapEvent]) -> list[dict]:
    return [asdict(e) for e in events]
