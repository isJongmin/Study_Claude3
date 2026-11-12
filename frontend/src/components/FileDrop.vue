<script setup lang="ts">
import { ref } from 'vue'
import { useUi } from '../stores/ui'

// PDF 한 개를 클릭해서 고르거나 끌어 놓아 선택한다. 업로드는 호출한 쪽이 저장할 때 함께 한다.
const props = defineProps<{ modelValue: File | null; testId?: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [File | null] }>()
const ui = useUi()
const over = ref(false), input = ref<HTMLInputElement>()
function take(f?: File) {
  if (!f) return
  if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') return ui.toast('PDF 파일만 올릴 수 있습니다.', 'e')
  emit('update:modelValue', f)
}
function onDrop(e: DragEvent) { over.value = false; if (!props.disabled) take(e.dataTransfer?.files?.[0]) }
function clear() { emit('update:modelValue', null); if (input.value) input.value.value = '' }
const size = (n: number) => (n > 1048576 ? (n / 1048576).toFixed(1) + 'MB' : Math.max(1, Math.round(n / 1024)) + 'KB')
</script>

<template>
  <div class="fdrop">
    <label class="drop" :class="{ over, off: disabled }" @dragover.prevent="over = true" @dragleave="over = false" @drop.prevent="onDrop">
      <input ref="input" type="file" accept=".pdf,application/pdf" :disabled="disabled" :data-test="testId" aria-label="도면 PDF 선택" @change="take(($event.target as HTMLInputElement).files?.[0])">
      <span v-if="!modelValue">PDF를 끌어 놓거나 눌러서 선택 (선택 사항)</span>
      <span v-else class="picked">📎 {{ modelValue.name }} <small>{{ size(modelValue.size) }}</small></span>
    </label>
    <button v-if="modelValue" type="button" class="btn sm" :disabled="disabled" @click="clear">선택 취소</button>
  </div>
</template>
