const USERNAME_RE = /^[a-zA-Z\-_0-9]{4,64}$/
const SPECIALS = new Set([".", "_", "-", "!", "/", "+", "=", "*"])

export function validateUsername(username: string): string | null {
  if (username.length < 4 || username.length > 64) {
    return "Username must be between 4 and 64 characters long (inclusive)"
  }
  if (!USERNAME_RE.test(username)) {
    return "Username contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), hyphens (-), and underscores (_)"
  }
  return null
}

export function validatePassword(password: string): string | null {
  if (password.length < 8) return "Password must be at least 8 characters long"

  const counts = { lower: 0, upper: 0, digit: 0, special: 0 }
  for (const char of password) {
    if (/[a-z]/.test(char)) counts.lower += 1
    else if (/[A-Z]/.test(char)) counts.upper += 1
    else if (/[0-9]/.test(char)) counts.digit += 1
    else if (SPECIALS.has(char)) counts.special += 1
    else {
      return "Password contains invalid characters. It can contain lowercase letters (a-z), uppercase letters (A-Z), digits (0-9), and special characters (._-!/+=*)"
    }
  }
  if (counts.lower === 0 || counts.upper === 0 || counts.digit === 0 || counts.special === 0) {
    return "Password must contain at least one of: lowercase letter, uppercase letter, digit, special character"
  }
  return null
}
