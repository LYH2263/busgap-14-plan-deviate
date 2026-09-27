"""计划参照：班次在各站的计划到点与偏离计算。

全系统共用同一参照：计划到点 = 班次计划发车 + 站序 × 每站计划运行分钟。
串车报告、时间轴、到站核对都以此为准，保证同一班的偏离口径一致。
"""
from __future__ import annotations
from datetime import datetime, timedelta

STOP_TRAVEL_MIN = 6.0  # 每站计划运行分钟（与种子数据一致）


def planned_arrive_at(planned_depart: datetime, stop_seq: int) -> datetime:
    """班次在指定站序的计划到点。"""
    return planned_depart + timedelta(minutes=STOP_TRAVEL_MIN * stop_seq)


def deviation_min(actual_arrive: datetime, planned_arrive: datetime) -> float:
    """实际到点相对计划参照的偏离分钟：早到为负，晚到为正。"""
    return round((actual_arrive - planned_arrive).total_seconds() / 60.0, 2)
