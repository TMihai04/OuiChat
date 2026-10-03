<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"

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

const writable = computed(() => store.selectedChat ? store.isWritable(store.selectedChat) : false)
const visible = computed(() => store.pane === "chat" && !!store.selectedChat && writable.value)

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

watch(() => store.selectedChat?.id, () => reset())

onMounted(() => window.addEventListener("ouichat-compose", onCompose))
onBeforeUnmount(() => window.removeEventListener("ouichat-compose", onCompose))

function addFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const picked = Array.from(input.files ?? [])
  input.value = ""
  if (mode.value === "edit") return
  const next = [...files.value]
  for (const file of picked) {
    if (next.length >= 5) {
      store.error = "A message can have at most 5 attachments"
      break
    }
    if (!next.some((entry) => entry.name === file.name && entry.size === file.size)) next.push(file)
  }
  files.value = next
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}

async function send() {
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
    store.error = errorText(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form v-if="visible" class="composer" @submit.prevent="send">
    <div v-if="mode" class="context-bar">
      <button class="icon-button" type="button" @click="reset()">
        <img src="/icons/close_icon.png" width="16" height="16" alt="" />
      </button>
      <strong>{{ mode === "edit" ? "Editing:" : "Replying to:" }}</strong>
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
        @keydown="onKeydown"
      />
      <button class="square" type="submit" :disabled="busy" title="Send">
        <img src="/icons/send_message_icon.png" width="22" height="22" alt="" />
      </button>
    </div>
    <input ref="fileInput" type="file" multiple hidden @change="addFiles" />
  </form>
</template>
