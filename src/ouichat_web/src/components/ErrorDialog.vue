<script setup lang="ts">
import { useAppStore } from "../stores/app"

const store = useAppStore()
</script>

<template>
  <div v-if="store.error" class="modal-backdrop" @click.self="store.error = null">
    <div class="modal-card">
      <p style="margin: 0 0 16px; white-space: pre-wrap;">{{ store.error }}</p>
      <div class="dialog-actions">
        <button type="button" @click="store.error = null">Close</button>
      </div>
    </div>
  </div>
</template>
