<script setup lang="ts">
import { useRouter } from "vue-router"

const router = useRouter()
</script>

<template>
  <div class="settings-page">
    <div>
      <button type="button" style="width: 70px; height: 30px;" @click="router.push('/app')">Close</button>
    </div>
    <div class="settings-label">SETTINGS SCREEN</div>
  </div>
</template>
