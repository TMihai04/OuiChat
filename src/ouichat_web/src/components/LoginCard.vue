<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import { validatePassword, validateUsername } from "../validate"

const props = defineProps<{ modal?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const store = useAppStore()
const router = useRouter()

const domain = ref("")
const username = ref("")
const password = ref("")
const register = ref(false)
const showPassword = ref(false)
const error = ref("")
const busy = ref(false)

async function submit() {
  error.value = ""
  if (!domain.value.trim()) {
    error.value = "Domain must not be empty"
    return
  }
  if (!username.value.trim()) {
    error.value = "Username must not be empty"
    return
  }
  if (!password.value) {
    error.value = "Password must not be empty"
    return
  }
  if (register.value) {
    error.value = validateUsername(username.value.trim()) ?? validatePassword(password.value) ?? ""
    if (error.value) return
  }
  busy.value = true
  try {
    await store.signIn(domain.value, username.value, password.value, register.value)
    if (props.modal) emit("close")
    else await router.push("/app")
  } catch (cause) {
    error.value = errorText(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="dialog-card" @submit.prevent="submit">
    <h1 style="text-align: center; font-size: 14px; font-weight: 600; margin: 0 0 16px;">Insert domain and credentials</h1>
    <label class="form-row">
      <span>Domain:</span>
      <input v-model="domain" class="field" placeholder="Domain..." autocomplete="off" />
    </label>
    <label class="form-row">
      <span>Username:</span>
      <input v-model="username" class="field" placeholder="Username..." autocomplete="username" />
    </label>
    <label class="form-row">
      <span>Password:</span>
      <span class="password-wrap">
        <input v-model="password" class="field" :type="showPassword ? 'text' : 'password'" placeholder="Password..." autocomplete="current-password" />
        <button class="icon-button eye" type="button" @click="showPassword = !showPassword">
          <img :src="showPassword ? '/icons/opened_eye_icon.png' : '/icons/closed_eye_icon.png'" width="18" height="18" alt="" />
        </button>
      </span>
    </label>
    <label class="check-row">
      <input v-model="register" type="checkbox" />
      <span>Register and Login</span>
    </label>
    <div class="form-error">{{ error }}</div>
    <div class="form-actions">
      <button v-if="modal" type="button" @click="emit('close')">Cancel</button>
      <button type="submit" :disabled="busy">Login</button>
    </div>
  </form>
</template>
