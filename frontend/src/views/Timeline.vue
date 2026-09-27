<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<{ stop_name: string; marks: any[] }>({ stop_name: '', marks: [] })
onMounted(async () => { data.value = await api('/reports/timeline?line_id=1') })
function fmtDev(v: number | null | undefined) {
  if (v === null || v === undefined) return '—'
  return (v > 0 ? '+' : '') + v + '′'
}
function devClass(v: number | null | undefined) {
  if (v === null || v === undefined || v === 0) return 'dev-zero'
  return v > 0 ? 'dev-late' : 'dev-early'
}
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布 · 偏离为相对计划到点（早到为负、晚到为正）</p>
  <div class="card">
    <div class="tl-track">
      <div v-for="m in data.marks" :key="m.trip_no" class="tl-mark"
        :style="{ left: m.pct + '%', background: m.pct < 15 ? 'var(--bg-red)' : 'var(--bg-cyan)' }"
        :title="m.trip_no + ' ' + m.actual_arrive" />
    </div>
    <table>
      <thead><tr><th>班次</th><th>计划到站</th><th>实际到站</th><th>偏离</th><th>相对位置</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td>
          <td>{{ m.planned_arrive }}</td>
          <td>{{ m.actual_arrive }}</td>
          <td><b :class="devClass(m.dev_min)">{{ fmtDev(m.dev_min) }}</b></td>
          <td>{{ m.pct }}%</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
