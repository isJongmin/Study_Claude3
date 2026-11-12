<script setup lang="ts">
import { computed, useId } from 'vue'

// 흰 선체 모형 안에 진척률만큼 물이 차 있다. 선종별로 갑판 위 화물이 다르다(LNG 돔·컨테이너·탱커).
const props = defineProps<{ progress: number; type?: string | null }>()
const id = useId()
const value = computed(() => Math.min(100, Math.max(0, Number(props.progress) || 0)))
const DECK = 46, DEPTH = 36
const HULL = 'M10 46H190L178 72Q174 82 162 82H36Q24 82 18 70Z'
const level = computed(() => `${((100 - value.value) / 100) * DEPTH}px`)
const WAVE = `M-40 ${DECK}${'q10-2 20 0t20 0'.repeat(7)}`
const kind = computed(() => (props.type === 'LNG' || props.type === 'CONT' ? props.type : 'TANK'))
const DOMES = [80, 110, 140, 170]
const STACKS = [[66, 2], [86, 3], [106, 3], [126, 2], [146, 3], [166, 2]]
const boxes = STACKS.flatMap(([x, rows], c) => Array.from({ length: rows }, (_, r) => ({ x, y: 39 - 7 * (r + 1), tone: (c + r) % 4 })))
</script>

<template>
  <svg class="ship-art" viewBox="0 0 200 92" role="img" :aria-label="`진척률 ${value}%`">
    <defs>
      <clipPath :id="`${id}c`"><path :d="HULL" /></clipPath>
      <linearGradient :id="`${id}h`" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" /><stop offset="1" stop-color="#DCE6F1" /></linearGradient>
      <linearGradient :id="`${id}w`" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7CC4FA" /><stop offset="1" stop-color="#1F6FE0" /></linearGradient>
    </defs>
    <ellipse class="ship-shadow" cx="100" cy="86" rx="86" ry="4" />
    <path class="ship-deck" d="M10 46L18 40H196L190 46Z" />
    <path class="ship-side" d="M52 46V22L58 17V41Z" />
    <path class="ship-face" d="M24 46V22H52V46Z" />
    <path class="ship-top" d="M24 22L30 17H58L52 22Z" />
    <path class="ship-win" d="M28 28H48M28 34H48" />
    <path class="ship-face" d="M33 22V9H43V22Z" />
    <path class="ship-band" d="M33 11H43V14H33Z" />
    <g v-if="kind === 'LNG'" class="ship-dome"><path v-for="x in DOMES" :key="x" :d="`M${x - 13} 42A13 13 0 0 1 ${x + 13} 42Z`" /></g>
    <g v-else-if="kind === 'CONT'"><rect v-for="(b, i) in boxes" :key="i" :class="`ship-box t${b.tone}`" :x="b.x" :y="b.y" width="18" height="6.5" rx="1" /></g>
    <g v-else>
      <path class="ship-face" d="M150 42V34H164V42Z" />
      <path class="ship-win" d="M64 40H146M80 40V43M100 40V43M128 40V43M112 40V24M112 26L130 34" />
    </g>
    <path class="ship-hull" :d="HULL" :fill="`url(#${id}h)`" />
    <g :clip-path="`url(#${id}c)`">
      <g v-if="value" class="ship-water" :style="{ '--y': level }">
        <path :d="`${WAVE}V130H-40Z`" :fill="`url(#${id}w)`" />
        <path class="ship-surface" :d="WAVE" />
      </g>
    </g>
    <path class="ship-outline" :d="HULL" />
    <path class="ship-gloss" d="M24 52H176" />
  </svg>
</template>
