<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ page: number; pages: number; total: number; size: number; unit?: string }>()
const emit = defineEmits<{ (e: 'update:page', v: number): void }>()
const go = (n: number) => emit('update:page', Math.min(props.pages, Math.max(1, n)))
// 현재 쪽 주변 5개만 번호로 보여 준다.
const nums = computed(() => {
  const s = Math.max(1, Math.min(props.page - 2, props.pages - 4)), e = Math.min(props.pages, s + 4)
  return Array.from({ length: e - s + 1 }, (_, i) => s + i)
})
const from = computed(() => (props.total ? (props.page - 1) * props.size + 1 : 0))
const to = computed(() => Math.min(props.total, props.page * props.size))
</script>

<template>
  <div class="pager" data-test="pager">
    <span class="pg-info">총 {{ total }}{{ unit || '건' }}<template v-if="pages > 1"> · {{ from }}–{{ to }}</template></span>
    <nav v-if="pages > 1" class="pg-nav" aria-label="페이지 이동">
      <button type="button" aria-label="이전 쪽" data-test="pager-prev" :disabled="page <= 1" @click="go(page - 1)">‹</button>
      <button v-for="n in nums" :key="n" type="button" :class="{ act: n === page }" :aria-current="n === page ? 'page' : undefined" :data-test="'pager-' + n" @click="go(n)">{{ n }}</button>
      <button type="button" aria-label="다음 쪽" data-test="pager-next" :disabled="page >= pages" @click="go(page + 1)">›</button>
    </nav>
  </div>
</template>
