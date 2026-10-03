<script setup lang="ts">
import { computed, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"

const store = useAppStore()
const query = ref("")
const menu = ref<{ x: number; y: number; chatId: string } | null>(null)

const chats = computed(() => {
  const text = query.value.trim().toLowerCase()
  return store.visibleChats.filter((chat) => store.displayName(chat).toLowerCase().includes(text))
})

const menuItems = computed(() => {
  const chat = store.visibleChats.find((entry) => entry.id === menu.value?.chatId)
  const me = store.current
  if (!chat || !me) return []
  const items = [{ id: "read", label: "Mark as Read" }]
  if (chat.type === "direct") {
    const other = chat.participants.find((participant) => participant.username !== me.username)?.username
    if (other) {
      const blocked = me.blacklist.includes(other)
      items.push({ id: blocked ? "unblock" : "block", label: blocked ? "Unblock User" : "Block User" })
    }
  } else {
    items.push({ id: "exit", label: "Exit Chat" })
    if (store.isAdmin(chat, me.username)) items.push({ id: "delete", label: "Delete Chat" })
  }
  return items
})

async function pick(action: string) {
  const chat = store.visibleChats.find((entry) => entry.id === menu.value?.chatId)
  const me = store.current
  menu.value = null
  if (!chat || !me) return
  try {
    if (action === "read") {
      await store.selectChat(chat.id)
      store.markSelectedRead()
      return
    }
    if (action === "block" || action === "unblock") {
      const other = chat.participants.find((participant) => participant.username !== me.username)?.username
      if (other) await store.blockUser(other, action === "block")
      return
    }
    if (action === "exit" || action === "delete") {
      await store.leaveChatById(chat.id)
    }
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <label class="search">
    <img src="/icons/search_icon.png" width="14" height="14" alt="" />
    <input v-model="query" placeholder="Search chat..." />
  </label>
  <div class="list-panel">
    <button
      v-for="chat in chats"
      :key="chat.id"
      class="row"
      :class="{ selected: store.selectedChat?.id === chat.id }"
      type="button"
      @click="store.selectChat(chat.id)"
      @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, chatId: chat.id }"
    >
      <span class="badge-wrap">
        <Avatar :domain="chat.domain" :picture-id="store.chatPicture(chat).pictureId" :fallback="store.chatPicture(chat).fallback" />
        <img v-if="store.unread(chat)" class="badge" src="/icons/new_messages_icon.png" alt="" />
      </span>
      <span class="row-label">{{ store.displayName(chat) }}</span>
    </button>
  </div>
  <ContextMenu v-if="menu" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
</template>
