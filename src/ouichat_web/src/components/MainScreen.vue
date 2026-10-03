<script setup lang="ts">
import { computed, ref } from "vue"
import { useRouter } from "vue-router"
import { errorText } from "../api/http"
import { MAX_SESSIONS, useAppStore } from "../stores/app"
import Avatar from "./Avatar.vue"
import ChatList from "./ChatList.vue"
import ChatPane from "./ChatPane.vue"
import Composer from "./Composer.vue"
import DetailsPane from "./DetailsPane.vue"
import LoginCard from "./LoginCard.vue"
import UserPicker from "./UserPicker.vue"
import UsersPane from "./UsersPane.vue"

const store = useAppStore()
const router = useRouter()
const accountOpen = ref(false)
const addingAccount = ref(false)
const picker = ref<null | "create" | "add" | "remove">(null)

const candidates = computed(() => {
  if (picker.value === "remove" && store.selectedChat) return store.removableMembers(store.selectedChat)
  if (picker.value === "add") return store.pickerCandidates(store.selectedChat)
  return store.pickerCandidates(null)
})

const pickerTitle = computed(() => picker.value === "remove" ? "Remove Users" : "Add Users")
const pickerConfirm = computed(() => picker.value === "remove" ? "Remove Users" : picker.value === "create" ? "Create Chat" : "Add Users")

async function chooseAccount(username: string, domain: string) {
  accountOpen.value = false
  if (store.current?.username === username && store.current.domain === domain) return
  await store.switchTo(username, domain)
}

async function confirmPicker(usernames: string[]) {
  const mode = picker.value
  const chatId = store.selectedChat?.id
  picker.value = null
  try {
    if (mode === "create") await store.createGroup(usernames)
    else if (mode === "add" && chatId) await store.addMembers(chatId, usernames)
    else if (mode === "remove" && chatId) await store.removeMembers(chatId, usernames)
  } catch (cause) {
    store.error = errorText(cause)
  }
}
</script>

<template>
  <div class="shell">
    <aside class="left">
      <ChatList />
      <button class="wide-button" type="button" @click="picker = 'create'">
        <img src="/icons/plus_icon.png" width="12" height="12" alt="" /> New Chat
      </button>
      <div class="account-bar">
        <button class="account-button" type="button" @click="accountOpen = !accountOpen">
          <Avatar
            v-if="store.current"
            :domain="store.current.domain"
            :picture-id="store.current.pictureId"
            fallback="/icons/default_user_icon.png"
          />
          <span class="row-label">{{ store.current?.username }} ({{ store.current?.domain }})</span>
        </button>
        <button class="square" type="button" title="Profile" @click="router.push('/profile')">
          <img src="/icons/user_settings_icon.png" width="22" height="22" alt="" />
        </button>
        <button class="square" type="button" title="Settings" @click="router.push('/settings')">
          <img src="/icons/settings_icon.png" width="22" height="22" alt="" />
        </button>
      </div>
      <div v-if="accountOpen" class="account-menu" style="left: 18px; bottom: 62px; width: 220px; z-index: 50;">
        <button
          v-for="session in store.sessions"
          :key="session.username + session.domain"
          type="button"
          @click="chooseAccount(session.username, session.domain)"
        >
          <Avatar :domain="session.domain" :picture-id="session.pictureId" fallback="/icons/default_user_icon.png" :size="24" />
          <span class="row-label">{{ session.username }} ({{ session.domain }})</span>
        </button>
        <button type="button" :disabled="store.sessions.length >= MAX_SESSIONS" @click="accountOpen = false; addingAccount = true">
          <img src="/icons/plus_icon.png" width="14" height="14" alt="" />
          Add User
        </button>
      </div>
    </aside>
    <section class="right">
      <UsersPane v-if="store.pane === 'users'" />
      <ChatPane v-else-if="store.pane === 'chat'" />
      <DetailsPane v-else @add="picker = 'add'" @remove="picker = 'remove'" />
      <Composer />
    </section>
    <div v-if="addingAccount" class="modal-backdrop">
      <LoginCard modal @close="addingAccount = false" />
    </div>
    <div v-if="accountOpen" class="modal-backdrop" style="background: transparent; z-index: 20;" @click="accountOpen = false" />
    <UserPicker
      v-if="picker && store.current"
      :title="pickerTitle"
      :confirm-label="pickerConfirm"
      :domain="store.current.domain"
      :candidates="candidates"
      :allow-empty="picker === 'create'"
      @cancel="picker = null"
      @confirm="confirmPicker"
    />
  </div>
</template>
