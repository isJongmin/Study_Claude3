<script setup lang="ts">
import { computed } from 'vue'
import { useUi } from '../stores/ui'

// kind: plan(공정상태) | dwg(도면/리비전 상태) | hull(호선상태)
const props = defineProps<{ kind: 'plan' | 'dwg' | 'hull'; code: string }>()
const ui = useUi()
const group = computed(() => ({ plan: 'PLANSTAT', dwg: 'DWGSTAT', hull: 'HULLSTAT' }[props.kind]))
const cls = computed(() => (props.kind === 'plan' ? 's-' + props.code : props.kind === 'dwg' ? 'd-' + props.code : 'b-info'))
</script>

<template>
  <span class="bdg" :class="cls" :data-test="`badge-${kind}-${code}`">{{ ui.cn(group, code) }}</span>
</template>
