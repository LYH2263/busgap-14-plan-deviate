<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { fmtDev, devClass } from '../util/deviation'
const tips = ref<any[]>([])
onMounted(async () => { tips.value = (await api('/reports/suggestions?line_id=1')).suggestions })
</script>
<template>
  <h1>建议</h1>
  <p class="sub">针对串车与大间隔的调班提示</p>
  <div class="card" v-for="(t,i) in tips" :key="i">
    <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
    <div class="bg-gap-dev" style="margin-top:0.3rem">
      <span>前班 {{ t.earlier_trip }}</span>
      <span class="badge" :class="devClass(t.earlier_deviation_min)">{{ fmtDev(t.earlier_deviation_min) }}</span>
    </div>
    <div class="bg-gap-dev">
      <span>后班 {{ t.later_trip }}</span>
      <span class="badge" :class="devClass(t.later_deviation_min)">{{ fmtDev(t.later_deviation_min) }}</span>
    </div>
    <p class="muted">{{ t.suggestion }}</p>
  </div>
  <p v-if="!tips.length" class="muted">暂无异常建议</p>
</template>
