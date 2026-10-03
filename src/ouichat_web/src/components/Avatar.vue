<script setup lang="ts">
import { ref, watch } from "vue"
import { useAppStore } from "../stores/app"

const props = withDefaults(defineProps<{
  domain: string
  pictureId?: string | null
  fallback: string
  size?: number
  clickable?: boolean
}>(), {
  pictureId: null,
  size: 32,
  clickable: false,
})

const emit = defineEmits<{ click: [] }>()
const store = useAppStore()
const src = ref(props.fallback)
let request = 0

watch(() => [props.domain, props.pictureId, props.fallback] as const, async ([domain, pictureId, fallback]) => {
  const ticket = ++request
  src.value = fallback
  if (!pictureId) return
  const resolved = await store.resolveIcon(domain, pictureId, fallback)
  if (ticket === request) src.value = resolved
}, { immediate: true })
</script>

<template>
  <button v-if="clickable" class="icon-button" type="button" @click="emit('click')">
    <img class="avatar" :style="{ width: `${size}px`, height: `${size}px` }" :src="src" alt="" />
  </button>
  <img v-else class="avatar" :style="{ width: `${size}px`, height: `${size}px` }" :src="src" alt="" />
</template>
