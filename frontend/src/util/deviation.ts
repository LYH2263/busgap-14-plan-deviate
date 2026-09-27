/** 相对计划到站的偏离分钟展示：早到为负、晚到为正；无参照显示 — */
export function fmtDev(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  if (v === 0) return '0′ 正点'
  return v < 0 ? `${v}′ 早到` : `+${v}′ 晚到`
}

/** 早到/晚到配色类，供报告、时间轴、到站统一使用（配合 .badge） */
export function devClass(v: number | null | undefined): string {
  if (v === null || v === undefined) return 'badge-none'
  if (v === 0) return 'badge-ok'
  return v < 0 ? 'dev-early' : 'dev-late'
}
