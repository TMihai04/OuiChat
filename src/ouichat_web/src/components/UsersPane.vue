<script setup lang="ts">
import { computed, ref } from "vue"
import { errorText } from "../api/http"
import { useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ContextMenu from "./ContextMenu.vue"

const store = useAppStore()
const query = ref("")
const menu = ref<{ x: number; y: number; username: string } | null>(null)

const users = computed(() => {
  const text = query.value.trim().toLowerCase()
  return store.directory.filter((user) => user.username.toLowerCase().includes(text))
})

const menuItems = computed(() => {
  const me = store.current
  const username = menu.value?.username
  if (!me || !username) return []
  const blocked = me.blacklist.includes(username)
  return [{ id: blocked ? "unblock" : "block", label: blocked ? "Unblock User" : "Block User" }]
})

async function pick(action: string) {
  const username = menu.value?.username
  menu.value = null
  if (!username) return
  try {
    await store.blockUser(username, action === "block")
  } catch (cause) {
    store.error = errorText(cause)
  }
}

async function openUser(username: string) {
  try {
    await store.openDirect(username)
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div class="pane">
    <div class="pane-toolbar">
      <label class="search" style="flex: 1;">
        <img src="/icons/search_icon.png" width="14" height="14" alt="" />
        <input v-model="query" placeholder="Search user..." />
      </label>
    </div>
    <div class="messages">
      <button
        v-for="user in users"
        :key="user.username"
        class="row"
        type="button"
        @click="openUser(user.username)"
        @contextmenu.prevent="menu = { x: $event.clientX, y: $event.clientY, username: user.username }"
      >
        <Avatar :domain="store.current?.domain ?? ''" :picture-id="user.pictureId" fallback="/icons/default_user_icon.png" />
        <span class="row-label">{{ user.username }}</span>
      </button>
    </div>
    <ContextMenu v-if="menu" :x="menu.x" :y="menu.y" :items="menuItems" @close="menu = null" @pick="pick" />
  </div>
</template>
