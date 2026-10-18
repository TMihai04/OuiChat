import { createApp } from "vue"
import { createPinia } from "pinia"
import App from "./App.vue"
import router from "./router"
import { useAppStore } from "./stores/app"
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
  const app = createApp(App)
  const pinia = createPinia()
  app.use(pinia)

  const store = useAppStore()
  await store.init()

  app.use(router)
  app.mount("#app")
}

void boot()
