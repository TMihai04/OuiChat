<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { ApiError, errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"

const MESSAGE_LIMIT = 512

interface ComposeDetail {
  mode: "reply" | "edit"
  messageId: string
  sender: string
  snip: string
}

const store = useAppStore()
const text = ref("")
const files = ref<File[]>([])
const mode = ref<"reply" | "edit" | null>(null)
const targetId = ref<string | null>(null)
const targetSender = ref("")
const targetSnip = ref("")
const fileInput = ref<HTMLInputElement | null>(null)
const box = ref<HTMLTextAreaElement | null>(null)
const busy = ref(false)
const pausedUntil = ref<Record<string, number>>({})
const now = ref(Date.now())
let pauseTimer = 0

const writable = computed(() => store.selectedChat ? store.isWritable(store.selectedChat) : false)
const visible = computed(() => store.pane === "chat" && !!store.selectedChat && writable.value)
const paused = computed(() => {
  const id = store.selectedChat?.id
  if (!id) return false
  return (pausedUntil.value[id] ?? 0) > now.value
})
const replyPicture = computed(() => {
  const chat = store.selectedChat
  if (!chat || mode.value !== "reply" || !targetSender.value) return null
  return store.userByName(chat.domain, targetSender.value)?.pictureId ?? null
})

function reset() {
  text.value = ""
  files.value = []
  mode.value = null
  targetId.value = null
  targetSender.value = ""
  targetSnip.value = ""
}

function onCompose(event: Event) {
  const detail = (event as CustomEvent<ComposeDetail>).detail
  mode.value = detail.mode
  targetId.value = detail.messageId
  targetSender.value = detail.sender
  targetSnip.value = detail.snip
  if (detail.mode === "edit") {
    text.value = detail.snip === "Attachment" ? "" : detail.snip
    files.value = []
  }
  box.value?.focus()
}

const composerMin = 48
const composerMax = 140

function fitComposer() {
  const element = box.value
  if (!element) return
  element.style.height = "0px"
  const next = Math.min(composerMax, Math.max(composerMin, element.scrollHeight))
  element.style.height = `${next}px`
}

watch(text, () => void nextTick(fitComposer))
watch(visible, () => void nextTick(fitComposer))
watch(() => store.selectedChat?.id, () => reset())

function stage(picked: File[]) {
  if (mode.value === "edit" || picked.length === 0) return
  const same = (left: File, right: File) => left.name === right.name && left.size === right.size
  const incoming: File[] = []
  for (const file of picked) {
    if (files.value.some((entry) => same(entry, file)) || incoming.some((entry) => same(entry, file))) continue
    incoming.push(file)
  }
  if (incoming.length === 0) return
  if (files.value.length + incoming.length > 5) {
    store.error = "A message can have at most 5 attachments"
    return
  }
  files.value = [...files.value, ...incoming]
}

function addFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const picked = Array.from(input.files ?? [])
  input.value = ""
  stage(picked)
}

function onExternalFiles(event: Event) {
  stage((event as CustomEvent<File[]>).detail ?? [])
}

function onDrop(event: DragEvent) {
  stage(Array.from(event.dataTransfer?.files ?? []))
}

function pause(chatId: string) {
  pausedUntil.value = { ...pausedUntil.value, [chatId]: Date.now() + 10_000 }
  now.value = Date.now()
  window.clearInterval(pauseTimer)
  pauseTimer = window.setInterval(() => {
    now.value = Date.now()
    const still = Object.values(pausedUntil.value).some((until) => until > now.value)
    if (!still) window.clearInterval(pauseTimer)
  }, 250)
}

onMounted(() => {
  window.addEventListener("ouichat-compose", onCompose)
  window.addEventListener("ouichat-files", onExternalFiles)
  fitComposer()
})
onBeforeUnmount(() => {
  window.removeEventListener("ouichat-compose", onCompose)
  window.removeEventListener("ouichat-files", onExternalFiles)
  window.clearInterval(pauseTimer)
})

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}

async function send() {
  if (paused.value) return
  if (text.value.length > MESSAGE_LIMIT) {
    store.error = "A message can be at most 512 characters"
    return
  }
  const value = text.value.trim()
  if (!value && files.value.length === 0) return
  if (mode.value === "edit" && !value) {
    store.error = "Message text must not be empty"
    return
  }
  busy.value = true
  try {
    if (mode.value === "edit" && targetId.value) {
      await store.editChatMessage(targetId.value, value)
    } else {
      await store.sendChatMessage(value, files.value, mode.value === "reply" ? targetId.value : null)
    }
    reset()
  } catch (cause) {
    const chatId = store.selectedChat?.id
    if (cause instanceof ApiError && cause.status === 429 && chatId) pause(chatId)
    else store.error = errorText(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form v-if="visible" class="composer" @submit.prevent="send" @dragover.prevent @drop.prevent="onDrop">
    <p v-if="paused" class="pause-note">Sending is paused</p>
    <div v-if="mode" class="context-bar">
      <button class="icon-button" type="button" @click="reset()">
        <img src="/icons/close_icon.png" width="16" height="16" alt="" />
      </button>
      <strong>{{ mode === "edit" ? "Editing" : "Reply to" }}</strong>
      <Avatar
        v-if="mode === 'reply' && store.selectedChat"
        :domain="store.selectedChat.domain"
        :picture-id="replyPicture"
        fallback="/icons/default_user_icon.png"
        :size="20"
      />
      <span class="row-label">{{ targetSender }}: {{ targetSnip }}</span>
    </div>
    <div v-if="files.length" class="staged-row">
      <span v-for="(file, index) in files" :key="`${file.name}-${index}`" class="staged-chip">
        <img src="/icons/file_uploaded_icon.png" width="14" height="14" alt="" />
        <span>{{ file.name }}</span>
        <button class="icon-button" type="button" @click="files.splice(index, 1)">
          <img src="/icons/close_icon.png" width="12" height="12" alt="" />
        </button>
      </span>
    </div>
    <div class="composer-row">
      <button class="square" type="button" :disabled="mode === 'edit'" title="Attach" @click="fileInput?.click()">
        <img src="/icons/upload_file_icon.png" width="22" height="22" alt="" />
      </button>
      <textarea
        ref="box"
        v-model="text"
        placeholder="Start typing..."
        rows="1"
        maxlength="512"
        @keydown="onKeydown"
      />
      <button class="square" type="submit" :disabled="busy || paused" title="Send">
        <img src="/icons/send_message_icon.png" width="22" height="22" alt="" />
      </button>
    </div>
    <input ref="fileInput" type="file" multiple hidden @change="addFiles" />
  </form>
</template>
