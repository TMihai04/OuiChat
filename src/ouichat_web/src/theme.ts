export type ThemeMode = "light" | "dark" | "system" | "auto"

const THEME_KEY = "ouichat.theme"

export function isNativeBridgeAvailable(): boolean {
  return typeof window !== "undefined" && !!(window as any).AndroidBridge
}

export function getSavedThemeMode(): ThemeMode {
  if (typeof window === "undefined") return "dark"
  const saved = localStorage.getItem(THEME_KEY) as ThemeMode | null
  if (saved === "light" || saved === "dark" || saved === "system" || saved === "auto") {
    if (saved === "auto" && !isNativeBridgeAvailable()) return "system"
    return saved
  }
  return "dark"
}

export function applyTheme(resolvedTheme: "light" | "dark") {
  if (typeof document === "undefined") return
  document.documentElement.setAttribute("data-theme", resolvedTheme)
}

export function setThemeMode(mode: ThemeMode) {
  if (typeof window === "undefined") return
  localStorage.setItem(THEME_KEY, mode)

  if (isNativeBridgeAvailable()) {
    try {
      (window as any).AndroidBridge.onThemeModeChanged(mode)
    } catch {}
  }

  if (mode === "dark") {
    applyTheme("dark")
  } else if (mode === "light") {
    applyTheme("light")
  } else if (mode === "system") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    applyTheme(prefersDark ? "dark" : "light")
  } else if (mode === "auto") {
    // Sensor mode: wait for native bridge or default to dark
    applyTheme("dark")
  }
}

export function initTheme() {
  if (typeof window === "undefined") return

  // Global hook for Kotlin evaluateJavascript: window.applyTheme('dark' | 'light')
  ;(window as any).applyTheme = (theme: "light" | "dark") => {
    applyTheme(theme)
  }

  const currentMode = getSavedThemeMode()
  setThemeMode(currentMode)

  // Listen for system changes if mode is system
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
  mediaQuery.addEventListener("change", (e) => {
    if (getSavedThemeMode() === "system") {
      applyTheme(e.matches ? "dark" : "light")
    }
  })
}
