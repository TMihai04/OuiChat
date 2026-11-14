import { computed, ref } from "vue"
import { defineStore } from "pinia"
import * as api from "../api/client"
import { ApiError, errorText } from "../api/http"
import type { ConversationRaw, MessageRaw, UserRaw, WsEvent } from "../api/types"
import { sessionKey } from "../format"
import { SocketHub } from "../ws/hub"
import { clearNotificationBuffer, queueDesktopNotification } from "../notifications"

export const MAX_SESSIONS = 3
const MESSAGE_BATCH = 30
const WINDOW_LIMIT = 180
const STORAGE_KEY = "ouichat.sessions"
const CURRENT_KEY = "ouichat.current"
const UNREAD_STORAGE_KEY = "ouichat.unread_counts"
const EXPIRED_SESSION_KEY = "ouichat.expired_session"
const REFRESH_LEAD_MS = 90_000

function getSavedItem(key: string): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(key) ?? sessionStorage.getItem(key)
}

function setSavedItem(key: string, value: string) {
  if (typeof window === "undefined") return
  try { localStorage.setItem(key, value) } catch {}
  try { sessionStorage.setItem(key, value) } catch {}
}

function removeSavedItem(key: string) {
  if (typeof window === "undefined") return
  try { localStorage.removeItem(key) } catch {}
  try { sessionStorage.removeItem(key) } catch {}
}

function accessTokenExpiry(token: string): number | null {
  const segment = token.split(".")[1]
  if (!segment) return null
  try {
    const base64 = segment.replace(/-/g, "+").replace(/_/g, "/")
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4)
    const payload = JSON.parse(atob(padded)) as { exp?: unknown }
    return typeof payload.exp === "number" ? payload.exp * 1000 : null
  } catch {
    return null
  }
}

function accessTokenFresh(token: string, leadMs: number): boolean {
  const expiry = accessTokenExpiry(token)
  if (expiry === null) return false
  return expiry - Date.now() > leadMs
}

export interface Session {
  username: string
  domain: string
  accessToken: string
  refreshToken: string
  blacklist: string[]
  mutedChats: string[]
  reachable: string[]
  status: string
  pictureId: string | null
}

export interface DirUser {
  username: string
  status: string
  pictureId: string | null
}

export interface Participant {
  username: string
  isAdmin: boolean
  lastSeenLocal: number
}

export interface Chat {
  domain: string
  id: string
  type: "direct" | "group"
  name: string | null
  description: string | null
  pictureId: string | null
  creators: string[]
  participants: Participant[]
  lastMessageAt: number
}

export interface ChatMessage {
  id: string
  chatId: string
  domain: string
  sender: string
  content: string
  attachments: string[]
  repliedTo: string | null
  createdAt: number
  updatedAt: number
  edited: boolean
}

export interface Thread {
  items: ChatMessage[]
  hasMore: boolean
  hasNewer?: boolean
  loaded: boolean
  loading: boolean
}

function normalizeUser(raw: UserRaw): DirUser {
  return {
    username: raw.username,
    status: raw.profile?.status || "Hi there!",
    pictureId: raw.profile?.picture_id || null,
  }
}

function normalizeMessage(domain: string, chatId: string, raw: MessageRaw): ChatMessage {
  return {
    id: raw.message_id,
    chatId,
    domain,
    sender: raw.sender,
    content: raw.content ?? "",
    attachments: raw.attachments ?? [],
    repliedTo: raw.replied_to ?? null,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    edited: raw.created_at !== raw.updated_at,
  }
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []
}

export const useAppStore = defineStore("app", () => {
  const ready = ref(false)
  let readyResolver: (() => void) | null = null
  const readyPromise = new Promise<void>((resolve) => {
    readyResolver = resolve
  })

  function waitForReady(): Promise<void> {
    if (ready.value) return Promise.resolve()
    return readyPromise
  }
  const sessions = ref<Session[]>([])
  const currentKey = ref<string | null>(null)
  const domainUsers = ref<Record<string, DirUser[]>>({})
  const chats = ref<Chat[]>([])
  const threads = ref<Record<string, Thread>>({})
  const selectedChatId = ref<string | null>(null)
  const pendingChatId = ref<string | null>(null)
  const unreadCounts = ref<Record<string, number>>({})
  const unreadSeparator = ref<{ chatId: string; firstMessageId: string; count: number } | null>(null)
  const pausedUntil = ref<Record<string, number>>({})
  const pauseNow = ref(Date.now())
  let pauseTimer: number | null = null

  function isChatPaused(chatId: string): boolean {
    return (pausedUntil.value[chatId] ?? 0) > pauseNow.value
  }

  function pauseChat(chatId: string, durationMs = 10_000) {
    pausedUntil.value = { ...pausedUntil.value, [chatId]: Date.now() + durationMs }
    pauseNow.value = Date.now()
    if (pauseTimer === null) {
      pauseTimer = window.setInterval(() => {
        pauseNow.value = Date.now()
        const still = Object.values(pausedUntil.value).some((until) => until > pauseNow.value)
        if (!still && pauseTimer !== null) {
          window.clearInterval(pauseTimer)
          pauseTimer = null
        }
      }, 250)
    }
  }
  const pane = ref<"users" | "chat" | "details">("users")
  const sidebarTab = ref<"chats" | "users">("chats")
  const onlineUsers = ref<Record<string, string[]>>({})
  const error = ref<string | null>(null)

  const iconCache = new Map<string, string>()
  const iconJobs = new Map<string, Promise<string>>()
  const attachmentNames = new Map<string, string>()
  const attachmentNameJobs = new Map<string, Promise<string>>()
  const recoveries = new Map<string, Promise<boolean>>()

  const refreshTimers = new Map<string, number>()

  const hub = new SocketHub({
    onEvent: (username, domain, event) => applyEvent(username, domain, event),
    onDead: (username, domain) => {
      error.value = `Connection lost with ${domain}. Logging out...`
      logout(username, domain)
    },
    ensureToken: (username, domain) => ensureToken(username, domain),
  })

  const current = computed(() => sessions.value.find((session) => sessionKey(session.username, session.domain) === currentKey.value) ?? null)

  const visibleChats = computed(() => {
    const me = current.value
    if (!me) return []
    return chats.value
      .filter((chat) => chat.domain === me.domain && chat.participants.some((participant) => participant.username === me.username))
      .slice()
      .sort((left, right) => {
        if (left.lastMessageAt !== right.lastMessageAt) return right.lastMessageAt - left.lastMessageAt
        return displayName(left).localeCompare(displayName(right))
      })
  })

  const directory = computed(() => {
    const me = current.value
    if (!me) return []
    return (domainUsers.value[me.domain] ?? [])
      .filter((user) => user.username !== me.username && me.reachable.includes(user.username))
      .slice()
      .sort((left, right) => left.username.localeCompare(right.username))
  })

  const selectedChat = computed(() => {
    const me = current.value
    if (!me || !selectedChatId.value) return null
    return chats.value.find((chat) => chat.domain === me.domain && chat.id === selectedChatId.value) ?? null
  })

  function persist() {
    const saved = sessions.value.map((session) => ({
      username: session.username,
      domain: session.domain,
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      blacklist: [...session.blacklist],
      mutedChats: [...(session.mutedChats ?? [])],
      reachable: [...session.reachable],
      status: session.status,
      pictureId: session.pictureId,
    }))
    setSavedItem(STORAGE_KEY, JSON.stringify(saved))
    setSavedItem(CURRENT_KEY, currentKey.value ?? "")
  }

  function persistUnreadCounts() {
    setSavedItem(UNREAD_STORAGE_KEY, JSON.stringify(unreadCounts.value))
  }

  function syncNativeUnreadCounts() {
    if (typeof window !== "undefined" && (window as any).AndroidBridge?.getUnreadCounts) {
      try {
        const raw = (window as any).AndroidBridge.getUnreadCounts()
        if (raw) {
          const nativeCounts = JSON.parse(raw) as Record<string, number>
          for (const [chatId, count] of Object.entries(nativeCounts)) {
            const matchingChat = chats.value.find((entry) => entry.id === chatId)
            const domain = matchingChat?.domain || current.value?.domain
            if (domain && count > 0) {
              const key = `${domain}:${chatId}`
              unreadCounts.value[key] = Math.max(unreadCounts.value[key] ?? 0, count)
            }
          }
          persistUnreadCounts()
        }
      } catch (err) {
        console.error("Error syncing native unread counts", err)
      }
    }
  }

  function findSession(username: string, domain: string): Session | undefined {
    return sessions.value.find((session) => session.username === username && session.domain === domain)
  }

  function sessionsOn(domain: string): Session[] {
    return sessions.value.filter((session) => session.domain === domain)
  }

  function otherUsername(chat: Chat, username: string): string | null {
    const names = chat.participants.map((participant) => participant.username)
    if (names.length < 2) return names.find((name) => name !== username) ?? null
    return names[0] === username ? names[1] : names[0]
  }

  function displayName(chat: Chat): string {
    const me = current.value
    if (!me) return chat.name ?? "Chat"
    if (chat.type === "group") return chat.name || "Chatroom"
    return otherUsername(chat, me.username) ?? "Direct"
  }

  function displayDescription(chat: Chat): string {
    const me = current.value
    if (!me) return ""
    if (chat.type === "group") return chat.description ?? ""
    const other = otherUsername(chat, me.username)
    if (!other) return ""
    return (domainUsers.value[chat.domain] ?? []).find((user) => user.username === other)?.status ?? ""
  }

  function chatPicture(chat: Chat): { pictureId: string | null; fallback: string } {
    const me = current.value
    if (chat.type === "group" || !me) {
      return { pictureId: chat.pictureId, fallback: "/icons/chat_room_icon.png" }
    }
    const other = otherUsername(chat, me.username)
    const user = (domainUsers.value[chat.domain] ?? []).find((entry) => entry.username === other)
    return { pictureId: user?.pictureId ?? null, fallback: "/icons/default_user_icon.png" }
  }

  function isWritable(chat: Chat): boolean {
    const me = current.value
    if (!me || chat.domain !== me.domain) return false
    if (chat.type !== "direct") return true
    const other = otherUsername(chat, me.username)
    if (!other) return false
    if (me.blacklist.includes(other)) return false
    return me.reachable.includes(other)
  }

  function isAdmin(chat: Chat, username: string): boolean {
    return chat.participants.some((participant) => participant.username === username && participant.isAdmin)
  }

  function isCreator(chat: Chat, username: string): boolean {
    return chat.creators.includes(username)
  }

  function presenceOf(domain: string, username: string): "online" | "offline" {
    return (onlineUsers.value[domain] ?? []).includes(username) ? "online" : "offline"
  }

  function setOnline(domain: string, names: string[]) {
    onlineUsers.value = { ...onlineUsers.value, [domain]: names }
  }

  function markOnline(domain: string, username: string, online: boolean) {
    const names = new Set(onlineUsers.value[domain] ?? [])
    if (online) names.add(username)
    else names.delete(username)
    setOnline(domain, [...names])
  }

  function unread(chat: Chat): boolean {
    const me = current.value
    if (!me) return false
    const self = chat.participants.find((participant) => participant.username === me.username)
    if (!self) return false
    return chat.lastMessageAt > self.lastSeenLocal
  }

  function directChatId(username: string, other: string, domain: string): string | null {
    const chat = chats.value.find((entry) => {
      if (entry.domain !== domain || entry.type !== "direct") return false
      const names = entry.participants.map((participant) => participant.username)
      return names.includes(username) && names.includes(other)
    })
    return chat?.id ?? null
  }

  function normalizeChat(domain: string, raw: ConversationRaw): Chat {
    return {
      domain,
      id: raw.conversation_id,
      type: raw.type,
      name: raw.profile?.name ?? null,
      description: raw.profile?.description ?? null,
      pictureId: raw.profile?.picture_id || null,
      creators: raw.preferences?.created_by ?? [],
      participants: (raw.preferences?.participants ?? []).map((participant) => ({
        username: participant.username,
        isAdmin: participant.is_admin,
        lastSeenLocal: typeof participant.last_seen === "number" ? participant.last_seen : 0,
      })),
      lastMessageAt: 0,
    }
  }

  function upsertChat(next: Chat) {
    const index = chats.value.findIndex((chat) => chat.domain === next.domain && chat.id === next.id)
    if (index === -1) {
      chats.value.push(next)
      return
    }
    const previous = chats.value[index]
    next.lastMessageAt = Math.max(previous.lastMessageAt, next.lastMessageAt)
    for (const participant of next.participants) {
      const old = previous.participants.find((entry) => entry.username === participant.username)
      if (old) participant.lastSeenLocal = Math.max(old.lastSeenLocal, participant.lastSeenLocal)
    }
    chats.value[index] = next
  }

  function removeChat(domain: string, chatId: string) {
    chats.value = chats.value.filter((chat) => !(chat.domain === domain && chat.id === chatId))
    delete threads.value[`${domain}:${chatId}`]
    if (selectedChatId.value === chatId && current.value?.domain === domain) {
      selectedChatId.value = null
      pane.value = "users"
    }
  }

  function maybeDropChat(chat: Chat) {
    const kept = sessionsOn(chat.domain).some((session) => chat.participants.some((participant) => participant.username === session.username))
    if (!kept) {
      removeChat(chat.domain, chat.id)
      return
    }
    const me = current.value
    if (me && me.domain === chat.domain && selectedChatId.value === chat.id && !chat.participants.some((participant) => participant.username === me.username)) {
      selectedChatId.value = null
      pane.value = "users"
    }
  }

  function setDirectory(domain: string, users: DirUser[]) {
    const merged: DirUser[] = []
    for (const user of users) {
      if (!merged.some((entry) => entry.username === user.username)) merged.push(user)
    }
    domainUsers.value = { ...domainUsers.value, [domain]: merged }
  }

  function upsertDirUser(domain: string, user: DirUser) {
    const list = (domainUsers.value[domain] ?? []).slice()
    const index = list.findIndex((entry) => entry.username === user.username)
    if (index === -1) list.push(user)
    else list[index] = user
    domainUsers.value = { ...domainUsers.value, [domain]: list }
    const session = findSession(user.username, domain)
    if (session) {
      session.status = user.status
      session.pictureId = user.pictureId
    }
  }

  function removeDirUser(domain: string, username: string) {
    domainUsers.value = {
      ...domainUsers.value,
      [domain]: (domainUsers.value[domain] ?? []).filter((user) => user.username !== username),
    }
    for (const session of sessionsOn(domain)) {
      session.reachable = session.reachable.filter((name) => name !== username)
    }
  }

  function threadFor(domain: string, chatId: string): Thread {
    const key = `${domain}:${chatId}`
    if (!threads.value[key]) {
      threads.value[key] = { items: [], hasMore: true, hasNewer: false, loaded: false, loading: false }
    }
    return threads.value[key]
  }

  function markRead(chat: Chat, username: string) {
    const self = chat.participants.find((participant) => participant.username === username)
    if (!self) return
    self.lastSeenLocal = Math.max(self.lastSeenLocal, Date.now(), chat.lastMessageAt)
    const session = findSession(username, chat.domain)
    if (session) void persistSeen(session, chat.id)
  }

  async function persistSeen(session: Session, chatId: string) {
    try {
      const response = await withSession(session, (active) => api.markChatSeen(active.domain, active.accessToken, chatId))
      const live = chats.value.find((entry) => entry.domain === session.domain && entry.id === chatId)
      const self = live?.participants.find((participant) => participant.username === session.username)
      if (self) self.lastSeenLocal = Math.max(self.lastSeenLocal, response.item.last_seen)
    } catch {
      return
    }
  }

  function forgetIcon(domain: string, pictureId: string | null) {
    if (!pictureId) return
    const key = `${domain}:${pictureId}`
    const url = iconCache.get(key)
    if (url) URL.revokeObjectURL(url)
    iconCache.delete(key)
    iconJobs.delete(key)
  }

  async function resolveIcon(domain: string, pictureId: string | null, fallback: string): Promise<string> {
    if (!pictureId) return fallback
    const key = `${domain}:${pictureId}`
    const cached = iconCache.get(key)
    if (cached) return cached
    const pending = iconJobs.get(key)
    if (pending) return pending
    const session = current.value?.domain === domain ? current.value : sessionsOn(domain)[0]
    if (!session) return fallback
    const job = (async () => {
      try {
        const file = await withSession(session, (active) => api.downloadFile(active.domain, active.accessToken, pictureId))
        const url = URL.createObjectURL(file.blob)
        iconCache.set(key, url)
        return url
      } catch {
        return fallback
      } finally {
        iconJobs.delete(key)
      }
    })()
    iconJobs.set(key, job)
    return job
  }

  async function resolveAttachmentName(domain: string, fileId: string): Promise<string> {
    const key = `${domain}:${fileId}`
    const known = attachmentNames.get(key)
    if (known) return known
    const pending = attachmentNameJobs.get(key)
    if (pending) return pending
    const session = current.value?.domain === domain ? current.value : sessionsOn(domain)[0]
    if (!session) return fileId
    const job = (async () => {
      try {
        const name = await withSession(session, (active) => api.attachmentFileName(active.domain, active.accessToken, fileId))
        attachmentNames.set(key, name)
        return name
      } catch {
        return fileId
      } finally {
        attachmentNameJobs.delete(key)
      }
    })()
    attachmentNameJobs.set(key, job)
    return job
  }

  async function downloadAttachment(fileId: string) {
    const me = requireCurrent()
    const file = await withSession(me, (session) => api.downloadFile(session.domain, session.accessToken, fileId))
    const cached = attachmentNames.get(`${me.domain}:${fileId}`)
    const filename = file.filename !== "download" ? file.filename : cached || file.filename

    if (typeof window !== "undefined" && (window as any).AndroidBridge?.saveBlob) {
      try {
        const base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(file.blob)
        })
        const handled = (window as any).AndroidBridge.saveBlob(
          base64,
          file.blob.type || "application/octet-stream",
          filename
        )
        if (handled) return
      } catch (e) {
        console.error("AndroidBridge.saveBlob failed, falling back to browser download", e)
      }
    }

    const url = URL.createObjectURL(file.blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  async function recover(session: Session, _interactive = false): Promise<boolean> {
    const key = sessionKey(session.username, session.domain)
    const existing = recoveries.get(key)
    if (existing) return existing
    const job = (async () => {
      try {
        const tokens = await api.refreshTokens(session.domain, session.refreshToken)
        if (!findSession(session.username, session.domain)) return false
        session.accessToken = tokens.access_token
        session.refreshToken = tokens.refresh_token
        hub.updateToken(session.username, session.domain, session.accessToken)
        persist()
        syncNativeBridge(session)
        scheduleRefresh(session)
        return true
      } catch {
        setSavedItem(EXPIRED_SESSION_KEY, JSON.stringify({ username: session.username, domain: session.domain }))
        logout(session.username, session.domain)
        return false
      }
    })().finally(() => {
      recoveries.delete(key)
    })
    recoveries.set(key, job)
    return job
  }

  async function withSession<T>(session: Session, action: (session: Session) => Promise<T>, interactive = true): Promise<T> {
    try {
      return await action(session)
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error
      const ok = await recover(session, interactive)
      if (!ok || !findSession(session.username, session.domain)) throw error
      return action(session)
    }
  }

  function requireCurrent(): Session {
    if (!current.value) throw new Error("Not signed in")
    return current.value
  }

  async function loadDomain(session: Session, interactive = true) {
    const [chatList, userList] = await Promise.all([
      withSession(session, (active) => api.listChats(active.domain, active.accessToken), interactive),
      withSession(session, (active) => api.listUsers(active.domain, active.accessToken), interactive),
    ])
    for (const raw of chatList.items ?? []) upsertChat(normalizeChat(session.domain, raw))
    const white = userList.item?.white ?? []
    const black = userList.item?.black ?? []
    setDirectory(session.domain, [...white, ...black].map(normalizeUser))
    session.reachable = white.map((user) => user.username)
    const self = [...white, ...black].find((user) => user.username === session.username)
    if (self) {
      session.status = self.profile?.status || session.status
      session.pictureId = self.profile?.picture_id || null
    }
    await hydrateLastMessages(session, interactive)
  }

  async function hydrateLastMessages(session: Session, interactive: boolean) {
    const mine = chats.value.filter((chat) => chat.domain === session.domain && chat.participants.some((participant) => participant.username === session.username))
    await Promise.all(mine.map(async (chat) => {
      try {
        const raw = await withSession(session, (active) => api.listMessages(
          active.domain,
          active.accessToken,
          chat.id,
          "old",
          null,
          15,
        ), interactive)
        const newest = raw[raw.length - 1]
        if (!newest) return
        const live = chats.value.find((entry) => entry.domain === session.domain && entry.id === chat.id)
        if (!live) return
        live.lastMessageAt = Math.max(live.lastMessageAt, newest.created_at)
        const self = live.participants.find((participant) => participant.username === session.username)
        if (self && self.lastSeenLocal === 0 && live.lastMessageAt === 0) {
          const response = await withSession(session, (active) => api.markChatSeen(active.domain, active.accessToken, live.id), interactive)
          self.lastSeenLocal = Math.max(self.lastSeenLocal, response.item.last_seen)
        } else if (self && live.lastMessageAt > self.lastSeenLocal) {
          const unreadMsgs = raw.filter((m) => m.created_at > self.lastSeenLocal && m.sender !== session.username)
          if (unreadMsgs.length > 0) {
            const key = `${session.domain}:${chat.id}`
            unreadCounts.value[key] = Math.max(unreadCounts.value[key] ?? 0, unreadMsgs.length)
            persistUnreadCounts()
          }
        }
      } catch {
        return
      }
    }))
  }

  async function signIn(domain: string, username: string, password: string, register: boolean, signal?: AbortSignal) {
    const cleanDomain = domain.trim()
    const cleanUsername = username.trim()
    if (!cleanDomain) throw new Error("Domain must not be empty")
    if (!cleanUsername) throw new Error("Username must not be empty")
    if (!password) throw new Error("Password must not be empty")
    if (sessions.value.length >= MAX_SESSIONS) throw new Error("You can only be signed in to 3 accounts")
    if (findSession(cleanUsername, cleanDomain)) throw new Error("Username already logged in")
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError")
    if (register) await api.registerAccount(cleanDomain, cleanUsername, password, signal)

    if (signal?.aborted) throw new DOMException("Aborted", "AbortError")
    const tokens = await api.loginAccount(cleanDomain, cleanUsername, password, signal)
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError")
    const me = await api.getMe(cleanDomain, tokens.access_token, signal)
    const session: Session = {
      username: me.item.username || cleanUsername,
      domain: cleanDomain,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      blacklist: me.item.preferences?.blacklist ?? [],
      mutedChats: me.item.preferences?.muted_chats ?? [],
      reachable: [],
      status: me.item.profile?.status || "Hi there!",
      pictureId: me.item.profile?.picture_id || null,
    }
    const previousKey = currentKey.value
    sessions.value.push(session)
    currentKey.value = sessionKey(session.username, session.domain)
    selectedChatId.value = null
    unreadSeparator.value = null
    pane.value = "users"
    try {
      await loadDomain(session)
    } catch (cause) {
      sessions.value = sessions.value.filter((entry) => entry !== session)
      currentKey.value = previousKey
      throw cause
    }
    hub.connect(session.username, session.domain, session.accessToken)
    scheduleRefresh(session)
    persist()
    syncNativeBridge(session)
  }

  async function switchTo(username: string, domain: string) {
    const session = findSession(username, domain)
    if (!session) return
    if (current.value && selectedChat.value) markRead(selectedChat.value, current.value.username)
    currentKey.value = sessionKey(username, domain)
    selectedChatId.value = null
    unreadSeparator.value = null
    pane.value = "users"
    persist()
    syncNativeBridge(session)
    try {
      await loadDomain(session)
    } catch (cause) {
      error.value = errorText(cause)
    }
  }

  function clearRefresh(username: string, domain: string) {
    const key = sessionKey(username, domain)
    const timer = refreshTimers.get(key)
    if (timer !== undefined) window.clearTimeout(timer)
    refreshTimers.delete(key)
  }

  function scheduleRefresh(session: Session) {
    clearRefresh(session.username, session.domain)
    const expiry = accessTokenExpiry(session.accessToken)
    const delay = expiry === null ? 10 * 60 * 1000 : Math.max(0, expiry - Date.now() - REFRESH_LEAD_MS)
    const key = sessionKey(session.username, session.domain)
    const timer = window.setTimeout(() => {
      refreshTimers.delete(key)
      const live = findSession(session.username, session.domain)
      if (live) void recover(live, true)
    }, delay)
    refreshTimers.set(key, timer)
  }

  async function ensureToken(username: string, domain: string) {
    const session = findSession(username, domain)
    if (!session) return null
    if (accessTokenFresh(session.accessToken, REFRESH_LEAD_MS)) {
      return { token: session.accessToken, refreshed: false }
    }
    const ok = await recover(session, true)
    const live = findSession(username, domain)
    if (!ok || !live) return null
    return { token: live.accessToken, refreshed: true }
  }

  function logout(username: string, domain: string) {
    clearRefresh(username, domain)
    const leavingCurrent = current.value?.username === username && current.value.domain === domain
    if (leavingCurrent && selectedChat.value) markRead(selectedChat.value, username)
    unreadSeparator.value = null
    hub.disconnect(username, domain)
    const remaining = sessions.value.filter((session) => !(session.username === username && session.domain === domain))
    const others = remaining.filter((session) => session.domain === domain)
    if (others.length === 0) {
      chats.value = chats.value.filter((chat) => chat.domain !== domain)
      const nextUsers = { ...domainUsers.value }
      delete nextUsers[domain]
      domainUsers.value = nextUsers
      for (const key of Object.keys(threads.value)) {
        if (key.startsWith(`${domain}:`)) delete threads.value[key]
      }
    } else {
      chats.value = chats.value.filter((chat) => {
        if (chat.domain !== domain) return true
        return chat.participants.some((participant) => others.some((session) => session.username === participant.username))
      })
    }
    sessions.value = remaining
    if (leavingCurrent) {
      selectedChatId.value = null
      pane.value = "users"
      const fallback = remaining[0]
      currentKey.value = fallback ? sessionKey(fallback.username, fallback.domain) : null
    }
    if (remaining.length === 0) {
      removeSavedItem(STORAGE_KEY)
      removeSavedItem(CURRENT_KEY)
      if (typeof window !== "undefined" && (window as any).AndroidBridge) {
        try {
          (window as any).AndroidBridge.onLogout()
        } catch (err) {
          console.error("[NativeBridge] onLogout error:", err)
        }
      }
    } else {
      syncAllNativeSessions()
    }
    persist()
  }

  function logoutCurrent() {
    const me = current.value
    if (!me) return
    logout(me.username, me.domain)
  }

  async function selectChat(chatId: string) {
    if (!ready.value) {
      pendingChatId.value = chatId
      return
    }
    let me = current.value
    if (!me && sessions.value.length > 0) {
      await switchTo(sessions.value[0].username, sessions.value[0].domain)
      me = current.value
    }
    if (!me) return

    let chat = chats.value.find((entry) => entry.domain === me!.domain && entry.id === chatId)
    if (!chat) {
      // Check if chat belongs to another logged-in user session
      for (const otherSession of sessions.value) {
        if (otherSession !== me) {
          const match = chats.value.find((entry) => entry.domain === otherSession.domain && entry.id === chatId)
          if (match) {
            await switchTo(otherSession.username, otherSession.domain)
            me = otherSession
            chat = match
            break
          }
        }
      }
    }
    if (!chat) {
      await fetchChat(me.username, me.domain, chatId)
      chat = chats.value.find((entry) => entry.domain === me!.domain && entry.id === chatId)
    }
    if (!chat) return
    if (selectedChat.value && selectedChat.value.id !== chatId) {
      markRead(selectedChat.value, me.username)
      clearNotificationBuffer(`${selectedChat.value.domain}:${selectedChat.value.id}`)
      if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearNotification) {
        try { (window as any).AndroidBridge.clearNotification(selectedChat.value.id) } catch {}
      }
    }

    const wasUnread = unread(chat) || (unreadCounts.value[`${me.domain}:${chatId}`] || 0) > 0
    const selfParticipant = chat.participants.find((p) => p.username === me!.username)
    const lastSeen = selfParticipant?.lastSeenLocal ?? 0
    const cachedBadge = unreadCounts.value[`${me.domain}:${chatId}`] || 0

    selectedChatId.value = chatId
    pane.value = "chat"
    unreadSeparator.value = null

    clearNotificationBuffer(`${me.domain}:${chatId}`)
    if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearNotification) {
      try { (window as any).AndroidBridge.clearNotification(chatId) } catch {}
    }
    if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearUnreadCount) {
      try { (window as any).AndroidBridge.clearUnreadCount(chatId) } catch {}
    }
    unreadCounts.value[`${me.domain}:${chatId}`] = 0
    persistUnreadCounts()

    // Prune inactive threads in memory to keep DOM and memory lean across multiple rooms
    for (const [key, t] of Object.entries(threads.value)) {
      if (key !== `${me.domain}:${chatId}` && t.items.length > MESSAGE_BATCH) {
        t.items = t.items.slice(-MESSAGE_BATCH)
        t.hasMore = true
        t.hasNewer = false
      }
    }

    const initialBatch = wasUnread && cachedBadge > MESSAGE_BATCH
      ? Math.min(cachedBadge + 10, 100)
      : MESSAGE_BATCH

    await ensureMessages(chat, null, initialBatch)

    if (wasUnread) {
      const thread = threadFor(chat.domain, chat.id)
      while (
        thread.hasMore &&
        thread.items.length > 0 &&
        thread.items[0].createdAt > lastSeen &&
        thread.items.length < 200
      ) {
        await ensureMessages(chat, thread.items[0].id)
      }

      const unreadItems = thread.items.filter((m) => m.createdAt > lastSeen && m.sender !== me!.username)
      if (unreadItems.length > 0) {
        unreadSeparator.value = {
          chatId: chat.id,
          firstMessageId: unreadItems[0].id,
          count: Math.max(unreadItems.length, cachedBadge),
        }
      } else if (cachedBadge > 0 && thread.items.length > 0) {
        const sliceCount = Math.min(cachedBadge, thread.items.length)
        const firstUnread = thread.items[thread.items.length - sliceCount]
        unreadSeparator.value = {
          chatId: chat.id,
          firstMessageId: firstUnread.id,
          count: cachedBadge,
        }
      }
    }

    markRead(chat, me.username)
  }

  function showUsers() {
    const me = current.value
    if (me && selectedChat.value) markRead(selectedChat.value, me.username)
    sidebarTab.value = "users"
    selectedChatId.value = null
    unreadSeparator.value = null
    pane.value = "users"
  }

  function showDetails() {
    if (!selectedChat.value) return
    pane.value = "details"
  }

  function showChat() {
    if (!selectedChat.value) return
    pane.value = "chat"
  }

  function markSelectedRead() {
    const me = current.value
    if (!me || !selectedChat.value) return
    markRead(selectedChat.value, me.username)
    clearNotificationBuffer(`${selectedChat.value.domain}:${selectedChat.value.id}`)
    unreadCounts.value[`${me.domain}:${selectedChat.value.id}`] = 0
    persistUnreadCounts()
    if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearUnreadCount) {
      try { (window as any).AndroidBridge.clearUnreadCount(selectedChat.value.id) } catch {}
    }
  }

  async function ensureMessages(chat: Chat, beforeId: string | null, batchSize = MESSAGE_BATCH) {
    const me = current.value
    if (!me || me.domain !== chat.domain) return
    const thread = threadFor(chat.domain, chat.id)
    if (thread.loading) return
    if (beforeId && !thread.hasMore) return
    thread.loading = true
    try {
      const raw = await withSession(me, (session) => api.listMessages(
        session.domain,
        session.accessToken,
        chat.id,
        "old",
        beforeId,
        batchSize,
      ))
      const incoming = raw.map((message) => normalizeMessage(chat.domain, chat.id, message))
      if (!beforeId) {
        thread.items = incoming
        thread.hasNewer = false
      } else {
        const known = new Set(thread.items.map((message) => message.id))
        const older = incoming.filter((message) => message.id !== beforeId && !known.has(message.id))
        thread.items = [...older, ...thread.items]
        // Sliding window: prune excess newer messages from the bottom
        if (thread.items.length > WINDOW_LIMIT) {
          thread.items = thread.items.slice(0, WINDOW_LIMIT)
          thread.hasNewer = true
        }
      }
      thread.hasMore = raw.length >= batchSize
      thread.loaded = true
      const newest = thread.items[thread.items.length - 1]
      if (newest) chat.lastMessageAt = Math.max(chat.lastMessageAt, newest.createdAt)
    } catch (cause) {
      error.value = errorText(cause)
    } finally {
      thread.loading = false
    }
  }

  async function loadOlder() {
    const chat = selectedChat.value
    if (!chat) return
    const thread = threadFor(chat.domain, chat.id)
    const oldest = thread.items[0]
    if (!oldest) return
    await ensureMessages(chat, oldest.id)
  }

  async function loadNewer() {
    const chat = selectedChat.value
    if (!chat) return
    const thread = threadFor(chat.domain, chat.id)
    if (thread.loading || !thread.hasNewer) return
    const me = current.value
    if (!me || me.domain !== chat.domain) return
    const newest = thread.items[thread.items.length - 1]
    if (!newest) return
    thread.loading = true
    try {
      const raw = await withSession(me, (session) => api.listMessages(
        session.domain,
        session.accessToken,
        chat.id,
        "new",
        newest.id,
        MESSAGE_BATCH,
      ))
      const incoming = raw.map((message) => normalizeMessage(chat.domain, chat.id, message))
      const known = new Set(thread.items.map((message) => message.id))
      const newer = incoming.filter((message) => message.id !== newest.id && !known.has(message.id))
      if (newer.length > 0) {
        thread.items = [...thread.items, ...newer]
        // Sliding window: prune excess older messages from the top
        if (thread.items.length > WINDOW_LIMIT) {
          thread.items = thread.items.slice(thread.items.length - WINDOW_LIMIT)
          thread.hasMore = true
        }
      }
      thread.hasNewer = raw.length >= MESSAGE_BATCH
    } catch (cause) {
      error.value = errorText(cause)
    } finally {
      thread.loading = false
    }
  }

  async function revealMessage(messageId: string): Promise<boolean> {
    const chat = selectedChat.value
    if (!chat) return false
    const thread = threadFor(chat.domain, chat.id)
    if (!thread.loaded) await ensureMessages(chat, null)
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (thread.items.some((message) => message.id === messageId)) return true
      if (!thread.hasMore) return false
      const oldest = thread.items[0]
      if (!oldest) return false
      await ensureMessages(chat, oldest.id)
    }
    return thread.items.some((message) => message.id === messageId)
  }

  async function openDirect(username: string) {
    const me = requireCurrent()
    if (username === me.username) return
    const existing = directChatId(me.username, username, me.domain)
    if (existing) {
      await selectChat(existing)
      return
    }
    if (me.blacklist.includes(username)) return
    const created = await withSession(me, (session) => api.createChat(session.domain, session.accessToken, {
      type: "direct",
      participants: { [session.username]: true, [username]: true },
    }))
    const details = await withSession(me, (session) => api.getChat(session.domain, session.accessToken, created.item.conversation_id))
    upsertChat(normalizeChat(me.domain, details.item))
    await selectChat(created.item.conversation_id)
  }

  async function createGroup(usernames: string[]) {
    const me = requireCurrent()
    const participants: Record<string, boolean> = { [me.username]: true }
    for (const username of usernames) participants[username] = false
    const name = `${me.username}s Chatroom`
    const created = await withSession(me, (session) => api.createChat(session.domain, session.accessToken, {
      type: "group",
      group: { name, description: name, picture_id: null },
      participants,
    }))
    const details = await withSession(me, (session) => api.getChat(session.domain, session.accessToken, created.item.conversation_id))
    upsertChat(normalizeChat(me.domain, details.item))
    await selectChat(created.item.conversation_id)
  }

  async function addMembers(chatId: string, usernames: string[]) {
    const me = requireCurrent()
    await withSession(me, (session) => api.changeMembers(session.domain, session.accessToken, chatId, usernames, true))
  }

  async function removeMembers(chatId: string, usernames: string[]) {
    const me = requireCurrent()
    await withSession(me, (session) => api.changeMembers(session.domain, session.accessToken, chatId, usernames, false))
  }

  async function leaveChatById(chatId: string) {
    const me = requireCurrent()
    await withSession(me, (session) => api.leaveChat(session.domain, session.accessToken, chatId))
  }

  async function deleteChatById(chatId: string) {
    const me = requireCurrent()
    await withSession(me, (session) => api.deleteChat(session.domain, session.accessToken, chatId))
  }

  async function setAdmin(chatId: string, username: string, admin: boolean) {
    const me = requireCurrent()
    await withSession(me, (session) => api.setAdmins(session.domain, session.accessToken, chatId, { [username]: admin }))
  }

  async function renameChat(chatId: string, name: string) {
    const me = requireCurrent()
    await withSession(me, (session) => api.setChatField(session.domain, session.accessToken, chatId, "name", { name }))
  }

  async function describeChat(chatId: string, description: string) {
    const me = requireCurrent()
    await withSession(me, (session) => api.setChatField(session.domain, session.accessToken, chatId, "description", { description }))
  }

  async function changeChatIcon(chatId: string, file: File) {
    const me = requireCurrent()
    const iconId = await withSession(me, (session) => api.uploadFile(session.domain, session.accessToken, file, "icon"))
    await withSession(me, (session) => api.setChatField(session.domain, session.accessToken, chatId, "picture", { icon_id: iconId }))
  }

  async function blockUser(username: string, block: boolean) {
    const me = requireCurrent()
    await withSession(me, (session) => api.setBlacklist(session.domain, session.accessToken, username, block))
    if (block) {
      if (!me.blacklist.includes(username)) me.blacklist.push(username)
    } else {
      me.blacklist = me.blacklist.filter((name) => name !== username)
    }
    persist()
  }

  async function sendChatMessage(
    text: string,
    files: File[],
    repliedTo: string | null,
    onProgress?: (uploadedCount: number, totalCount: number) => void,
  ) {
    const me = requireCurrent()
    const chat = selectedChat.value
    if (!chat) return
    const uploaded: string[] = []
    let uploadError: string | null = null

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      if (i > 0) {
        // Micro-pause to allow keep-alive TCP sockets to settle between uploads
        await new Promise((resolve) => setTimeout(resolve, 150))
      }
      onProgress?.(uploaded.length, files.length)
      try {
        let fileId: string | null = null
        let lastErr: unknown = null
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            if (attempt > 0) {
              await new Promise((resolve) => setTimeout(resolve, attempt * 250))
            }
            fileId = await withSession(me, (session) => api.uploadFile(session.domain, session.accessToken, file, "attachment"))
            break
          } catch (err) {
            lastErr = err
            if (!(err instanceof ApiError && err.status === 0)) {
              throw err
            }
          }
        }
        if (!fileId) throw lastErr
        attachmentNames.set(`${me.domain}:${fileId}`, file.name)
        uploaded.push(fileId)
        onProgress?.(uploaded.length, files.length)
      } catch (cause) {
        uploadError = `Failed to upload "${file.name}": ${errorText(cause)}`
        break
      }
    }
    if (uploadError) throw new Error(uploadError)
    const body: { content?: string; attachments?: string[]; replied_to?: string } = {}
    if (text) body.content = text
    if (uploaded.length) body.attachments = uploaded
    if (repliedTo) body.replied_to = repliedTo
    await withSession(me, (session) => api.sendMessage(session.domain, session.accessToken, chat.id, body))
    unreadSeparator.value = null
  }

  async function editChatMessage(messageId: string, text: string) {
    const me = requireCurrent()
    const chat = selectedChat.value
    if (!chat) return
    await withSession(me, (session) => api.editMessage(session.domain, session.accessToken, chat.id, messageId, text))
  }

  async function deleteChatMessage(messageId: string) {
    const me = requireCurrent()
    const chat = selectedChat.value
    if (!chat) return
    await withSession(me, (session) => api.deleteMessage(session.domain, session.accessToken, chat.id, messageId))
  }

  async function changeStatus(status: string) {
    const me = requireCurrent()
    await withSession(me, (session) => api.setStatus(session.domain, session.accessToken, status))
    me.status = status
    const listed = (domainUsers.value[me.domain] ?? []).find((user) => user.username === me.username)
    if (listed) listed.status = status
    persist()
  }

  async function changeOwnIcon(file: File) {
    const me = requireCurrent()
    const iconId = await withSession(me, (session) => api.uploadFile(session.domain, session.accessToken, file, "icon"))
    await withSession(me, (session) => api.setUserPicture(session.domain, session.accessToken, iconId))
    forgetIcon(me.domain, me.pictureId)
    me.pictureId = iconId
    const listed = (domainUsers.value[me.domain] ?? []).find((user) => user.username === me.username)
    if (listed) listed.pictureId = iconId
    persist()
  }

  function userByName(domain: string, username: string): DirUser | undefined {
    return (domainUsers.value[domain] ?? []).find((user) => user.username === username)
  }

  function pickerCandidates(chat: Chat | null): DirUser[] {
    const me = current.value
    if (!me) return []
    const members = new Set(chat?.participants.map((participant) => participant.username) ?? [])
    return (domainUsers.value[me.domain] ?? [])
      .filter((user) => {
        if (user.username === me.username) return false
        if (me.blacklist.includes(user.username)) return false
        if (chat && members.has(user.username)) return false
        return true
      })
      .sort((left, right) => left.username.localeCompare(right.username))
  }

  function removableMembers(chat: Chat): DirUser[] {
    const me = current.value
    if (!me) return []
    const creator = isCreator(chat, me.username)
    return chat.participants
      .filter((participant) => participant.username !== me.username)
      .filter((participant) => creator || !participant.isAdmin)
      .map((participant) => userByName(chat.domain, participant.username) ?? {
        username: participant.username,
        status: "",
        pictureId: null,
      })
      .sort((left, right) => left.username.localeCompare(right.username))
  }

  function applyEvent(username: string, domain: string, event: WsEvent) {
    const [root, child] = event.scope.split(".")
    const data = event.data
    if (root === "token") {
      const session = findSession(username, domain)
      if (session) void recover(session, true)
      return
    }
    if (root === "user" && !child) {
      if (event.type === "create") {
        const raw = data as unknown as UserRaw
        upsertDirUser(domain, normalizeUser(raw))
        for (const session of sessionsOn(domain)) {
          if (!session.reachable.includes(raw.username)) session.reachable.push(raw.username)
        }
      } else if (event.type === "delete" && typeof data.username === "string") {
        removeDirUser(domain, data.username)
      }
      return
    }
    if (root === "user" && event.type === "update") {
      if (child === "blacklist" && typeof data.username === "string") {
        const session = findSession(username, domain)
        if (!session) return
        if (data.is_blacklisted) session.reachable = session.reachable.filter((name) => name !== data.username)
        else if (!session.reachable.includes(data.username)) session.reachable.push(data.username)
        persist()
      } else if (child === "muted_chats" && typeof data.chat_id === "string") {
        const session = findSession(username, domain)
        if (!session) return
        if (!session.mutedChats) session.mutedChats = []
        if (data.is_muted && !session.mutedChats.includes(data.chat_id)) {
          session.mutedChats.push(data.chat_id)
        } else if (!data.is_muted) {
          session.mutedChats = session.mutedChats.filter((id) => id !== data.chat_id)
        }
        persist()
        syncNativeBridge(session)
      } else if (child === "status" && typeof data.username === "string" && typeof data.status === "string") {
        const user = userByName(domain, data.username)
        if (user) user.status = data.status
        const session = findSession(data.username, domain)
        if (session) session.status = data.status
      } else if (child === "presence") {
        if (Array.isArray(data.usernames)) setOnline(domain, asStringList(data.usernames))
        else if (typeof data.username === "string" && typeof data.online === "boolean") markOnline(domain, data.username, data.online)
      } else if (child === "picture" && typeof data.username === "string") {
        const pictureId = typeof data.picture_id === "string" ? data.picture_id : null
        const user = userByName(domain, data.username)
        if (user) {
          forgetIcon(domain, user.pictureId)
          user.pictureId = pictureId
        }
        const session = findSession(data.username, domain)
        if (session) {
          forgetIcon(domain, session.pictureId)
          session.pictureId = pictureId
        }
      }
      return
    }
    if (root === "conversation" && !child) {
      if (event.type === "create") upsertChat(normalizeChat(domain, data as unknown as ConversationRaw))
      else if (event.type === "delete" && typeof data.conversation_id === "string") removeChat(domain, data.conversation_id)
      return
    }
    if (root === "conversation" && event.type === "update" && typeof data.conversation_id === "string") {
      const chat = chats.value.find((entry) => entry.domain === domain && entry.id === data.conversation_id)
      if (child === "participants") {
        const who = asStringList(data.who)
        if (data.operation === "removed") {
          if (!chat) return
          chat.participants = chat.participants.filter((participant) => !who.includes(participant.username))
          maybeDropChat(chat)
        } else if (data.operation === "added") {
          if (!chat) {
            void fetchChat(username, domain, data.conversation_id)
            return
          }
          for (const name of who) {
            if (!chat.participants.some((participant) => participant.username === name)) {
              chat.participants.push({ username: name, isAdmin: false, lastSeenLocal: 0 })
            }
          }
        }
        return
      }
      if (!chat) return
      if (child === "admins") {
        for (const name of asStringList(data.make_admin)) {
          const participant = chat.participants.find((entry) => entry.username === name)
          if (participant) participant.isAdmin = true
        }
        for (const name of asStringList(data.remove_admin)) {
          const participant = chat.participants.find((entry) => entry.username === name)
          if (participant) participant.isAdmin = false
        }
      } else if (child === "name" && typeof data.name === "string") {
        chat.name = data.name
      } else if (child === "description" && typeof data.description === "string") {
        chat.description = data.description
      } else if (child === "picture") {
        forgetIcon(domain, chat.pictureId)
        chat.pictureId = typeof data.picture_id === "string" ? data.picture_id : null
      } else if (child === "owner" && typeof data.owner === "string") {
        chat.creators = [data.owner]
      } else if (child === "seen" && typeof data.last_seen === "number") {
        const self = chat.participants.find((participant) => participant.username === username)
        if (self) self.lastSeenLocal = Math.max(self.lastSeenLocal, data.last_seen)
        if (current.value && username === current.value.username) {
          const key = `${domain}:${chat.id}`
          unreadCounts.value[key] = 0
          persistUnreadCounts()
          syncNativeUnreadCounts()
        }
      }
      return
    }
    if (root === "message" && !child && typeof data.chat_id === "string") {
      if (event.type === "create") addLiveMessage(domain, data.chat_id, data as unknown as MessageRaw)
      else if (event.type === "delete" && typeof data.message_id === "string") {
        const thread = threads.value[`${domain}:${data.chat_id}`]
        if (thread) thread.items = thread.items.filter((message) => message.id !== data.message_id)

        const key = `${domain}:${data.chat_id}`
        if (unreadCounts.value[key] && unreadCounts.value[key] > 0) {
          unreadCounts.value[key] = Math.max(0, unreadCounts.value[key] - 1)
          persistUnreadCounts()
          syncNativeUnreadCounts()
        }

        if (unreadSeparator.value && unreadSeparator.value.chatId === data.chat_id) {
          if (unreadSeparator.value.firstMessageId === data.message_id) {
            const me = current.value
            const chat = chats.value.find((c) => c.domain === domain && c.id === data.chat_id)
            const selfPart = chat?.participants.find((p) => p.username === me?.username)
            const lastSeen = selfPart?.lastSeenLocal ?? 0
            const nextUnread = thread?.items.find((m) => m.createdAt > lastSeen && m.sender !== me?.username)
            if (nextUnread) {
              unreadSeparator.value.firstMessageId = nextUnread.id
              unreadSeparator.value.count = Math.max(0, unreadSeparator.value.count - 1)
            } else {
              unreadSeparator.value = null
            }
          } else {
            unreadSeparator.value.count = Math.max(0, unreadSeparator.value.count - 1)
            if (unreadSeparator.value.count <= 0) {
              unreadSeparator.value = null
            }
          }
        }
      }
      return
    }
    if (root === "message" && child === "content" && event.type === "update" && typeof data.chat_id === "string" && typeof data.message_id === "string") {
      const thread = threads.value[`${domain}:${data.chat_id}`]
      const message = thread?.items.find((entry) => entry.id === data.message_id)
      if (message && typeof data.content === "string") {
        message.content = data.content
        message.edited = true
      }
    }
  }

  function addLiveMessage(domain: string, chatId: string, raw: MessageRaw) {
    const message = normalizeMessage(domain, chatId, { ...raw, chat_id: chatId })
    const thread = threads.value[`${domain}:${chatId}`]
    if (thread?.loaded && !thread.hasNewer && !thread.items.some((entry) => entry.id === message.id)) {
      thread.items.push(message)
      if (thread.items.length > WINDOW_LIMIT) {
        thread.items = thread.items.slice(thread.items.length - WINDOW_LIMIT)
        thread.hasMore = true
      }
    }
    const chat = chats.value.find((entry) => entry.domain === domain && entry.id === chatId)
    if (!chat) return
    chat.lastMessageAt = Math.max(chat.lastMessageAt, message.createdAt)
    const me = current.value
    const isChatOpen = selectedChatId.value !== null && pane.value === "chat"
    const isSameChat = isChatOpen && selectedChatId.value === chatId && me?.domain === domain
    const isForeground = typeof document !== "undefined" && !document.hidden

    const isActivelyReading = isSameChat && isForeground && document.hasFocus()
    if (isActivelyReading) {
      markRead(chat, me.username)
      clearNotificationBuffer(`${domain}:${chatId}`)
      if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearNotification) {
        try { (window as any).AndroidBridge.clearNotification(chatId) } catch {}
      }
      unreadCounts.value[`${domain}:${chatId}`] = 0
      persistUnreadCounts()
    } else {
      const key = `${domain}:${chatId}`
      unreadCounts.value[key] = (unreadCounts.value[key] ?? (unread(chat) ? 1 : 0)) + 1
      persistUnreadCounts()

      if (isSameChat && me && message.sender !== me.username) {
        if (!unreadSeparator.value || unreadSeparator.value.chatId !== chatId) {
          unreadSeparator.value = {
            chatId,
            firstMessageId: message.id,
            count: 1,
          }
        } else {
          unreadSeparator.value.count += 1
        }
      }

      // Notification policy:
      // Case #1 (Foreground & a chat selected): Chime + Push notification for other chats
      // Case #2 (Foreground & NO chat selected): Chime ONLY (no push notification)
      // Case #3 (Background/minimized): Chime (first msg) + Push notification
      if (me && message.sender !== me.username && !isMuted(chatId)) {
        const senderName = message.sender
        const chatTitle = displayName(chat)
        const text = message.content.trim() || (message.attachments.length > 0 ? "[Attachment]" : "Sent a message")

        const isAndroidBridge = typeof window !== "undefined" && Boolean((window as any).AndroidBridge)
        if (isAndroidBridge && !isForeground) {
          // Inside Android app: When minimized or backgrounded, OuiChatPushService handles all notifications and chime.
          // Exit early to prevent duplicate chime and sound overlapping.
          return
        }

        let shouldPushBanner = false
        if (isAndroidBridge) {
          // Inside Android app in foreground: only push banner for messages from other chats (Case #1)
          shouldPushBanner = isForeground && isChatOpen && selectedChatId.value !== chatId
        } else {
          // Standard desktop browser environment
          if (isForeground) {
            shouldPushBanner = isChatOpen && selectedChatId.value !== chatId
          } else {
            shouldPushBanner = true
          }
        }

        queueDesktopNotification({
          chatId,
          chatKey: `${domain}:${chatId}`,
          sender: senderName,
          chatTitle,
          isGroup: chat.type === "group",
          text,
          showPopup: shouldPushBanner,
          onClick: () => {
            void selectChat(chatId)
          },
        })
      }
    }
  }

  async function fetchChat(username: string, domain: string, chatId: string) {
    const session = findSession(username, domain)
    if (!session) return
    try {
      const details = await withSession(session, (active) => api.getChat(active.domain, active.accessToken, chatId))
      upsertChat(normalizeChat(domain, details.item))
    } catch (cause) {
      error.value = errorText(cause)
    }
  }

  function isMuted(chatId: string): boolean {
    const me = current.value
    if (!me || !me.mutedChats) return false
    return me.mutedChats.includes(chatId)
  }

  async function toggleMuteChat(chatId: string) {
    const me = requireCurrent()
    if (!me.mutedChats) me.mutedChats = []
    const currentlyMuted = me.mutedChats.includes(chatId)
    const next = !currentlyMuted
    await withSession(me, (session) => api.setMutedChat(session.domain, session.accessToken, chatId, next))
    if (next) {
      if (!me.mutedChats.includes(chatId)) me.mutedChats.push(chatId)
    } else {
      me.mutedChats = me.mutedChats.filter((id) => id !== chatId)
    }
    persist()
    syncNativeBridge(me)
  }

  function syncAllNativeSessions() {
    if (typeof window !== "undefined" && (window as any).AndroidBridge) {
      try {
        const payload = sessions.value.map((s) => ({
          username: s.username,
          domain: s.domain,
          accessToken: s.accessToken,
          refreshToken: s.refreshToken,
        }))
        if (typeof (window as any).AndroidBridge.syncSessions === "function") {
          (window as any).AndroidBridge.syncSessions(JSON.stringify(payload))
        } else if (payload[0] && typeof (window as any).AndroidBridge.onLoginSuccess === "function") {
          (window as any).AndroidBridge.onLoginSuccess(payload[0].domain, payload[0].username, payload[0].accessToken)
        }
        if (current.value && typeof (window as any).AndroidBridge.syncMutedChats === "function") {
          (window as any).AndroidBridge.syncMutedChats(JSON.stringify(current.value.mutedChats || []))
        }
      } catch (err) {
        console.error("[NativeBridge] sync error:", err)
      }
    }
  }

  function syncNativeBridge(_session?: Session) {
    syncAllNativeSessions()
  }

  function unreadBadge(chat: Chat): string | null {
    const key = `${chat.domain}:${chat.id}`
    const isChatUnread = unread(chat)
    if (!isChatUnread) {
      unreadCounts.value[key] = 0
      return null
    }
    const raw = unreadCounts.value[key]
    const count = (raw && raw > 0) ? raw : 1
    if (count > 9) return "9+"
    return String(count)
  }

  function deselectChat() {
    const me = current.value
    if (me && selectedChat.value) {
      markRead(selectedChat.value, me.username)
      unreadCounts.value[`${me.domain}:${selectedChat.value.id}`] = 0
      persistUnreadCounts()
    }
    selectedChatId.value = null
    unreadSeparator.value = null
    pane.value = "users"
  }

  async function init() {
    const savedUnread = getSavedItem(UNREAD_STORAGE_KEY)
    if (savedUnread) {
      try {
        unreadCounts.value = JSON.parse(savedUnread)
      } catch {}
    }

    const saved = getSavedItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Session[]
        sessions.value = parsed
          .filter((session) => session.username && session.domain && session.accessToken && session.refreshToken)
          .map((session) => ({
            ...session,
            blacklist: session.blacklist ?? [],
            mutedChats: session.mutedChats ?? [],
            reachable: session.reachable ?? [],
            status: session.status || "Hi there!",
            pictureId: session.pictureId ?? null,
          }))
      } catch {
        sessions.value = []
      }
    }
    const kept: Session[] = []
    for (const session of sessions.value) {
      try {
        await loadDomain(session, false)
        hub.connect(session.username, session.domain, session.accessToken)
        scheduleRefresh(session)
        kept.push(session)
      } catch (err) {
        console.warn("[OuiChat] Could not load domain on startup for", session.username, err)
        const ok = await recover(session, false)
        if (ok) {
          try {
            await loadDomain(session, false)
            hub.connect(session.username, session.domain, session.accessToken)
            scheduleRefresh(session)
            kept.push(session)
          } catch {
            logout(session.username, session.domain)
          }
        }
      }
    }
    sessions.value = kept
    const wanted = getSavedItem(CURRENT_KEY)
    const match = kept.find((session) => sessionKey(session.username, session.domain) === wanted)
    currentKey.value = match ? sessionKey(match.username, match.domain) : (kept[0] ? sessionKey(kept[0].username, kept[0].domain) : null)
    persist()
    const active = match ?? kept[0]
    if (active) {
      syncNativeBridge(active)
    }
    ready.value = true
    readyResolver?.()
    syncNativeUnreadCounts()

    if (typeof window !== "undefined" && (window as any).AndroidBridge?.consumePendingChatId) {
      const nativePending = (window as any).AndroidBridge.consumePendingChatId()
      if (nativePending) {
        pendingChatId.value = nativePending
      }
    }

    if (pendingChatId.value) {
      const target = pendingChatId.value
      pendingChatId.value = null
      void selectChat(target)
    }

    if (typeof window !== "undefined") {
      (window as any).selectChatFromNative = (chatId: string) => {
        void selectChat(chatId)
      }
      (window as any).markChatReadFromNative = (chatId: string) => {
        if (!current.value) return
        const key = `${current.value.domain}:${chatId}`
        unreadCounts.value[key] = 0
        if (unreadSeparator.value?.chatId === chatId) {
          unreadSeparator.value = null
        }
        const chat = chats.value.find((c) => c.domain === current.value!.domain && c.id === chatId)
        if (chat) {
          const self = chat.participants.find((p) => p.username === current.value!.username)
          if (self) self.lastSeenLocal = Math.max(self.lastSeenLocal, Date.now())
        }
        persistUnreadCounts()
        syncNativeUnreadCounts()
      }
    }
  }

  function onAppResumed() {
    syncNativeUnreadCounts()
    for (const session of sessions.value) {
      if (!accessTokenFresh(session.accessToken, REFRESH_LEAD_MS)) void recover(session, true)
    }
    const me = current.value
    if (me && selectedChat.value) {
      const chatId = selectedChat.value.id
      markRead(selectedChat.value, me.username)
      unreadCounts.value[`${me.domain}:${chatId}`] = 0
      persistUnreadCounts()
      if (typeof window !== "undefined" && (window as any).AndroidBridge?.clearNotification) {
        try { (window as any).AndroidBridge.clearNotification(chatId) } catch {}
      }
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return
    onAppResumed()
  })

  return {
    ready,
    waitForReady,
    sessions,
    current,
    visibleChats,
    directory,
    domainUsers,
    selectedChat,
    pane,
    sidebarTab,
    error,
    displayName,
    displayDescription,
    chatPicture,
    isWritable,
    isAdmin,
    isCreator,
    presenceOf,
    directChatId,
    unread,
    threadFor,
    userByName,
    pickerCandidates,
    removableMembers,
    resolveIcon,
    resolveAttachmentName,
    downloadAttachment,
    signIn,
    switchTo,
    logoutCurrent,
    selectChat,
    pendingChatId,
    showUsers,
    showDetails,
    showChat,
    markSelectedRead,
    unreadBadge,
    isMuted,
    toggleMuteChat,
    deselectChat,
    loadOlder,
    loadNewer,
    revealMessage,
    openDirect,
    createGroup,
    addMembers,
    removeMembers,
    leaveChatById,
    deleteChatById,
    setAdmin,
    renameChat,
    describeChat,
    changeChatIcon,
    blockUser,
    sendChatMessage,
    editChatMessage,
    deleteChatMessage,
    changeStatus,
    changeOwnIcon,
    unreadSeparator,
    isChatPaused,
    pauseChat,
    onAppResumed,
    init,
  }
})
