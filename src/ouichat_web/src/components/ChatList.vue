<script setup lang="ts">
import { computed, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"

const store = useAppStore()
const dmQuery = ref("")
const roomQuery = ref("")
const menu = ref<{ x: number; y: number; chatId: string } | null>(null)

function matching(type: "direct" | "group", query: string) {
  const text = query.trim().toLowerCase()
  return store.visibleChats.filter((chat) => chat.type === type && store.displayName(chat).toLowerCase().includes(text))
}

const directChats = computed(() => matching("direct", dmQuery.value))
const groupChats = computed(() => matching("group", roomQuery.value))

function dmPresence(chat: { type: string; domain: string; participants: { username: string }[] }) {
  const me = store.current
  if (!me || chat.type !== "direct") return null
  const other = chat.participants.find((participant) => participant.username !== me.username)
  if (!other) return null
  return store.presenceOf(chat.domain, other.username)
}

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
    if (action === "exit") {
      await store.leaveChatById(chat.id)
      return
    }
    if (action === "delete") {
      await store.deleteChatById(chat.id)
    }
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div class="chat-lists">
    <section class="list-block">
      <h2 class="list-title">DMs</h2>
      <button class="home-wide" type="button" title="Home" @click="store.showUsers()">
        <img src="/icons/home.png" width="18" height="18" alt="" />
      </button>
      <label class="search">
        <img src="/icons/search_icon.png" width="14" height="14" alt="" />
        <input v-model="dmQuery" placeholder="Search DM..." />
      </label>
      <div class="list-panel">
        <button
          v-for="chat in directChats"
          :key="chat.id"
          class="row"
          :class="{ selected: store.selectedChat?.id === chat.id, unread: store.unread(chat) }"
          type="button"
          @click="store.selectChat(chat.id)"
          @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, chatId: chat.id }"
        >
          <Avatar
            :domain="chat.domain"
            :picture-id="store.chatPicture(chat).pictureId"
            :fallback="store.chatPicture(chat).fallback"
            :presence="dmPresence(chat)"
          />
          <span class="row-label">{{ store.displayName(chat) }}</span>
        </button>
      </div>
    </section>
    <section class="list-block">
      <h2 class="list-title">Chatrooms</h2>
      <label class="search">
        <img src="/icons/search_icon.png" width="14" height="14" alt="" />
        <input v-model="roomQuery" placeholder="Search chatroom..." />
      </label>
      <div class="list-panel">
        <button
          v-for="chat in groupChats"
          :key="chat.id"
          class="row"
          :class="{ selected: store.selectedChat?.id === chat.id, unread: store.unread(chat) }"
          type="button"
          @click="store.selectChat(chat.id)"
          @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, chatId: chat.id }"
        >
          <Avatar :domain="chat.domain" :picture-id="store.chatPicture(chat).pictureId" :fallback="store.chatPicture(chat).fallback" />
          <span class="row-label">{{ store.displayName(chat) }}</span>
        </button>
      </div>
    </section>
  </div>
  <ContextMenu v-if="menu" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
</template>
