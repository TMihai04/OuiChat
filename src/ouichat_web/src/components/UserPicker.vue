<script setup lang="ts">
import { computed, ref } from "vue"
import type { DirUser } from "../stores/app"
import Avatar from "./Avatar.vue"

const props = defineProps<{
  title: string
  confirmLabel: string
  domain: string
  candidates: DirUser[]
  allowEmpty?: boolean
}>()

const emit = defineEmits<{ cancel: []; confirm: [usernames: string[]] }>()
const leftQuery = ref("")
const rightQuery = ref("")
const selected = ref<string[]>([])

const left = computed(() => props.candidates.filter((user) => {
  return user.username.toLowerCase().includes(leftQuery.value.trim().toLowerCase())
}))

const right = computed(() => props.candidates
  .filter((user) => selected.value.includes(user.username))
  .filter((user) => user.username.toLowerCase().includes(rightQuery.value.trim().toLowerCase())))

function userOf(username: string): DirUser {
  return props.candidates.find((user) => user.username === username) ?? {
    username,
    status: "",
    pictureId: null,
  }
}

function toggle(username: string, on: boolean) {
  if (on) {
    if (!selected.value.includes(username)) selected.value.push(username)
  } else {
    selected.value = selected.value.filter((name) => name !== username)
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('cancel')">
    <div class="picker">
      <div class="picker-columns">
        <section>
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong style="white-space: nowrap;">{{ title }}:</strong>
            <label class="search" style="flex: 1;">
              <img src="/icons/search_icon.png" width="14" height="14" alt="" />
              <input v-model="leftQuery" placeholder="Search user..." />
            </label>
          </div>
          <div class="picker-list">
            <label v-for="user in left" :key="user.username" class="row">
              <input type="checkbox" :checked="selected.includes(user.username)" @change="toggle(user.username, ($event.target as HTMLInputElement).checked)" />
              <Avatar :domain="domain" :picture-id="user.pictureId" fallback="/icons/default_user_icon.png" />
              <span class="row-label">{{ user.username }}</span>
            </label>
          </div>
        </section>
        <section>
          <div style="display: flex; align-items: center; gap: 8px;">
            <strong style="white-space: nowrap;">Selected Users:</strong>
            <label class="search" style="flex: 1;">
              <img src="/icons/search_icon.png" width="14" height="14" alt="" />
              <input v-model="rightQuery" placeholder="Search user..." />
            </label>
          </div>
          <div class="picker-list">
            <button v-for="username in right.map((user) => user.username)" :key="username" class="row" type="button" @click="toggle(username, false)">
              <Avatar :domain="domain" :picture-id="userOf(username).pictureId" fallback="/icons/default_user_icon.png" />
              <span class="row-label">{{ username }}</span>
            </button>
          </div>
        </section>
      </div>
      <div class="dialog-actions">
        <button type="button" @click="emit('cancel')">Cancel</button>
        <button type="button" :disabled="!allowEmpty && selected.length === 0" @click="emit('confirm', selected.slice())">{{ confirmLabel }}</button>
      </div>
    </div>
  </div>
</template>
