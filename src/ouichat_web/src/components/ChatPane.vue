<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue"
import { errorText } from "../api/http"
import { formatDay, formatTime } from "../format"
import { useAppStore, type ChatMessage } from "../stores/app"
import AttachmentName from "./AttachmentName.vue"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"

const store = useAppStore()
const scroller = ref<HTMLElement | null>(null)
const menu = ref<{ x: number; y: number; message: ChatMessage } | null>(null)
const stick = ref(true)

const thread = computed(() => {
  const chat = store.selectedChat
  if (!chat) return null
  return store.threadFor(chat.domain, chat.id)
})

const transcript = computed(() => {
  const rows: Array<{ kind: "day"; id: string; label: string } | { kind: "message"; id: string; message: ChatMessage }> = []
  let previousDay = ""
  for (const message of thread.value?.items ?? []) {
    const label = formatDay(message.createdAt)
    if (label !== previousDay) {
      rows.push({ kind: "day", id: `day-${message.id}`, label })
      previousDay = label
    }
    rows.push({ kind: "message", id: message.id, message })
  }
  return rows
})

const menuItems = computed(() => {
  const message = menu.value?.message
  const me = store.current
  const chat = store.selectedChat
  if (!message || !me || !chat) return []
  const items: { id: string; label: string }[] = []
  if (store.isWritable(chat)) items.push({ id: "reply", label: "Reply" })
  const sender = message.sender === me.username
  const admin = store.isAdmin(chat, me.username)
  if (admin || sender) items.push({ id: "delete", label: "Delete Message" })
  if (sender) items.push({ id: "edit", label: "Edit Message" })
  return items
})

function openMenu(event: MouseEvent, message: ChatMessage) {
  const chat = store.selectedChat
  if (!chat || !store.isWritable(chat)) return
  menu.value = { x: event.clientX, y: event.clientY, message }
}

function quote(message: ChatMessage): string | null {
  if (!message.repliedTo || !thread.value) return null
  const original = thread.value.items.find((entry) => entry.id === message.repliedTo)
  if (!original) return "Unknown User: Unknown Message"
  const snip = original.content || "Attachment"
  return `${original.sender}: ${snip}`
}

function picture(username: string): string | null {
  const chat = store.selectedChat
  if (!chat) return null
  return store.userByName(chat.domain, username)?.pictureId ?? null
}

async function onScroll() {
  const element = scroller.value
  const chat = store.selectedChat
  if (!element || !chat) return
  stick.value = element.scrollHeight - element.scrollTop - element.clientHeight < 80
  if (element.scrollTop > 40) return
  const before = element.scrollHeight
  await store.loadOlder()
  await nextTick()
  element.scrollTop = element.scrollHeight - before + element.scrollTop
}

watch(() => store.selectedChat?.id, async () => {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  stick.value = true
})

watch(() => thread.value?.items.at(-1)?.id, async () => {
  if (!stick.value) return
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
})

async function pick(action: string) {
  const message = menu.value?.message
  menu.value = null
  if (!message) return
  if (action === "reply" || action === "edit") {
    window.dispatchEvent(new CustomEvent("ouichat-compose", {
      detail: {
        mode: action,
        messageId: message.id,
        sender: message.sender,
        snip: message.content || "Attachment",
      },
    }))
    return
  }
  try {
    await store.deleteChatMessage(message.id)
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div v-if="store.selectedChat" class="pane">
    <div class="pane-toolbar">
      <button class="pane-back" type="button" title="Back" @click="store.showUsers()">
        <img src="/icons/left_arrow_icon.png" width="18" height="18" alt="" />
      </button>
      <button class="chat-title" type="button" @click="store.showDetails()">
        <Avatar
          :domain="store.selectedChat.domain"
          :picture-id="store.chatPicture(store.selectedChat).pictureId"
          :fallback="store.chatPicture(store.selectedChat).fallback"
          :size="26"
        />
        <span class="row-label">{{ store.displayName(store.selectedChat) }}</span>
      </button>
    </div>
    <div ref="scroller" class="messages" @scroll="onScroll">
      <template v-for="row in transcript" :key="row.id">
      <div v-if="row.kind === 'day'" class="day-separator">{{ row.label }}</div>
      <article
        v-else
        class="message"
        @contextmenu.prevent="openMenu($event, row.message)"
      >
        <Avatar :domain="row.message.domain" :picture-id="picture(row.message.sender)" fallback="/icons/default_user_icon.png" />
        <div class="message-body">
          <div class="message-meta">
            <span class="message-author">{{ row.message.sender }}</span>
            <span class="message-time">{{ formatTime(row.message.createdAt) }}</span>
            <span v-if="row.message.edited" class="edited">edited</span>
          </div>
          <div v-if="quote(row.message)" class="reply-quote">{{ quote(row.message) }}</div>
          <p v-if="row.message.content" class="message-text">{{ row.message.content }}</p>
          <div v-if="row.message.attachments.length" class="file-stack">
            <button
              v-for="fileId in row.message.attachments"
              :key="fileId"
              class="file-chip"
              type="button"
              @click="store.downloadAttachment(fileId).catch((cause) => store.error = errorText(cause))"
            >
              <img src="/icons/download_file_icon.png" width="22" height="22" alt="" />
              <AttachmentName :domain="row.message.domain" :file-id="fileId" />
            </button>
          </div>
        </div>
      </article>
      </template>
    </div>
    <ContextMenu v-if="menu" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
  </div>
</template>
