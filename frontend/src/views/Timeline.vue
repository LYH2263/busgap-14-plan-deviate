<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { fmtDev, devClass } from '../util/deviation'
const data = ref<{ stop_name: string; marks: any[] }>({ stop_name: '', marks: [] })
onMounted(async () => { data.value = await api('/reports/timeline?line_id=1') })
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布（实条=实际到站，虚线刻度=计划到站，同一把尺）</p>
  <div class="card">
    <div class="tl-track">
      <template v-for="m in data.marks" :key="m.trip_no">
        <div v-if="m.scheduled_pct !== null && m.scheduled_pct !== undefined" class="tl-sched"
          :style="{ left: m.scheduled_pct + '%' }"
          :title="m.trip_no + ' 计划 ' + m.scheduled_arrive" />
        <div class="tl-mark"
          :style="{ left: m.pct + '%', background: m.pct < 15 ? 'var(--bg-red)' : 'var(--bg-cyan)' }"
          :title="m.trip_no + ' 实际 ' + m.actual_arrive" />
      </template>
    </div>
    <table>
      <thead><tr><th>班次</th><th>计划到站</th><th>实际到站</th><th>偏离</th><th>相对位置</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td>
          <td>{{ m.scheduled_arrive ?? '—' }}</td>
          <td>{{ m.actual_arrive }}</td>
          <td><span class="badge" :class="devClass(m.deviation_min)">{{ fmtDev(m.deviation_min) }}</span></td>
          <td>{{ m.pct }}%</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
