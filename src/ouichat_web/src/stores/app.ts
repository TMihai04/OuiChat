import { computed, ref } from "vue"
import { defineStore } from "pinia"
import * as api from "../api/client"
import { ApiError, errorText } from "../api/http"
import type { ConversationRaw, MessageRaw, UserRaw, WsEvent } from "../api/types"
import { sessionKey } from "../format"
import { SocketHub } from "../ws/hub"

export const MAX_SESSIONS = 3
const MESSAGE_BATCH = 30
const STORAGE_KEY = "ouichat.sessions"
const CURRENT_KEY = "ouichat.current"
const REFRESH_LEAD_MS = 90_000

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
  loaded: boolean
  loading: boolean
}

interface ReloginJob {
  key: string
  resolve: (ok: boolean) => void
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
  const sessions = ref<Session[]>([])
  const currentKey = ref<string | null>(null)
  const domainUsers = ref<Record<string, DirUser[]>>({})
  const chats = ref<Chat[]>([])
  const threads = ref<Record<string, Thread>>({})
  const selectedChatId = ref<string | null>(null)
  const pane = ref<"users" | "chat" | "details">("users")
  const error = ref<string | null>(null)
  const relogin = ref<{ username: string; domain: string } | null>(null)

  const iconCache = new Map<string, string>()
  const iconJobs = new Map<string, Promise<string>>()
  const attachmentNames = new Map<string, string>()
  const attachmentNameJobs = new Map<string, Promise<string>>()
  const recoveries = new Map<string, Promise<boolean>>()
  const reloginQueue: ReloginJob[] = []

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
      reachable: [...session.reachable],
      status: session.status,
      pictureId: session.pictureId,
    }))
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
    sessionStorage.setItem(CURRENT_KEY, currentKey.value ?? "")
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
        lastSeenLocal: 0,
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
      if (old) participant.lastSeenLocal = old.lastSeenLocal
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
      threads.value[key] = { items: [], hasMore: true, loaded: false, loading: false }
    }
    return threads.value[key]
  }

  function markRead(chat: Chat, username: string) {
    const self = chat.participants.find((participant) => participant.username === username)
    if (!self) return
    self.lastSeenLocal = Math.max(self.lastSeenLocal, Date.now(), chat.lastMessageAt)
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
    const url = URL.createObjectURL(file.blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  }

  function pumpRelogin() {
    if (relogin.value || reloginQueue.length === 0) return
    const job = reloginQueue[0]
    const session = sessions.value.find((entry) => sessionKey(entry.username, entry.domain) === job.key)
    if (!session) {
      reloginQueue.shift()
      job.resolve(false)
      pumpRelogin()
      return
    }
    relogin.value = { username: session.username, domain: session.domain }
  }

  function askRelogin(session: Session): Promise<boolean> {
    const key = sessionKey(session.username, session.domain)
    const existing = reloginQueue.find((job) => job.key === key)
    if (existing) {
      return new Promise((resolve) => {
        const previous = existing.resolve
        existing.resolve = (ok) => {
          previous(ok)
          resolve(ok)
        }
      })
    }
    return new Promise((resolve) => {
      reloginQueue.push({ key, resolve })
      pumpRelogin()
    })
  }

  function settleRelogin(ok: boolean) {
    const job = reloginQueue.shift()
    relogin.value = null
    job?.resolve(ok)
    pumpRelogin()
  }

  async function submitRelogin(password: string) {
    if (!relogin.value) return
    const { username, domain } = relogin.value
    const tokens = await api.loginAccount(domain, username, password)
    const session = findSession(username, domain)
    if (!session) {
      settleRelogin(false)
      return
    }
    session.accessToken = tokens.access_token
    session.refreshToken = tokens.refresh_token
    hub.updateToken(username, domain, session.accessToken)
    persist()
    settleRelogin(true)
  }

  function cancelRelogin() {
    const target = relogin.value
    settleRelogin(false)
    if (target) logout(target.username, target.domain)
  }

  async function recover(session: Session, interactive: boolean): Promise<boolean> {
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
        scheduleRefresh(session)
        return true
      } catch {
        if (!interactive) return false
        const ok = await askRelogin(session)
        const live = findSession(session.username, session.domain)
        if (ok && live) scheduleRefresh(live)
        return ok
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
  }

  async function signIn(domain: string, username: string, password: string, register: boolean) {
    const cleanDomain = domain.trim()
    const cleanUsername = username.trim()
    if (!cleanDomain) throw new Error("Domain must not be empty")
    if (!cleanUsername) throw new Error("Username must not be empty")
    if (!password) throw new Error("Password must not be empty")
    if (sessions.value.length >= MAX_SESSIONS) throw new Error("You can only be signed in to 3 accounts")
    if (findSession(cleanUsername, cleanDomain)) throw new Error("Username already logged in")
    if (register) await api.registerAccount(cleanDomain, cleanUsername, password)

    const tokens = await api.loginAccount(cleanDomain, cleanUsername, password)
    const me = await api.getMe(cleanDomain, tokens.access_token)
    const session: Session = {
      username: me.item.username || cleanUsername,
      domain: cleanDomain,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      blacklist: me.item.preferences?.blacklist ?? [],
      reachable: [],
      status: me.item.profile?.status || "Hi there!",
      pictureId: me.item.profile?.picture_id || null,
    }
    const previousKey = currentKey.value
    sessions.value.push(session)
    currentKey.value = sessionKey(session.username, session.domain)
    selectedChatId.value = null
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
  }

  async function switchTo(username: string, domain: string) {
    const session = findSession(username, domain)
    if (!session) return
    if (current.value && selectedChat.value) markRead(selectedChat.value, current.value.username)
    currentKey.value = sessionKey(username, domain)
    selectedChatId.value = null
    pane.value = "users"
    persist()
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
    persist()
  }

  function logoutCurrent() {
    const me = current.value
    if (!me) return
    logout(me.username, me.domain)
  }

  async function selectChat(chatId: string) {
    const me = requireCurrent()
    const chat = chats.value.find((entry) => entry.domain === me.domain && entry.id === chatId)
    if (!chat) return
    if (selectedChat.value) markRead(selectedChat.value, me.username)
    selectedChatId.value = chatId
    pane.value = "chat"
    markRead(chat, me.username)
    await ensureMessages(chat, null)
    markRead(chat, me.username)
  }

  function showUsers() {
    const me = current.value
    if (me && selectedChat.value) markRead(selectedChat.value, me.username)
    selectedChatId.value = null
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
  }

  async function ensureMessages(chat: Chat, beforeId: string | null) {
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
        MESSAGE_BATCH,
      ))
      const incoming = raw.map((message) => normalizeMessage(chat.domain, chat.id, message))
      if (!beforeId) {
        thread.items = incoming
      } else {
        const known = new Set(thread.items.map((message) => message.id))
        const older = incoming.filter((message) => message.id !== beforeId && !known.has(message.id))
        thread.items = [...older, ...thread.items]
      }
      thread.hasMore = raw.length >= MESSAGE_BATCH
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

  async function openDirect(username: string) {
    const me = requireCurrent()
    if (username === me.username) return
    if (me.blacklist.includes(username)) return
    const existing = directChatId(me.username, username, me.domain)
    if (existing) {
      await selectChat(existing)
      return
    }
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

  async function sendChatMessage(text: string, files: File[], repliedTo: string | null) {
    const me = requireCurrent()
    const chat = selectedChat.value
    if (!chat) return
    const uploaded: string[] = []
    let uploadError: string | null = null
    for (const file of files) {
      try {
        const fileId = await withSession(me, (session) => api.uploadFile(session.domain, session.accessToken, file, "attachment"))
        attachmentNames.set(`${me.domain}:${fileId}`, file.name)
        uploaded.push(fileId)
      } catch (cause) {
        uploadError = errorText(cause)
        break
      }
    }
    if (uploadError && !text && uploaded.length === 0) throw new Error(uploadError)
    const body: { content?: string; attachments?: string[]; replied_to?: string } = {}
    if (text) body.content = text
    if (uploaded.length) body.attachments = uploaded
    if (repliedTo) body.replied_to = repliedTo
    await withSession(me, (session) => api.sendMessage(session.domain, session.accessToken, chat.id, body))
    if (uploadError) error.value = uploadError
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
      } else if (child === "status" && typeof data.username === "string" && typeof data.status === "string") {
        const user = userByName(domain, data.username)
        if (user) user.status = data.status
        const session = findSession(data.username, domain)
        if (session) session.status = data.status
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
      }
      return
    }
    if (root === "message" && !child && typeof data.chat_id === "string") {
      if (event.type === "create") addLiveMessage(domain, data.chat_id, data as unknown as MessageRaw)
      else if (event.type === "delete" && typeof data.message_id === "string") {
        const thread = threads.value[`${domain}:${data.chat_id}`]
        if (thread) thread.items = thread.items.filter((message) => message.id !== data.message_id)
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
    if (thread?.loaded && !thread.items.some((entry) => entry.id === message.id)) thread.items.push(message)
    const chat = chats.value.find((entry) => entry.domain === domain && entry.id === chatId)
    if (!chat) return
    chat.lastMessageAt = Math.max(chat.lastMessageAt, message.createdAt)
    const me = current.value
    if (me && selectedChatId.value === chatId && me.domain === domain && pane.value === "chat") {
      markRead(chat, me.username)
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

  async function init() {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Session[]
        sessions.value = parsed
          .filter((session) => session.username && session.domain && session.accessToken && session.refreshToken)
          .map((session) => ({
            ...session,
            blacklist: session.blacklist ?? [],
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
      } catch {
        hub.disconnect(session.username, session.domain)
      }
    }
    sessions.value = kept
    const wanted = sessionStorage.getItem(CURRENT_KEY)
    const match = kept.find((session) => sessionKey(session.username, session.domain) === wanted)
    currentKey.value = match ? sessionKey(match.username, match.domain) : (kept[0] ? sessionKey(kept[0].username, kept[0].domain) : null)
    persist()
    ready.value = true
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return
    for (const session of sessions.value) {
      if (!accessTokenFresh(session.accessToken, REFRESH_LEAD_MS)) void recover(session, true)
    }
  })

  return {
    ready,
    sessions,
    current,
    visibleChats,
    directory,
    domainUsers,
    selectedChat,
    pane,
    error,
    relogin,
    displayName,
    displayDescription,
    chatPicture,
    isWritable,
    isAdmin,
    isCreator,
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
    showUsers,
    showDetails,
    showChat,
    markSelectedRead,
    loadOlder,
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
    submitRelogin,
    cancelRelogin,
    init,
  }
})
