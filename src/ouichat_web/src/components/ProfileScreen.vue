<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import TextPrompt from "./TextPrompt.vue"

const store = useAppStore()
const router = useRouter()
const editing = ref(false)
const iconInput = ref<HTMLInputElement | null>(null)

function logout() {
  store.logoutCurrent()
  if (store.current) void router.push("/app")
  else void router.push("/")
}

async function applyStatus(status: string) {
  editing.value = false
  try {
    await store.changeStatus(status)
  } catch (cause) {
    store.error = errorText(cause)
  }
}

async function changeIcon(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ""
  if (!file) return
  try {
    await store.changeOwnIcon(file)
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div v-if="store.current" class="profile-page">
    <div class="profile-close">
      <button class="icon-button" type="button" @click="router.push('/app')">
        <img src="/icons/close_icon.png" width="20" height="20" alt="" />
      </button>
    </div>
    <div class="center-col">
      <Avatar
        :domain="store.current.domain"
        :picture-id="store.current.pictureId"
        fallback="/icons/default_user_icon.png"
        :size="64"
        clickable
        @click="iconInput?.click()"
      />
      <div>{{ store.current.username }}</div>
    </div>
    <div style="margin-top: 18px;">
      <div class="description-head">
        <span>Description:</span>
        <button class="icon-button" type="button" @click="editing = true">
          <img src="/icons/edit_icon.png" width="16" height="16" alt="" />
        </button>
      </div>
      <div class="description-widget">{{ store.current.status }}</div>
    </div>
    <button type="button" style="margin-top: 16px; width: 100px; height: 28px;" @click="logout">Log Out</button>
    <input ref="iconInput" hidden type="file" accept="image/png,image/jpeg" @change="changeIcon" />
    <TextPrompt
      v-if="editing"
      title="Change Description"
      label="Change Description:"
      placeholder="Type a description..."
      :initial="store.current.status"
      @cancel="editing = false"
      @submit="applyStatus"
    />
  </div>
</template>
