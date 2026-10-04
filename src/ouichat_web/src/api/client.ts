import type {
  ConversationRaw,
  ItemResponse,
  ItemsResponse,
  MessageRaw,
  TokenPair,
  UserRaw,
} from "./types"
import { ApiError, httpOrigin, request, type DownloadedFile } from "./http"

function formBody(username: string, password: string): URLSearchParams {
  const body = new URLSearchParams()
  body.set("grant_type", "password")
  body.set("username", username)
  body.set("password", password)
  return body
}

export function registerAccount(domain: string, username: string, password: string) {
  return request(domain, {
    method: "POST",
    path: "/register",
    form: formBody(username, password),
  })
}

export function loginAccount(domain: string, username: string, password: string) {
  return request(domain, {
    method: "POST",
    path: "/login",
    form: formBody(username, password),
  }) as Promise<TokenPair>
}

export function refreshTokens(domain: string, refreshToken: string) {
  return request(domain, {
    method: "POST",
    path: "/refresh",
    accessToken: refreshToken,
    expect: "json",
  }) as Promise<TokenPair>
}

export function getMe(domain: string, accessToken: string) {
  return request(domain, {
    path: "/users/me",
    accessToken,
  }) as Promise<ItemResponse<UserRaw>>
}

export function listUsers(domain: string, accessToken: string) {
  return request(domain, {
    path: "/users/list",
    accessToken,
  }) as Promise<ItemResponse<{ white?: UserRaw[]; black?: UserRaw[] }>>
}

export function setStatus(domain: string, accessToken: string, status: string) {
  return request(domain, {
    method: "POST",
    path: "/users/profile/status",
    accessToken,
    json: { status },
  })
}

export function setUserPicture(domain: string, accessToken: string, iconId: string) {
  return request(domain, {
    method: "POST",
    path: "/users/profile/picture",
    accessToken,
    json: { icon_id: iconId },
  })
}

export function setBlacklist(domain: string, accessToken: string, username: string, block: boolean) {
  return request(domain, {
    method: block ? "POST" : "DELETE",
    path: "/users/preferences/blacklist",
    accessToken,
    json: { who: username },
    expect: block ? "json" : "empty",
  })
}

export function listChats(domain: string, accessToken: string) {
  return request(domain, {
    path: "/chats/list",
    accessToken,
  }) as Promise<ItemsResponse<ConversationRaw>>
}

export function getChat(domain: string, accessToken: string, chatId: string) {
  return request(domain, {
    path: "/chats/chat",
    accessToken,
    query: { chat_id: chatId },
  }) as Promise<ItemResponse<ConversationRaw>>
}

export function createChat(
  domain: string,
  accessToken: string,
  body: {
    type: "direct" | "group"
    group?: { name: string; description: string; picture_id: string | null }
    participants: Record<string, boolean>
  },
) {
  return request(domain, {
    method: "POST",
    path: "/chats/create",
    accessToken,
    json: body,
  }) as Promise<ItemResponse<{ conversation_id: string }>>
}

export function setAdmins(
  domain: string,
  accessToken: string,
  chatId: string,
  admins: Record<string, boolean>,
) {
  return request(domain, {
    method: "POST",
    path: "/chats/participant/admin",
    accessToken,
    query: { chat_id: chatId },
    json: { admins },
  })
}

export function changeMembers(
  domain: string,
  accessToken: string,
  chatId: string,
  usernames: string[],
  add: boolean,
) {
  return request(domain, {
    method: add ? "POST" : "DELETE",
    path: add ? "/chats/participant/add" : "/chats/participant/remove",
    accessToken,
    query: { chat_id: chatId },
    json: { who: usernames },
    expect: "json",
  })
}

export function leaveChat(domain: string, accessToken: string, chatId: string) {
  return request(domain, {
    method: "DELETE",
    path: "/chats/participant/leave",
    accessToken,
    query: { chat_id: chatId },
    expect: "empty",
  })
}

export function setChatField(
  domain: string,
  accessToken: string,
  chatId: string,
  field: "name" | "description" | "picture",
  body: Record<string, string>,
) {
  return request(domain, {
    method: "POST",
    path: `/chats/preferences/${field}`,
    accessToken,
    query: { chat_id: chatId },
    json: body,
  })
}

export function sendMessage(
  domain: string,
  accessToken: string,
  chatId: string,
  body: { content?: string; attachments?: string[]; replied_to?: string },
) {
  return request(domain, {
    method: "POST",
    path: "/messages/send",
    accessToken,
    query: { chat_id: chatId },
    json: body,
  })
}

export function editMessage(
  domain: string,
  accessToken: string,
  chatId: string,
  messageId: string,
  newContent: string,
) {
  return request(domain, {
    method: "POST",
    path: "/messages/edit",
    accessToken,
    query: { chat_id: chatId },
    json: { message_id: messageId, new_content: newContent },
  })
}

export function deleteMessage(
  domain: string,
  accessToken: string,
  chatId: string,
  messageId: string,
) {
  return request(domain, {
    method: "DELETE",
    path: "/messages/delete",
    accessToken,
    query: { chat_id: chatId },
    json: { message_id: messageId },
    expect: "empty",
  })
}

export async function listMessages(
  domain: string,
  accessToken: string,
  chatId: string,
  direction: "old" | "mixed" | "new",
  messageId: string | null,
  batchSize: number,
) {
  const text = await request(domain, {
    path: "/messages/list",
    accessToken,
    query: {
      chat_id: chatId,
      direction,
      message_id: messageId,
      batch_size: batchSize,
    },
    expect: "text",
  }) as string

  const messages: MessageRaw[] = []
  for (const line of text.split("\n")) {
    const trimmed = line.trim()
    if (!trimmed.startsWith("data:")) continue
    const payload = trimmed.slice("data:".length).trim()
    if (!payload) continue
    messages.push(JSON.parse(payload) as MessageRaw)
  }
  return messages
}

export async function uploadFile(
  domain: string,
  accessToken: string,
  file: File,
  fileType: "attachment" | "icon",
) {
  const bytes = await file.arrayBuffer()
  const response = await request(domain, {
    method: "POST",
    path: "/attachments/upload",
    accessToken,
    query: { file_type: fileType },
    body: bytes,
    headers: {
      "Content-Type": "application/octet-stream",
      "X-Original-Filename": file.name || "unknown_file",
    },
  }) as ItemResponse<{ file_id: string }>
  return response.item.file_id
}

export function downloadFile(domain: string, accessToken: string, fileId: string) {
  return request(domain, {
    path: "/attachments/download",
    accessToken,
    query: { file_id: fileId },
    expect: "blob",
  }) as Promise<DownloadedFile>
}

export async function attachmentFileName(domain: string, accessToken: string, fileId: string) {
  const url = new URL(`${httpOrigin(domain)}/attachments/download`)
  url.searchParams.set("file_id", fileId)
  let response: Response
  try {
    response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Range: "bytes=0-0",
      },
    })
  } catch {
    throw new ApiError(0, "Cannot establish a connection with the server.")
  }
  const header = response.headers.get("Content-Disposition") ?? ""
  await response.body?.cancel()
  if (response.status === 401) throw new ApiError(401, "Unauthorized")
  if (!response.ok && response.status !== 206) throw new ApiError(response.status, "Could not read the file name.")
  const match = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i.exec(header)
  const encoded = match?.[1] ?? match?.[2] ?? ""
  try {
    return decodeURIComponent(encoded) || fileId
  } catch {
    return encoded || fileId
  }
}
