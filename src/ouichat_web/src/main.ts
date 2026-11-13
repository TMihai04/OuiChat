import { createApp } from "vue"
import { createPinia } from "pinia"
import App from "./App.vue"
import router from "./router"
import { useAppStore } from "./stores/app"
import { initTheme } from "./theme"
import "./styles/app.css"

const SCROLL_AREAS = ".list-panel, .messages, .picker-list"
const SELECTABLE = ".message-text, input, textarea"

function scrollArea(target: EventTarget | null): HTMLElement | null {
  if (!(target instanceof Element)) return null
  const scroller = target.closest(SCROLL_AREAS)
  return scroller instanceof HTMLElement ? scroller : null
}

function onScrollbar(scroller: HTMLElement, event: MouseEvent): boolean {
  const bounds = scroller.getBoundingClientRect()
  const x = event.clientX - bounds.left - scroller.clientLeft
  const y = event.clientY - bounds.top - scroller.clientTop
  return (scroller.scrollHeight > scroller.clientHeight && x >= scroller.clientWidth)
    || (scroller.scrollWidth > scroller.clientWidth && y >= scroller.clientHeight)
}

function ignoreBlankCaret(event: MouseEvent) {
  const target = event.target
  const scroller = scrollArea(target)
  if (!scroller || !(target instanceof Element)) return
  if (onScrollbar(scroller, event)) return
  if (target.closest(SELECTABLE)) return
  event.preventDefault()
  const selection = window.getSelection()
  if (selection && selection.isCollapsed) selection.removeAllRanges()
}

window.addEventListener("mousedown", ignoreBlankCaret, true)

async function boot() {
  initTheme()

  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)

  const store = useAppStore()

  // Native Android back button & notification navigation hooks
  if (typeof window !== "undefined") {
    ;(window as any).onNativeBackPressed = () => {
      if (store.selectedChat) {
        store.deselectChat()
        return true
      }
      if (store.sidebarTab === "users") {
        store.sidebarTab = "chats"
        return true
      }
      return false
    }

    ;(window as any).onNativeAppResumed = () => {
      store.onAppResumed?.()
    }

    ;(window as any).selectChatFromNative = async (chatId: string) => {
      if (!store.ready) {
        await store.waitForReady()
      }
      if (store.current !== null) {
        void router.push("/app")
        void store.selectChat(chatId)
      } else {
        store.pendingChatId = chatId
      }
    }
  }

  await store.init()

  app.use(router)
  app.mount("#app")
}

void boot()
