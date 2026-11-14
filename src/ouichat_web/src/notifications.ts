// Web Audio API Synthesizer & HTML5 Notifications Manager

let audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (AudioContextClass) audioCtx = new AudioContextClass()
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume().catch(() => {})
  }
  return audioCtx
}

// Unlock AudioContext on first user interaction anywhere on the page
if (typeof window !== "undefined") {
  const unlock = () => {
    getAudioContext()
    window.removeEventListener("pointerdown", unlock)
    window.removeEventListener("keydown", unlock)
  }
  window.addEventListener("pointerdown", unlock)
  window.addEventListener("keydown", unlock)
}

const NOTIF_ENABLED_KEY = "ouichat.notifications_enabled"
const NOTIF_DISMISSED_KEY = "ouichat.notif_dismissed"

export function isNotificationBannerDismissed(): boolean {
  if (typeof window === "undefined") return false
  return localStorage.getItem(NOTIF_DISMISSED_KEY) === "true"
}

export function dismissNotificationBanner() {
  if (typeof window === "undefined") return
  localStorage.setItem(NOTIF_DISMISSED_KEY, "true")
}

export function resetNotificationBanner() {
  if (typeof window === "undefined") return
  localStorage.removeItem(NOTIF_DISMISSED_KEY)
}

export function isNotificationsGloballyEnabled(): boolean {
  if (typeof window === "undefined") return true
  const val = localStorage.getItem(NOTIF_ENABLED_KEY)
  return val === null ? true : val === "true"
}

export function setNotificationsGloballyEnabled(enabled: boolean) {
  if (typeof window === "undefined") return
  localStorage.setItem(NOTIF_ENABLED_KEY, String(enabled))
}

/**
 * Plays a pleasant, lightweight synthesized dual-tone notification chime (D5 -> A5)
 * without requiring any external audio files or downloads.
 */
export async function playNotificationChime(force = false) {
  if (!force && !isNotificationsGloballyEnabled()) return

  if (typeof window !== "undefined" && (window as any).AndroidBridge?.playChime) {
    try {
      (window as any).AndroidBridge.playChime()
      if (typeof (window as any).AndroidBridge?.vibrate === "function") {
        (window as any).AndroidBridge.vibrate(200)
      }
      return
    } catch {}
  }

  const ctx = getAudioContext()
  if (!ctx) return
  try {
    if (ctx.state === "suspended") {
      await ctx.resume().catch(() => {})
    }
    const now = ctx.currentTime

    // Play note 1: A5 (880.00 Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(880.00, now);
    gain1.gain.setValueAtTime(0.15, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.22);
    osc1.connect(gain1).connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.22);

    // Play note 2: C#6 (1108.73 Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(1108.73, now + 0.06);
    gain2.gain.setValueAtTime(0.18, now + 0.06);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
    osc2.connect(gain2).connect(ctx.destination);
    osc2.start(now + 0.06);
    osc2.stop(now + 0.28);

    // Play note 3: E6 (1318.51 Hz) ringing top tone
    const osc3 = ctx.createOscillator();
    const gain3 = ctx.createGain();
    osc3.type = "sine";
    osc3.frequency.setValueAtTime(1318.51, now + 0.12);
    gain3.gain.setValueAtTime(0.20, now + 0.12);
    gain3.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
    osc3.connect(gain3).connect(ctx.destination);
    osc3.start(now + 0.12);
    osc3.stop(now + 0.45);
  } catch {
    // Ignore audio errors if blocked by browser policy
  }
}

export function isNotificationSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window
}

export function getNotificationPermission(): NotificationPermission {
  if (!isNotificationSupported()) return "denied"
  return Notification.permission
}

export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (!isNotificationSupported()) return "denied"
  try {
    return await Notification.requestPermission()
  } catch {
    return "denied"
  }
}

interface ChatNotifEntry {
  sender: string
  chatTitle: string
  isGroup: boolean
  messages: string[]
  totalCount: number
  instance?: Notification
}

const notificationBuffers = new Map<string, ChatNotifEntry>()

export function clearNotificationBuffer(chatKey: string) {
  const entry = notificationBuffers.get(chatKey)
  if (entry?.instance) {
    try {
      entry.instance.close()
    } catch {}
  }
  notificationBuffers.delete(chatKey)
  if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearNotification) {
    try {
      const cleanChatId: string = chatKey.includes(":") ? chatKey.slice(chatKey.lastIndexOf(":") + 1) : chatKey;
      ;(window as any).AndroidBridge.clearNotification(cleanChatId)
    } catch {}
  }
}

export function clearAllNotificationBuffers() {
  for (const [key] of notificationBuffers) {
    clearNotificationBuffer(key)
  }
}

export function queueDesktopNotification(options: {
  chatId?: string
  chatKey: string
  sender: string
  chatTitle: string
  isGroup: boolean
  text: string
  icon?: string
  showPopup?: boolean
  onClick?: () => void
}) {
  if (!isNotificationsGloballyEnabled()) return

  // Play chime only for the first incoming message of a chat that doesn't already have an active notification
  const isFirstNotificationForChat = !notificationBuffers.has(options.chatKey)
  if (isFirstNotificationForChat) {
    playNotificationChime()
  }

  let entry = notificationBuffers.get(options.chatKey)
  if (!entry) {
    entry = {
      sender: options.sender,
      chatTitle: options.chatTitle,
      isGroup: options.isGroup,
      messages: [],
      totalCount: 0,
    }
    notificationBuffers.set(options.chatKey, entry)
  }

  // Increment total unread count for this notification stack
  entry.totalCount += 1

  // Truncate message snippet if excessively long
  const raw = options.text.trim() || "Sent a message"
  const snippet = raw.length > 80 ? raw.slice(0, 77) + "..." : raw
  entry.messages.push(snippet)

  // Keep up to 4 preview lines in the notification body
  if (entry.messages.length > 4) {
    entry.messages.shift()
  }

  // Format count text: "9+ new messages" for 10 or more, otherwise "{count} new messages"
  const countText = entry.totalCount >= 10
    ? "9+ new messages"
    : `${entry.totalCount} new messages`

  let title = ""
  if (options.isGroup) {
    title = entry.totalCount > 1
      ? `${options.chatTitle} (${countText})`
      : `${options.sender} (${options.chatTitle})`
  } else {
    title = entry.totalCount > 1
      ? `${options.sender} (${countText})`
      : options.sender
  }

  const body = entry.messages.join("\n")

  const shouldShowPopup = options.showPopup !== false

  // If running inside Android WebView bridge, push native notification card
  if (shouldShowPopup && typeof window !== "undefined" && (window as any).AndroidBridge?.showNotification) {
    try {
      const resolvedChatId = options.chatId || (options.chatKey.includes(":") ? options.chatKey.slice(options.chatKey.lastIndexOf(":") + 1) : options.chatKey)
      ;(window as any).AndroidBridge.showNotification(
        resolvedChatId,
        options.sender,
        options.text.trim() || "Sent a message",
        options.isGroup ? options.chatTitle : null,
        Boolean(options.isGroup)
      )
    } catch (err) {
      console.error("[NativeBridge] showNotification error:", err)
    }
  }

  const isAndroidBridge = typeof window !== "undefined" && Boolean((window as any).AndroidBridge)
  const shouldShowWebPopup = shouldShowPopup
    && !isAndroidBridge
    && isNotificationSupported()
    && Notification.permission === "granted"

  if (shouldShowWebPopup) {
    try {
      const notif = new Notification(title, {
        body,
        icon: options.icon || "/icons/app_icon.png",
        tag: options.chatKey, // Stacks into single card per chat
        silent: true,
      })

      entry.instance = notif

      notif.onclick = () => {
        window.focus()
        clearNotificationBuffer(options.chatKey)
        options.onClick?.()
        try {
          notif.close()
        } catch {}
      }
    } catch {
      // Notification error or background restriction
    }
  }
}

export function showDesktopNotification(options: {
  title: string
  body: string
  icon?: string
  tag?: string
  onClick?: () => void
}) {
  if (!isNotificationsGloballyEnabled()) return
  if (!isNotificationSupported() || Notification.permission !== "granted") return

  try {
    const notif = new Notification(options.title, {
      body: options.body,
      icon: options.icon || "/icons/app_icon.png",
      tag: options.tag,
      silent: true,
    })

    if (options.onClick) {
      notif.onclick = () => {
        window.focus()
        options.onClick?.()
        try {
          notif.close()
        } catch {}
      }
    }
  } catch {}
}
