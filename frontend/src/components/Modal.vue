<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

defineProps<{ title: string; small?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const root = ref<HTMLElement>()
let opener: HTMLElement | null = null

const focusables = () => [...(root.value?.querySelectorAll<HTMLElement>('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])') || [])].filter((e) => e.offsetParent !== null)
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') { e.stopPropagation(); emit('close') }
  if (e.key === 'Tab') { // 포커스를 모달 안에 가둔다
    const f = focusables()
    if (!f.length) return
    const first = f[0], last = f[f.length - 1]
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
  }
}
onMounted(() => {
  opener = document.activeElement as HTMLElement | null
  window.addEventListener('keydown', onKey)
  ;(root.value?.querySelector<HTMLElement>('[data-autofocus]') || root.value)?.focus() // 열릴 때 내부로 포커스 이동
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  opener?.focus?.() // 닫을 때 원래 위치로
})
</script>

<template>
  <div class="mask" @mousedown.self="emit('close')">
    <div ref="root" class="modal" :class="{ sm: small }" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1" data-test="modal">
      <header><span>{{ title }}</span><button class="x" aria-label="닫기" data-test="modal-close" @click="emit('close')">×</button></header>
      <div class="mb"><slot /></div>
    </div>
  </div>
</template>
