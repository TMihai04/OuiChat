import { createRouter, createWebHistory } from "vue-router"
import LoginCard from "../components/LoginCard.vue"
import MainScreen from "../components/MainScreen.vue"
import ProfileScreen from "../components/ProfileScreen.vue"
import SettingsScreen from "../components/SettingsScreen.vue"
import { useAppStore } from "../stores/app"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "login", component: LoginCard },
    { path: "/app", name: "main", component: MainScreen },
    { path: "/profile", name: "profile", component: ProfileScreen },
    { path: "/settings", name: "settings", component: SettingsScreen },
    {
      path: "/index.html",
      redirect: () => {
        const store = useAppStore()
        return store.current !== null ? "/app" : "/"
      },
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: () => {
        const store = useAppStore()
        return store.current !== null ? "/app" : "/"
      },
    },
  ],
})

router.beforeEach(async (to) => {
  const store = useAppStore()
  if (!store.ready) {
    await store.waitForReady()
  }
  const signedIn = store.current !== null
  if (!signedIn && to.name !== "login") return { name: "login" }
  if (signedIn && (to.name === "login" || !to.name || to.path === "/index.html")) return { name: "main" }
  return true
})

export default router
