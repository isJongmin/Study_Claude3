<script setup lang="ts">
import { computed } from 'vue'

// 20px, 1.75px stroke, 둥근 끝선 (custom_design.md 4장). 경로는 고정 문자열만 쓴다.
const P: Record<string, string> = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  hulls: '<path d="M2 18c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0"/><path d="M4 14l-1-4h18l-2 4"/><path d="M9 10V5h6v5"/>',
  plans: '<path d="M4 6h10M8 12h12M6 18h9"/>',
  progress: '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
  drawings: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
  approvals: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
  users: '<path d="M16 19v-1a4 4 0 00-4-4H8a4 4 0 00-4 4v1"/><circle cx="10" cy="7.5" r="3.5"/><path d="M20 19v-1a3.5 3.5 0 00-2.5-3.3M16 4.2a3.5 3.5 0 010 6.6"/>',
  alert: '<path d="M12 8v5M12 16.5v.01"/><path d="M10.3 3.9L2.4 18a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  ship: '<path d="M2 18c2 1.5 4 1.5 6 0s4-1.5 6 0 4 1.5 6 0"/><path d="M4 14l-1-4h18l-2 4"/><path d="M9 10V5h6v5"/>',
}
const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 20 })
const html = computed(() => P[props.name] || '')
</script>

<template>
  <svg class="icon" :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="html"></svg>
</template>
