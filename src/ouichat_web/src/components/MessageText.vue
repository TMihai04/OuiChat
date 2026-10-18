<script setup lang="ts">
import { computed } from "vue"

const props = defineProps<{ text: string }>()

const parts = computed(() => {
  const pattern = /https?:\/\/[^\s<>"']+/gi
  const pieces: { kind: "text" | "link"; value: string }[] = []
  let cursor = 0
  for (const match of props.text.matchAll(pattern)) {
    const start = match.index ?? 0
    if (start > cursor) pieces.push({ kind: "text", value: props.text.slice(cursor, start) })
    const raw = match[0]
    const value = raw.replace(/[),.!?:;]+$/u, "")
    pieces.push({ kind: "link", value })
    if (value.length < raw.length) pieces.push({ kind: "text", value: raw.slice(value.length) })
    cursor = start + raw.length
  }
  if (cursor < props.text.length) pieces.push({ kind: "text", value: props.text.slice(cursor) })
  return pieces
})
</script>

<template>
  <p class="message-text">
    <template v-for="(part, index) in parts" :key="index">
      <a v-if="part.kind === 'link'" :href="part.value" target="_blank" rel="noopener noreferrer">{{ part.value }}</a>
      <template v-else>{{ part.value }}</template>
    </template>
  </p>
</template>
