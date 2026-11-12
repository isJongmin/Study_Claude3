<script setup lang="ts">
defineProps<{ value: number }>()
</script>

<template>
  <div class="pbar"><div class="t"><i :style="{ width: Math.min(100, value) + '%' }"></i></div><b>{{ value }}%</b></div>
</template>
