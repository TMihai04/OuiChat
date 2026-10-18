export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export function isLocalEnvironment(): boolean {
  const configured = import.meta.env.VITE_ENVIRONMENT
  if (configured === "production") return false
  if (configured === "local") return true
  return window.location.protocol !== "https:"
}

export function httpOrigin(domain: string): string {
  return `${isLocalEnvironment() ? "http" : "https"}://${domain}/api`
}

export function wsOrigin(domain: string): string {
  return `${isLocalEnvironment() ? "ws" : "wss"}://${domain}`
}

export interface RequestOptions {
  method?: string
  path: string
  query?: Record<string, string | number | null | undefined>
  json?: unknown
  form?: URLSearchParams
  body?: BodyInit | null
  headers?: Record<string, string>
  accessToken?: string
  expect?: "json" | "text" | "blob" | "empty"
}

export interface DownloadedFile {
  blob: Blob
  filename: string
}

export function filenameFromDisposition(header: string): string | null {
  const starred = /filename\*=utf-8''([^;]+)/i.exec(header)
  const quoted = /filename="([^"]*)"/i.exec(header)
  const plain = /(?:^|;)\s*filename=([^";\s]+)/i.exec(header)
  const raw = (starred?.[1] ?? quoted?.[1] ?? plain?.[1] ?? "").trim()
  if (!raw) return null
  try {
    return decodeURIComponent(raw).split(/[/\\]/).pop() || null
  } catch {
    return raw.split(/[/\\]/).pop() || null
  }
}

function detailMessage(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: unknown }).msg)
      }
      return ""
    }).filter(Boolean)
    if (parts.length) return parts.join(" ")
  }
  return "Something went wrong"
}

async function readError(response: Response): Promise<string> {
  try {
    const data = await response.json() as { detail?: unknown }
    return detailMessage(data.detail)
  } catch {
    return "Something went wrong"
  }
}

export async function request(domain: string, options: RequestOptions): Promise<unknown> {
  const url = new URL(`${httpOrigin(domain)}${options.path}`)
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const headers = new Headers(options.headers)
  if (options.accessToken) headers.set("Authorization", `Bearer ${options.accessToken}`)

  let body: BodyInit | null | undefined = options.body
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json")
    body = JSON.stringify(options.json)
  } else if (options.form) {
    headers.set("Content-Type", "application/x-www-form-urlencoded")
    body = options.form
  }

  let response: Response
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body,
    })
  } catch {
    throw new ApiError(0, "Cannot establish a connection with the server.")
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }

  if (options.expect === "empty" || response.status === 204) return null
  if (options.expect === "text") return response.text()
  if (options.expect === "blob") {
    const header = response.headers.get("Content-Disposition") ?? ""
    return {
      blob: await response.blob(),
      filename: filenameFromDisposition(header) ?? "download",
    } satisfies DownloadedFile
  }
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  return JSON.parse(text) as unknown
}

export function errorText(error: unknown): string {
  if (error instanceof Error && error.message) return error.message
  return "Something went wrong"
}
