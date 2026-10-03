import { createApp } from "vue"
import { createPinia } from "pinia"
import App from "./App.vue"
import router from "./router"
import { useAppStore } from "./stores/app"
import "./styles/app.css"

async function boot() {
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)

  const store = useAppStore()
  await store.init()

  app.use(router)
  app.mount("#app")
}

void boot()
