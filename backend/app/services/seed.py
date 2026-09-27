from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.config import settings
from app.models.models import Arrival, Line, Trip

def planned_arrive_at(planned_depart: datetime, stop_seq: int) -> datetime:
    """计划到站 = 计划发车 + 站序 × 单站计划运行分钟（报告/时间轴/到站共用参照的来源）。"""
    return planned_depart + timedelta(minutes=stop_seq * settings.planned_stop_runtime_min)

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Line)) or 0) > 0:
        return
    base = datetime(2026, 9, 17, 7, 0, 0)
    line = Line(code="B12", name="城东环线", planned_headway_min=8.0, bunch_threshold=3.0, large_threshold=15.0)
    db.add(line); db.flush()
    specs = [("T01", "粤A1001", 0), ("T02", "粤A1002", 2), ("T03", "粤A1003", 18), ("T04", "粤A1004", 26)]
    stops = ["起点站", "市民中心", "火车站", "终点站"]
    # 相对计划到站的偏离分钟（早到为负、晚到为正），键为 (班次, 站点)
    deviations = {
        ("T02", "市民中心"): -1,   # 早到 1 分，与 T01 在市民中心形成串车
        ("T03", "市民中心"): 2,    # 晚点 2 分，与 T02 拉开成大间隔
        ("T03", "火车站"): 3,
        ("T03", "终点站"): 2,
    }
    for trip_no, vehicle, offset in specs:
        planned_depart = base + timedelta(minutes=offset)
        trip = Trip(line_id=line.id, trip_no=trip_no, planned_depart=planned_depart, vehicle_no=vehicle)
        db.add(trip); db.flush()
        for seq, stop in enumerate(stops):
            scheduled = planned_arrive_at(planned_depart, seq)
            arrive = scheduled + timedelta(minutes=deviations.get((trip_no, stop), 0))
            db.add(Arrival(trip_id=trip.id, stop_name=stop, stop_seq=seq,
                           actual_arrive=arrive, scheduled_arrive=scheduled))
    db.commit()

def backfill_scheduled(db: Session) -> None:
    """旧数据没有计划到站列值时，按计划发车+站序×运行分钟回填（只补缺失，不覆盖）。"""
    rows = db.scalars(
        select(Arrival).options(joinedload(Arrival.trip)).where(Arrival.scheduled_arrive.is_(None))
    ).unique().all()
    if not rows:
        return
    for a in rows:
        a.scheduled_arrive = planned_arrive_at(a.trip.planned_depart, a.stop_seq)
    db.commit()
