export function formatTime(ms: number): string {
  const date = new Date(ms)
  const minutes = String(date.getMinutes()).padStart(2, "0")
  const suffix = date.getHours() >= 12 ? "PM" : "AM"
  const hours = String(date.getHours() % 12 || 12).padStart(2, "0")
  return `${hours}:${minutes} ${suffix}`
}

export function sessionKey(username: string, domain: string): string {
  return `${username}@${domain}`
}
