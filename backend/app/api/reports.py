import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.models import Arrival, BunchReport, Line, Trip
from app.services.bunch_engine import detect_bunching, deviation_min, events_to_dicts, upgrade_legacy_event
router = APIRouter(prefix="/reports", tags=["reports"])

def _schedule_refs(db: Session, line_id: int) -> dict[tuple[str, str], tuple[datetime, datetime | None]]:
    """该线路 (站点, 班次) -> (实际到站, 计划到站)，供旧报告事件读时回填偏离。"""
    trips = db.scalars(select(Trip).where(Trip.line_id == line_id)).all()
    trip_ids = [t.id for t in trips]
    trip_no_map = {t.id: t.trip_no for t in trips}
    rows = db.scalars(
        select(Arrival).options(joinedload(Arrival.trip)).where(Arrival.trip_id.in_(trip_ids))
    ).unique().all()
    return {(a.stop_name, trip_no_map[a.trip_id]): (a.actual_arrive, a.scheduled_arrive) for a in rows}

@router.get("")
def list_reports(db: Session = Depends(get_db)):
    out = []
    for r in db.scalars(select(BunchReport).order_by(BunchReport.id.desc())).all():
        refs = _schedule_refs(db, r.line_id)
        events = [upgrade_legacy_event(e, refs) for e in json.loads(r.summary_json)]
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
    arrivals = db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids))).all()
    payload = [{"stop_name": a.stop_name, "trip_no": trip_no_map[a.trip_id],
                "actual_arrive": a.actual_arrive, "scheduled_arrive": a.scheduled_arrive}
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
    arrivals = sorted(db.scalars(select(Arrival).where(Arrival.trip_id.in_(trip_ids), Arrival.stop_name == stop_name)).all(),
                      key=lambda a: a.actual_arrive)
    if not arrivals: return {"stop_name": stop_name, "marks": []}
    all_ts = [t for a in arrivals for t in (a.actual_arrive, a.scheduled_arrive) if t is not None]
    t0 = min(all_ts)
    span = max((max(all_ts) - t0).total_seconds(), 1)
    def pct(ts: datetime | None) -> float | None:
        if ts is None: return None
        return round((ts - t0).total_seconds() / span * 100, 2)
    marks = [{"trip_no": trip_no_map[a.trip_id], "actual_arrive": a.actual_arrive.isoformat(),
              "scheduled_arrive": a.scheduled_arrive.isoformat() if a.scheduled_arrive else None,
              "deviation_min": deviation_min(a.actual_arrive, a.scheduled_arrive),
              "pct": pct(a.actual_arrive), "scheduled_pct": pct(a.scheduled_arrive)} for a in arrivals]
    return {"stop_name": stop_name, "marks": marks}
