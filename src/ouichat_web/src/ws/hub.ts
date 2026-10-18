import { wsOrigin } from "../api/http"
import type { WsEvent } from "../api/types"

const MAX_RETRIES = 3
const MAX_SEEN = 512

export interface FreshToken {
  token: string
  refreshed: boolean
}

export interface SocketHandlers {
  onEvent: (username: string, domain: string, event: WsEvent) => void
  onDead: (username: string, domain: string) => void
  ensureToken: (username: string, domain: string) => Promise<FreshToken | null>
}

interface Connection {
  username: string
  domain: string
  accessToken: string
  socket: WebSocket | null
  stopped: boolean
  attempt: number
  timer: number | null
}

function sessionKey(username: string, domain: string): string {
  return `${username}@${domain}`
}

export class SocketHub {
  private connections = new Map<string, Connection>()
  private seen: string[] = []

  constructor(private handlers: SocketHandlers) {}

  connect(username: string, domain: string, accessToken: string) {
    this.disconnect(username, domain)
    const connection: Connection = {
      username,
      domain,
      accessToken,
      socket: null,
      stopped: false,
      attempt: 0,
      timer: null,
    }
    this.connections.set(sessionKey(username, domain), connection)
    this.open(connection)
  }

  updateToken(username: string, domain: string, accessToken: string) {
    const connection = this.connections.get(sessionKey(username, domain))
    if (!connection) return
    connection.accessToken = accessToken
    if (connection.socket && connection.socket.readyState === WebSocket.OPEN) {
      const payload = new TextEncoder().encode(JSON.stringify({ access_token: accessToken }))
      connection.socket.send(payload)
    }
  }

  disconnect(username: string, domain: string) {
    const connection = this.connections.get(sessionKey(username, domain))
    if (!connection) return
    connection.stopped = true
    if (connection.timer !== null) window.clearTimeout(connection.timer)
    connection.socket?.close()
    this.connections.delete(sessionKey(username, domain))
  }

  private open(connection: Connection) {
    const url = `${wsOrigin(connection.domain)}/ws/global?token=${encodeURIComponent(connection.accessToken)}`
    const socket = new WebSocket(url)
    socket.binaryType = "arraybuffer"
    connection.socket = socket

    socket.onopen = () => {
      connection.attempt = 0
    }

    socket.onmessage = (event) => {
      void this.takeMessage(connection, event.data)
    }

    socket.onclose = () => {
      if (connection.stopped || connection.socket !== socket) return
      connection.attempt += 1
      if (connection.attempt >= MAX_RETRIES) {
        this.fail(connection)
        return
      }
      connection.timer = window.setTimeout(() => {
        void this.reopen(connection)
      }, 2000 * connection.attempt)
    }
  }

  private async reopen(connection: Connection) {
    if (connection.stopped) return
    let fresh: FreshToken | null = null
    try {
      fresh = await this.handlers.ensureToken(connection.username, connection.domain)
    } catch {
      fresh = null
    }
    if (connection.stopped) return
    if (!fresh) {
      this.fail(connection)
      return
    }
    connection.accessToken = fresh.token
    if (fresh.refreshed) connection.attempt = 0
    this.open(connection)
  }

  private fail(connection: Connection) {
    if (connection.stopped) return
    connection.stopped = true
    if (connection.timer !== null) window.clearTimeout(connection.timer)
    connection.timer = null
    this.connections.delete(sessionKey(connection.username, connection.domain))
    this.handlers.onDead(connection.username, connection.domain)
  }

  private async takeMessage(connection: Connection, data: unknown) {
    let text = ""
    if (typeof data === "string") text = data
    else if (data instanceof ArrayBuffer) text = new TextDecoder().decode(data)
    else if (data instanceof Blob) text = await data.text()
    else return

    let event: WsEvent
    try {
      event = JSON.parse(text) as WsEvent
    } catch {
      return
    }
    if (!event.event_id || this.seen.includes(event.event_id)) return
    this.seen.push(event.event_id)
    if (this.seen.length > MAX_SEEN) this.seen.shift()
    this.handlers.onEvent(connection.username, connection.domain, event)
  }
}
