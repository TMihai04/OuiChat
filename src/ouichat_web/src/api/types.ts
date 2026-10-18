export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type?: string
}

export interface UserProfileRaw {
  status?: string
  picture_id?: string | null
}

export interface UserRaw {
  username: string
  profile?: UserProfileRaw
  preferences?: { blacklist?: string[] }
}

export interface ParticipantRaw {
  username: string
  is_admin: boolean
  last_seen?: number | null
}

export interface ConversationRaw {
  conversation_id: string
  type: "direct" | "group"
  profile?: {
    name?: string | null
    description?: string | null
    picture_id?: string | null
  }
  preferences?: {
    participants?: ParticipantRaw[]
    created_by?: string[]
  }
}

export interface MessageRaw {
  message_id: string
  sender: string
  content?: string | null
  attachments?: string[]
  replied_to?: string | null
  created_at: number
  updated_at: number
  chat_id?: string
}

export interface ItemResponse<T> {
  item: T
}

export interface ItemsResponse<T> {
  items: T[]
}

export interface WsEvent {
  event_id: string
  type: "create" | "update" | "delete" | "system"
  scope: string
  data: Record<string, unknown>
}
