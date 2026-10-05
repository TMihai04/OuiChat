<script setup lang="ts">
import { computed, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"
import TextPrompt from "./TextPrompt.vue"

const emit = defineEmits<{ add: []; remove: [] }>()
const store = useAppStore()
const memberQuery = ref("")
const menu = ref<{ x: number; y: number; username: string } | null>(null)
const prompt = ref<null | { field: "name" | "description"; title: string; label: string; placeholder: string; initial: string }>(null)
const iconInput = ref<HTMLInputElement | null>(null)

const chat = computed(() => store.selectedChat)
const me = computed(() => store.current)
const admin = computed(() => chat.value && me.value ? store.isAdmin(chat.value, me.value.username) : false)
const group = computed(() => chat.value?.type === "group")

const members = computed(() => {
  if (!chat.value) return []
  const text = memberQuery.value.trim().toLowerCase()
  return chat.value.participants
    .filter((participant) => participant.username.toLowerCase().includes(text))
    .slice()
    .sort((left, right) => left.username.localeCompare(right.username))
})

const menuItems = computed(() => {
  const username = menu.value?.username
  const currentChat = chat.value
  const user = me.value
  if (!username || !currentChat || !user || !store.isAdmin(currentChat, user.username)) return []
  if (username === user.username) return []
  if (store.isCreator(currentChat, username)) return []
  const targetAdmin = store.isAdmin(currentChat, username)
  if (targetAdmin && !store.isCreator(currentChat, user.username)) return []
  return [{ id: targetAdmin ? "demote" : "promote", label: targetAdmin ? "Remove Admin" : "Make Admin" }]
})

function memberPicture(username: string): string | null {
  if (!chat.value) return null
  return store.userByName(chat.value.domain, username)?.pictureId ?? null
}

async function pick(action: string) {
  const username = menu.value?.username
  const currentChat = chat.value
  menu.value = null
  if (!username || !currentChat) return
  try {
    await store.setAdmin(currentChat.id, username, action === "promote")
  } catch (cause) {
    store.error = errorText(cause)
  }
}

function openPrompt(field: "name" | "description") {
  if (!chat.value) return
  prompt.value = field === "name"
    ? {
      field,
      title: "Change Chat Name",
      label: "Change Chat Name:",
      placeholder: "Type chat name...",
      initial: store.displayName(chat.value),
    }
    : {
      field,
      title: "Change Chat Description",
      label: "Change Chat Description:",
      placeholder: "Type chat description...",
      initial: store.displayDescription(chat.value),
    }
}

async function applyPrompt(value: string) {
  if (!chat.value || !prompt.value) return
  const field = prompt.value.field
  prompt.value = null
  try {
    if (field === "name") await store.renameChat(chat.value.id, value)
    else await store.describeChat(chat.value.id, value)
  } catch (cause) {
    store.error = errorText(cause)
  }
}

async function leave() {
  if (!chat.value) return
  try {
    await store.leaveChatById(chat.value.id)
  } catch (cause) {
    store.error = errorText(cause)
  }
}

async function changeIcon(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ""
  if (!file || !chat.value) return
  try {
    await store.changeChatIcon(chat.value.id, file)
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div v-if="chat" class="pane details">
    <div class="details-close">
      <button class="surface-button" type="button" @click="store.showChat()">
        <img src="/icons/close_icon.png" width="20" height="20" alt="" />
      </button>
    </div>
    <div class="center-col">
      <div class="icon-slot">
        <Avatar
          :domain="chat.domain"
          :picture-id="store.chatPicture(chat).pictureId"
          :fallback="store.chatPicture(chat).fallback"
          :size="64"
        />
        <button v-if="group && admin" class="surface-button edit-button" type="button" title="Change icon" @click="iconInput?.click()">
          <img src="/icons/edit_icon.png" width="14" height="14" alt="" />
        </button>
      </div>
      <div class="name-line">
        <span>{{ store.displayName(chat) }}</span>
        <button v-if="group && admin" class="surface-button edit-button" type="button" @click="openPrompt('name')">
          <img src="/icons/edit_icon.png" width="14" height="14" alt="" />
        </button>
      </div>
    </div>
    <div style="margin-top: 16px;">
      <div class="description-head">
        <span>Description:</span>
        <button v-if="group && admin" class="surface-button edit-button" type="button" @click="openPrompt('description')">
          <img src="/icons/edit_icon.png" width="14" height="14" alt="" />
        </button>
      </div>
      <div class="description-widget">{{ store.displayDescription(chat) }}</div>
    </div>
    <template v-if="group">
      <div style="display: flex; justify-content: flex-end; margin-top: 12px;">
        <label class="search" style="width: 220px;">
          <img src="/icons/search_icon.png" width="14" height="14" alt="" />
          <input v-model="memberQuery" placeholder="Search member..." />
        </label>
      </div>
      <div class="list-panel" style="margin-top: 8px; max-height: 280px;">
        <button
          v-for="member in members"
          :key="member.username"
          class="row"
          type="button"
          @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, username: member.username }"
        >
          <Avatar :domain="chat.domain" :picture-id="memberPicture(member.username)" fallback="/icons/default_user_icon.png" />
          <span class="row-label">{{ member.username }}<template v-if="member.isAdmin"> (Admin)</template></span>
        </button>
      </div>
      <div v-if="admin" class="member-tools">
        <button class="mid-button" type="button" @click="emit('add')">
          <img src="/icons/plus_icon.png" width="12" height="12" alt="" /> Add members
        </button>
        <button class="mid-button" type="button" @click="emit('remove')">
          <img src="/icons/minus_icon.png" width="12" height="12" alt="" /> Remove members
        </button>
      </div>
      <div class="leave-row">
        <button class="mid-button" type="button" @click="leave">Leave Chat</button>
      </div>
    </template>
    <input ref="iconInput" hidden type="file" accept="image/png,image/jpeg" @change="changeIcon" />
    <ContextMenu v-if="menu && menuItems.length" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
    <TextPrompt
      v-if="prompt"
      :title="prompt.title"
      :label="prompt.label"
      :placeholder="prompt.placeholder"
      :initial="prompt.initial"
      @cancel="prompt = null"
      @submit="applyPrompt"
    />
  </div>
</template>
