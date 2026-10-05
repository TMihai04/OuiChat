import { createApp } from "vue"
import { createPinia } from "pinia"
import App from "./App.vue"
import router from "./router"
import { useAppStore } from "./stores/app"
import "./styles/app.css"

function ignoreBlankScrollFocus(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof HTMLElement)) return
  if (!target.matches(".list-panel, .messages, .picker-list")) return
  const bounds = target.getBoundingClientRect()
  const x = event.clientX - bounds.left
  const y = event.clientY - bounds.top
  const onScrollbar = (target.scrollHeight > target.clientHeight && x >= target.clientWidth)
    || (target.scrollWidth > target.clientWidth && y >= target.clientHeight)
  if (onScrollbar) return
  event.preventDefault()
}

window.addEventListener("mousedown", ignoreBlankScrollFocus, true)

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
