<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue"

defineProps<{
  x: number
  y: number
  items: { id: string; label: string }[]
}>()

const emit = defineEmits<{ pick: [id: string]; close: [] }>()

function onPointerDown(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest(".menu")) return
  emit("close")
}

onMounted(() => {
  window.addEventListener("pointerdown", onPointerDown)
})

onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", onPointerDown)
})
</script>

<template>
  <div class="menu" :style="{ left: `${x}px`, top: `${y}px` }" @pointerdown.stop @contextmenu.prevent>
    <button v-for="item in items" :key="item.id" type="button" @click="emit('pick', item.id)">
      {{ item.label }}
    </button>
  </div>
</template>
