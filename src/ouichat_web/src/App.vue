<script setup lang="ts">
import { watch } from "vue"
import { RouterView, useRoute, useRouter } from "vue-router"
import ErrorDialog from "./components/ErrorDialog.vue"
import ReloginDialog from "./components/ReloginDialog.vue"
import { useAppStore } from "./stores/app"

const store = useAppStore()
const route = useRoute()
const router = useRouter()

watch(() => store.sessions.length, (count, previous) => {
  if (!store.ready || previous === undefined) return
  if (count === 0 && route.name !== "login") void router.replace("/")
  else if (count < previous && (route.name === "profile" || route.name === "settings")) void router.replace("/app")
})
</script>

<template>
  <RouterView />
  <ErrorDialog />
  <ReloginDialog />
</template>
