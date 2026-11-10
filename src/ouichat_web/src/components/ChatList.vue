<script setup lang="ts">
import { computed, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"
import { getNotificationPermission, isNotificationSupported, requestNotificationPermission } from "../notifications"

const notifDismissed = ref(typeof localStorage !== "undefined" && localStorage.getItem("ouichat.notif_dismissed") === "true")
const notifPermission = ref(getNotificationPermission())

const showNotifBanner = computed(() => {
  return isNotificationSupported() && notifPermission.value === "default" && !notifDismissed.value
})

async function enableNotifs() {
  const perm = await requestNotificationPermission()
  notifPermission.value = perm
}

function dismissNotifBanner() {
  notifDismissed.value = true
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("ouichat.notif_dismissed", "true")
  }
}

const store = useAppStore()
const dmQuery = ref("")
const roomQuery = ref("")
const userQuery = ref("")
const menu = ref<{ x: number; y: number; chatId?: string; username?: string } | null>(null)

function matching(type: "direct" | "group", query: string) {
  const text = query.trim().toLowerCase()
  return store.visibleChats.filter((chat) => chat.type === type && store.displayName(chat).toLowerCase().includes(text))
}

const directChats = computed(() => matching("direct", dmQuery.value))
const groupChats = computed(() => matching("group", roomQuery.value))

const users = computed(() => {
  const text = userQuery.value.trim().toLowerCase()
  return store.directory.filter((user) => user.username.toLowerCase().includes(text))
})

function dmPresence(chat: { type: string; domain: string; participants: { username: string }[] }) {
  const me = store.current
  if (!me || chat.type !== "direct") return null
  const other = chat.participants.find((participant) => participant.username !== me.username)
  if (!other) return null
  return store.presenceOf(chat.domain, other.username)
}

const menuItems = computed(() => {
  const me = store.current
  const target = menu.value
  if (!me || !target) return []

  if (target.chatId) {
    const chat = store.visibleChats.find((entry) => entry.id === target.chatId)
    if (!chat) return []
    const items = [{ id: "read", label: "Mark as Read" }]
    const isMuted = store.isMuted(chat.id)
    items.push({ id: isMuted ? "unmute" : "mute", label: isMuted ? "Unmute" : "Mute" })
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
  }

  if (target.username) {
    const blocked = me.blacklist.includes(target.username)
    return [{ id: blocked ? "unblock" : "block", label: blocked ? "Unblock User" : "Block User" }]
  }

  return []
})

async function openUser(username: string) {
  try {
    await store.openDirect(username)
  } catch (cause) {
    store.error = errorText(cause)
  }
}

async function pick(action: string) {
  const me = store.current
  const target = menu.value
  menu.value = null
  if (!target || !me) return
  try {
    if (target.chatId) {
      const chat = store.visibleChats.find((entry) => entry.id === target.chatId)
      if (!chat) return
      if (action === "read") {
        await store.selectChat(chat.id)
        store.markSelectedRead()
        return
      }
      if (action === "mute" || action === "unmute") {
        await store.toggleMuteChat(chat.id)
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
        return
      }
    }
    if (target.username) {
      if (action === "block" || action === "unblock") {
        await store.blockUser(target.username, action === "block")
      }
    }
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div class="chat-lists">
    <div class="selection-bar">
      <button
        type="button"
        class="selection-tab"
        :class="{ active: store.sidebarTab === 'chats' }"
        @click="store.sidebarTab = 'chats'"
      >
        Chats
      </button>
      <button
        type="button"
        class="selection-tab"
        :class="{ active: store.sidebarTab === 'users' }"
        @click="store.sidebarTab = 'users'"
      >
        Users
      </button>
    </div>

    <div v-if="showNotifBanner" class="notif-banner">
      <div class="notif-banner-text">
        <strong>Desktop Notifications</strong>
        <span>Get alerted for new messages</span>
      </div>
      <button type="button" class="notif-banner-btn" @click="enableNotifs">Enable</button>
      <button type="button" class="notif-banner-close" title="Dismiss" @click="dismissNotifBanner">✕</button>
    </div>

    <!-- Chats Tab -->
    <template v-if="store.sidebarTab === 'chats'">
      <section class="list-block">
        <h2 class="list-title">DMs</h2>
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
            <span class="badge-wrap">
              <Avatar
                :domain="chat.domain"
                :picture-id="store.chatPicture(chat).pictureId"
                :fallback="store.chatPicture(chat).fallback"
                :presence="dmPresence(chat)"
              />
            </span>
            <span class="row-label">{{ store.displayName(chat) }}</span>
            <span v-if="store.isMuted(chat.id)" class="muted-badge" title="Muted">🔕</span>
            <span v-if="store.unreadBadge(chat)" class="unread-pill">
              {{ store.unreadBadge(chat) }}
            </span>
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
            <span class="badge-wrap">
              <Avatar :domain="chat.domain" :picture-id="store.chatPicture(chat).pictureId" :fallback="store.chatPicture(chat).fallback" />
            </span>
            <span class="row-label">{{ store.displayName(chat) }}</span>
            <span v-if="store.isMuted(chat.id)" class="muted-badge" title="Muted">🔕</span>
            <span v-if="store.unreadBadge(chat)" class="unread-pill">
              {{ store.unreadBadge(chat) }}
            </span>
          </button>
        </div>
      </section>
    </template>

    <!-- Users Tab -->
    <template v-else>
      <section class="list-block">
        <h2 class="list-title">All Users</h2>
        <label class="search">
          <img src="/icons/search_icon.png" width="14" height="14" alt="" />
          <input v-model="userQuery" placeholder="Search user..." />
        </label>
        <div class="list-panel">
          <button
            v-for="user in users"
            :key="user.username"
            class="row"
            type="button"
            @click="openUser(user.username)"
            @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, username: user.username }"
          >
            <span class="badge-wrap">
              <Avatar
                :domain="store.current?.domain ?? ''"
                :picture-id="user.pictureId"
                fallback="/icons/default_user_icon.png"
                :presence="store.current ? store.presenceOf(store.current.domain, user.username) : null"
              />
            </span>
            <span class="row-label">{{ user.username }}</span>
          </button>
        </div>
      </section>
    </template>
  </div>
  <ContextMenu v-if="menu" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
</template>
