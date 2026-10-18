<script setup lang="ts">
import { ref, watch } from "vue"
import { useAppStore } from "../stores/app"

const props = defineProps<{
  domain: string
  fileId: string
}>()

const store = useAppStore()
const name = ref(props.fileId)
let request = 0

watch(() => [props.domain, props.fileId] as const, async ([domain, fileId]) => {
  const ticket = ++request
  name.value = fileId
  const resolved = await store.resolveAttachmentName(domain, fileId)
  if (ticket === request) name.value = resolved
}, { immediate: true })
</script>

<template>
  <span>{{ name }}</span>
</template>
