<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"

const store = useAppStore()
const password = ref("")
const showPassword = ref(false)
const error = ref("")
const busy = ref(false)

function onEscape(event: KeyboardEvent) {
  if (event.key !== "Escape" || !store.relogin) return
  event.preventDefault()
  store.cancelRelogin()
}

onMounted(() => window.addEventListener("keydown", onEscape))
onBeforeUnmount(() => window.removeEventListener("keydown", onEscape))

async function submit() {
  error.value = ""
  if (!password.value) {
    error.value = "Password must not be empty"
    return
  }
  busy.value = true
  try {
    await store.submitRelogin(password.value)
    password.value = ""
  } catch (cause) {
    error.value = errorText(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div v-if="store.relogin" class="modal-backdrop">
    <form class="modal-card" @submit.prevent="submit">
      <h2 style="margin: 0 0 12px; font-size: 14px;">Session expired</h2>
      <p style="margin: 0 0 12px;">
        Sign in again as {{ store.relogin.username }} ({{ store.relogin.domain }}).
      </p>
      <label class="form-row">
        <span>Password:</span>
        <span class="password-wrap">
          <input v-model="password" class="field" :type="showPassword ? 'text' : 'password'" placeholder="Password..." />
          <button class="icon-button eye" type="button" @click="showPassword = !showPassword">
            <img :src="showPassword ? '/icons/opened_eye_icon.png' : '/icons/closed_eye_icon.png'" width="18" height="18" alt="" />
          </button>
        </span>
      </label>
      <div class="form-error">{{ error }}</div>
      <div class="dialog-actions">
        <button type="button" @click="store.cancelRelogin()">Log out</button>
        <button class="accent-button" type="submit" :disabled="busy">Login</button>
      </div>
    </form>
  </div>
</template>
