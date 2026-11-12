<script setup lang="ts">
import { computed } from 'vue'

// 둥근 끝 도넛. 조각 사이에 작은 틈을 두고, 가운데에 합계를 크게 보여 준다.
const props = defineProps<{ items: { label: string; value: number; color: string }[]; unit?: string; caption?: string; center?: string | number; mini?: boolean; side?: boolean }>()
const total = computed(() => props.items.reduce((s, i) => s + i.value, 0))
const R = 38, C = 2 * Math.PI * R, GAP = 3
const arcs = computed(() => {
  const live = props.items.filter((i) => i.value > 0)
  let off = 0
  return live.map((i) => {
    const part = (i.value / total.value) * C
    const len = live.length > 1 ? Math.max(0.1, part - GAP) : part
    const a = { color: i.color, dash: `${len} ${C - len}`, off: -off }
    off += part
    return a
  })
})
const pct = (n: number) => (total.value ? Math.round((n / total.value) * 100) : 0)
</script>

<template>
  <div class="donut" :class="{ mini, side }">
    <div class="ring">
      <svg viewBox="0 0 100 100" role="img" :aria-label="`${caption || '분포'} 도넛 차트, 합계 ${total}${unit || '건'}`">
        <circle cx="50" cy="50" :r="R" fill="none" stroke="var(--neutral-soft)" stroke-width="9" />
        <circle v-for="(a, i) in arcs" :key="i" class="arc" cx="50" cy="50" :r="R" fill="none" :stroke="a.color" stroke-width="9"
          stroke-linecap="round" :stroke-dasharray="a.dash" :stroke-dashoffset="a.off" transform="rotate(-90 50 50)" />
      </svg>
      <div class="mid"><b>{{ center ?? total }}</b><small>{{ caption || unit || '건' }}</small></div>
    </div>
    <ul v-if="!mini" class="legend">
      <li v-for="i in items" :key="i.label" :class="{ zero: !i.value }">
        <i :style="{ background: i.color }"></i><span class="lb">{{ i.label }}</span>
        <b class="n">{{ i.value }}<small>{{ unit || '건' }}</small></b><span class="pc">{{ pct(i.value) }}%</span>
      </li>
    </ul>
  </div>
</template>
