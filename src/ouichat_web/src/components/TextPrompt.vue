<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue"

const props = defineProps<{
  title: string
  label: string
  placeholder: string
  initial: string
}>()

const emit = defineEmits<{ cancel: []; submit: [value: string] }>()
const text = ref(props.initial)
const error = ref("")

watch(() => props.initial, (value) => {
  text.value = value
  error.value = ""
})

function onEscape(event: KeyboardEvent) {
  if (event.key !== "Escape") return
  event.preventDefault()
  emit("cancel")
}

onMounted(() => window.addEventListener("keydown", onEscape))
onBeforeUnmount(() => window.removeEventListener("keydown", onEscape))

function apply() {
  if (!text.value.trim()) {
    error.value = "This field must not be empty"
    return
  }
  emit("submit", text.value.trim())
}
</script>

<template>
  <div class="modal-backdrop" @pointerdown.self="emit('cancel')">
    <form class="modal-card" @submit.prevent="apply">
      <h2 style="margin: 0 0 12px; font-size: 14px;">{{ title }}</h2>
      <label>
        <div style="margin-bottom: 8px;">{{ label }}</div>
        <textarea v-model="text" class="field" rows="4" :placeholder="placeholder" style="width: 100%; resize: vertical;" />
      </label>
      <div class="form-error">{{ error }}</div>
      <div class="dialog-actions">
        <button type="button" @click="emit('cancel')">Cancel</button>
        <button type="submit">Apply</button>
      </div>
    </form>
  </div>
</template>
