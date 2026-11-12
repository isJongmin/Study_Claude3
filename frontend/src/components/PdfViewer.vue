<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import type { PDFDocumentProxy, PDFDocumentLoadingTask, RenderTask } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';

const props = defineProps<{ url: string }>();
const doc = shallowRef<PDFDocumentProxy | null>(null);
const page = ref(1);
const zoom = ref(1);
const width = ref(0);
const height = ref(0);
const busy = ref(false);
const error = ref('');
const surface = ref<HTMLDivElement>();
const canvas = ref<HTMLCanvasElement>();
let loadingTask: PDFDocumentLoadingTask | null = null;
let renderTask: RenderTask | null = null;
let sequence = 0;
let observer: ResizeObserver | null = null;

async function load() {
  const current = ++sequence;
  renderTask?.cancel();
  void loadingTask?.destroy();
  doc.value = null;
  page.value = 1;
  zoom.value = 1;
  error.value = '';
  if (!props.url) return;
  busy.value = true;
  try {
    const pdfjs = await import('pdfjs-dist');
    pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
    if (current !== sequence) return;
    loadingTask = pdfjs.getDocument({ url: props.url });
    const loaded = await loadingTask.promise;
    if (current !== sequence) return;
    doc.value = loaded;
  } catch {
    if (current === sequence) error.value = 'PDF를 표시하지 못했습니다. 새 창으로 열어 확인하세요.';
  } finally {
    if (current === sequence) busy.value = false;
  }
}

async function render() {
  if (!doc.value || !canvas.value || !width.value) return;
  const current = sequence;
  renderTask?.cancel();
  try {
    const pdfPage = await doc.value.getPage(page.value);
    if (current !== sequence) return;
    await nextTick();
    const target = canvas.value;
    const context = target?.getContext('2d');
    if (!target || !context) return;
    const base = pdfPage.getViewport({ scale: 1 });
    const fit = Math.min((width.value - 40) / base.width, (height.value - 56) / base.height);
    const scale = Math.min(1.6, Math.max(0.3, fit)) * zoom.value;
    const viewport = pdfPage.getViewport({ scale });
    const pixelRatio = window.devicePixelRatio || 1;
    target.width = Math.floor(viewport.width * pixelRatio);
    target.height = Math.floor(viewport.height * pixelRatio);
    target.style.width = `${viewport.width}px`;
    target.style.height = `${viewport.height}px`;
    renderTask = pdfPage.render({ canvas: target, canvasContext: context, viewport, transform: pixelRatio === 1 ? undefined : [pixelRatio, 0, 0, pixelRatio, 0, 0] });
    await renderTask.promise;
  } catch (reason) {
    if (current === sequence && !(reason instanceof Error && reason.name === 'RenderingCancelledException')) {
      error.value = 'PDF 페이지를 표시하지 못했습니다. 새 창으로 열어 확인하세요.';
    }
  }
}

watch(() => props.url, () => void load(), { immediate: true });
watch([doc, page, zoom, width, height], () => void render(), { flush: 'post' });
onMounted(() => {
  observer = new ResizeObserver(() => { width.value = surface.value?.clientWidth ?? 0; height.value = surface.value?.clientHeight ?? 0; });
  if (surface.value) observer.observe(surface.value);
});
onBeforeUnmount(() => {
  sequence++;
  observer?.disconnect();
  renderTask?.cancel();
  void loadingTask?.destroy();
});
</script>

<template>
  <div ref="surface" class="pdfbox pdf-viewer" data-test="pdf-viewer" aria-label="도면 PDF 뷰어">
    <div class="pdf-toolbar">
      <button class="btn sm" type="button" aria-label="이전 페이지" :disabled="!doc || page <= 1" @click="page--">‹</button>
      <span>{{ doc ? `${page} / ${doc.numPages}` : '– / –' }}</span>
      <button class="btn sm" type="button" aria-label="다음 페이지" :disabled="!doc || page >= doc.numPages" @click="page++">›</button>
      <span class="sp"></span>
      <button class="btn sm" type="button" aria-label="축소" :disabled="!doc || zoom <= 0.5" @click="zoom = Math.max(0.5, zoom - 0.25)">−</button>
      <span>{{ Math.round(zoom * 100) }}%</span>
      <button class="btn sm" type="button" aria-label="확대" :disabled="!doc || zoom >= 2" @click="zoom = Math.min(2, zoom + 0.25)">+</button>
    </div>
    <div class="pdf-scroll">
      <canvas v-show="doc && !error" ref="canvas" aria-label="PDF 페이지" role="img"></canvas>
      <p v-if="busy || error || !url" class="pdf-placeholder" role="status">{{ error || (busy ? 'PDF를 여는 중입니다.' : '표시할 PDF가 없습니다.') }}</p>
    </div>
  </div>
</template>
