export function formatTime(ms: number): string {
  const date = new Date(ms)
  const minutes = String(date.getMinutes()).padStart(2, "0")
  const suffix = date.getHours() >= 12 ? "PM" : "AM"
  const hours = String(date.getHours() % 12 || 12).padStart(2, "0")
  return `${hours}:${minutes} ${suffix}`
}

function dayStamp(ms: number): string {
  const date = new Date(ms)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

export function formatDay(ms: number): string {
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  const key = dayStamp(ms)
  if (key === dayStamp(today.getTime())) return "Today"
  if (key === dayStamp(yesterday.getTime())) return "Yesterday"
  return new Date(ms).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
}

export function sessionKey(username: string, domain: string): string {
  return `${username}@${domain}`
}
