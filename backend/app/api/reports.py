import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, events_to_dicts
from app.services.schedule import deviation_min, planned_arrive_at
router = APIRouter(prefix="/reports", tags=["reports"])

def _deviation_lookup(db: Session, line_id: int) -> dict[tuple[str, str], float]:
    """(trip_no, stop_name) -> 相对计划参照的偏离分钟，与检测/时间轴同一参照。"""
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    planned_depart = {t.id: t.planned_depart for t in trips}
    trip_no = {t.id: t.trip_no for t in trips}
    if not trips: return {}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(planned_depart.keys()))).all()
    return {(trip_no[a.trip_id], a.stop_name): deviation_min(a.actual_arrive, planned_arrive_at(planned_depart[a.trip_id], a.stop_seq))
            for a in arrivals}

def _upgrade_events(events: list[dict], lookup: dict[tuple[str, str], float]) -> bool:
    """旧事件结构缺少偏离字段时补齐；返回是否有改动。"""
    changed = False
    for e in events:
        if "earlier_dev_min" in e and "later_dev_min" in e: continue
        e["earlier_dev_min"] = lookup.get((e.get("earlier_trip"), e.get("stop_name")))
        e["later_dev_min"] = lookup.get((e.get("later_trip"), e.get("stop_name")))
        changed = True
    return changed

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    rows = db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all()
    lookups: dict[int, dict] = {}
    out = []
    for r in rows:
        events = json.loads(r.summary_json)
        if any("earlier_dev_min" not in e or "later_dev_min" not in e for e in events):
            if r.line_id not in lookups:
                lookups[r.line_id] = _deviation_lookup(db, r.line_id)
            if _upgrade_events(events, lookups[r.line_id]):
                r.summary_json = json.dumps(events, ensure_ascii=False)
                db.commit()
        out.append({"id": r.id, "line_id": r.line_id, "stop_name": r.stop_name,
                    "created_at": r.created_at.isoformat(), "events": events})
    return out

@router.post("/run")
def run_detection(line_id: int, stop_name: str | None = None, db: Session = Depends(get_db)):
    line = db.get(Line, line_id)
    if not line: raise HTTPException(404, "线路不存在")
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    planned_depart_map = {t.id: t.planned_depart for t in trips}
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive,
                "planned_arrive": planned_arrive_at(planned_depart_map[a.trip_id], a.stop_seq)}
               for a in arrivals if stop_name is None or a.stop_name == stop_name]
    events = detect_bunching(payload, line.planned_headway_min, line.bunch_threshold, line.large_threshold)
    data = events_to_dicts(events)
    report = BunchReport(line_id=line_id, stop_name=stop_name or "*", created_at=datetime.utcnow(),
                         summary_json=json.dumps(data, ensure_ascii=False))
    db.add(report); db.commit(); db.refresh(report)
    return {"id": report.id, "events": data}

@router.get("/suggestions")
def suggestions(line_id: int, db: Session = Depends(get_db)):
    result = run_detection(line_id=line_id, stop_name=None, db=db)
    return {"line_id": line_id, "suggestions": [e for e in result["events"] if e["status"] != "normal"]}

@router.get("/timeline")
def timeline(line_id: int, stop_name: str = "市民中心", db: Session = Depends(get_db)):
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    planned_depart_map = {t.id: t.planned_depart for t in trips}
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": []}
    t0 = arrivals[0].actual_arrive
    span = max((arrivals[-1].actual_arrive - t0).total_seconds(), 1)
    marks = []
    for a in arrivals:
        planned = planned_arrive_at(planned_depart_map[a.trip_id], a.stop_seq)
        marks.append({"trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive.isoformat(),
                      "planned_arrive": planned.isoformat(),
                      "dev_min": deviation_min(a.actual_arrive, planned),
                      "pct": round((a.actual_arrive - t0).total_seconds() / span * 100, 2)})
    return {"stop_name": stop_name, "marks": marks}
