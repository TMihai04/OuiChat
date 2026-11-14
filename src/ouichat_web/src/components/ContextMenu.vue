<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"

const props = defineProps<{
  x: number
  y: number
  items: { id: string; label: string }[]
}>()

const emit = defineEmits<{ pick: [id: string]; close: [] }>()

const menuEl = ref<HTMLElement | null>(null)
const adjustedX = ref(props.x)
const adjustedY = ref(props.y)
const isVisible = ref(false)

function adjustPosition() {
  if (!menuEl.value) return
  const rect = menuEl.value.getBoundingClientRect()
  const vw = window.visualViewport?.width ?? window.innerWidth
  const vh = window.visualViewport?.height ?? window.innerHeight
  const padding = 8

  let top = props.y
  let left = props.x

  // If opening downward would push the menu below the bottom edge of the screen:
  if (props.y + rect.height + padding > vh) {
    // Render h pixels above the click/touch point
    top = Math.max(padding, props.y - rect.height)
  } else {
    top = Math.max(padding, props.y)
  }

  // If opening to the right would push the menu past the right edge of the screen:
  if (props.x + rect.width + padding > vw) {
    left = Math.max(padding, vw - rect.width - padding)
  } else {
    left = Math.max(padding, props.x)
  }

  adjustedX.value = left
  adjustedY.value = top
  isVisible.value = true
}

function onPointerDown(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest(".menu")) return
  emit("close")
}

onMounted(async () => {
  window.addEventListener("pointerdown", onPointerDown)
  await nextTick()
  adjustPosition()
})

onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", onPointerDown)
})

watch(() => [props.x, props.y, props.items], async () => {
  isVisible.value = false
  await nextTick()
  adjustPosition()
})
</script>

<template>
  <div
    ref="menuEl"
    class="menu"
    :style="{
      left: `${adjustedX}px`,
      top: `${adjustedY}px`,
      visibility: isVisible ? 'visible' : 'hidden'
    }"
    @pointerdown.stop
    @contextmenu.prevent
  >
    <button v-for="item in items" :key="item.id" type="button" @click="emit('pick', item.id)">
      {{ item.label }}
    </button>
  </div>
</template>
