<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { getSavedThemeMode, isNativeBridgeAvailable, setThemeMode, type ThemeMode } from "../theme"
import {
  getNotificationPermission,
  isNotificationBannerDismissed,
  isNotificationSupported,
  isNotificationsGloballyEnabled,
  playNotificationChime,
  requestNotificationPermission,
  resetNotificationBanner,
  setNotificationsGloballyEnabled,
} from "../notifications"

const router = useRouter()
const isNative = computed(() => isNativeBridgeAvailable())
const currentMode = ref<ThemeMode>(getSavedThemeMode())

function chooseTheme(mode: ThemeMode) {
  if (mode === "auto" && !isNative.value) return
  currentMode.value = mode
  setThemeMode(mode)
}

const notifPermission = ref(getNotificationPermission())
const notifEnabled = ref(isNotificationsGloballyEnabled())
const bannerDismissed = ref(isNotificationBannerDismissed())

function refreshNotifState() {
  const perm = getNotificationPermission()
  notifPermission.value = perm
  bannerDismissed.value = isNotificationBannerDismissed()
  if (perm === "denied") {
    notifEnabled.value = false
    setNotificationsGloballyEnabled(false)
  } else {
    notifEnabled.value = isNotificationsGloballyEnabled()
  }
}

const notifPermissionLabel = computed(() => {
  if (notifPermission.value === "denied") {
    return isNative.value
      ? "Permission blocked in Android system settings"
      : "Permission blocked in browser site settings"
  }
  if (notifPermission.value === "default") {
    return "Permission not requested"
  }
  if (!isNotificationSupported()) {
    return "Not supported in this environment"
  }
  return isNative.value ? "Active in Android app" : "Allowed by browser"
})

async function toggleNotifs(enabled: boolean) {
  if (enabled && notifPermission.value === "denied") {
    await requestPermissionDirectly()
    refreshNotifState()
    return
  }
  if (enabled && notifPermission.value === "default") {
    const perm = await requestNotificationPermission()
    notifPermission.value = perm
    if (perm === "denied") {
      notifEnabled.value = false
      setNotificationsGloballyEnabled(false)
      return
    }
  }
  notifEnabled.value = enabled
  setNotificationsGloballyEnabled(enabled)
}

async function requestPermissionDirectly() {
  const perm = await requestNotificationPermission()
  notifPermission.value = perm
  bannerDismissed.value = isNotificationBannerDismissed()
  if (perm === "granted") {
    notifEnabled.value = true
    setNotificationsGloballyEnabled(true)
  } else if (perm === "denied") {
    notifEnabled.value = false
    setNotificationsGloballyEnabled(false)
  }
}

function restoreBannerPrompt() {
  resetNotificationBanner()
  bannerDismissed.value = false
}

function testSound() {
  playNotificationChime(true)
}

onMounted(() => {
  refreshNotifState()
  if (typeof window !== "undefined") {
    ;(window as any).onNotificationPermissionChanged = () => {
      refreshNotifState()
    }
    window.addEventListener("focus", refreshNotifState)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    if ((window as any).onNotificationPermissionChanged) {
      delete (window as any).onNotificationPermissionChanged
    }
    window.removeEventListener("focus", refreshNotifState)
  }
})
</script>

<template>
  <div class="settings-page">
    <div class="settings-header">
      <button class="settings-back-btn" type="button" title="Back to Chat" @click="router.push('/app')">
        <img src="/icons/left_arrow_icon.png" width="18" height="18" alt="" />
      </button>
      <h2 class="settings-title">Settings</h2>
    </div>

    <div class="settings-container">
      <section class="settings-card">
        <h3 class="card-title">Appearance & Theme</h3>
        <p class="card-subtitle">Choose how OuiChat looks on your device.</p>

        <div class="theme-options">
          <label class="theme-option" :class="{ selected: currentMode === 'dark' }">
            <input
              type="radio"
              name="theme"
              value="dark"
              :checked="currentMode === 'dark'"
              @change="chooseTheme('dark')"
            />
            <div class="option-details">
              <span class="option-title">Dark Mode</span>
              <span class="option-desc">Permanent dark palette (default)</span>
            </div>
          </label>

          <label class="theme-option" :class="{ selected: currentMode === 'light' }">
            <input
              type="radio"
              name="theme"
              value="light"
              :checked="currentMode === 'light'"
              @change="chooseTheme('light')"
            />
            <div class="option-details">
              <span class="option-title">Light Mode</span>
              <span class="option-desc">Permanent clean, bright palette</span>
            </div>
          </label>

          <label class="theme-option" :class="{ selected: currentMode === 'system' }">
            <input
              type="radio"
              name="theme"
              value="system"
              :checked="currentMode === 'system'"
              @change="chooseTheme('system')"
            />
            <div class="option-details">
              <span class="option-title">System Default</span>
              <span class="option-desc">Matches your OS day/night settings</span>
            </div>
          </label>

          <label
            class="theme-option"
            :class="{ selected: currentMode === 'auto', disabled: !isNative }"
          >
            <input
              type="radio"
              name="theme"
              value="auto"
              :disabled="!isNative"
              :checked="currentMode === 'auto'"
              @change="chooseTheme('auto')"
            />
            <div class="option-details">
              <div class="title-with-badge">
                <span class="option-title">Dynamic</span>
                <span v-if="!isNative" class="phone-only-tag">Phone App Only</span>
              </div>
              <span class="option-desc">
                {{ isNative ? 'Adapts automatically using your phone\'s ambient light sensor' : 'Disabled in browser (available in OuiChat Android app)' }}
              </span>
            </div>
          </label>
        </div>
      </section>

      <section class="settings-card" style="margin-top: 16px;">
        <h3 class="card-title">Notifications</h3>
        <p class="card-subtitle">Web alerts and sound when messages arrive.</p>

        <div class="notif-box">
          <div class="selection-bar notif-toggle-bar">
            <button
              type="button"
              class="selection-tab"
              :class="{ active: notifEnabled && notifPermission === 'granted' }"
              @click="toggleNotifs(true)"
            >
              Enabled
            </button>
            <button
              type="button"
              class="selection-tab"
              :class="{ active: !notifEnabled || notifPermission !== 'granted' }"
              @click="toggleNotifs(false)"
            >
              Disabled
            </button>
          </div>

          <div class="notif-meta-row">
            <span class="notif-status-info">
              Status: {{ (notifEnabled && notifPermission === 'granted') ? notifPermissionLabel : (notifPermission === 'denied' ? notifPermissionLabel : 'Disabled in OuiChat settings') }}
            </span>
            <button
              type="button"
              class="mid-button"
              @click="testSound"
            >
              Test Sound
            </button>
          </div>

          <div class="notif-actions-row">
            <button
              v-if="notifPermission !== 'granted'"
              type="button"
              class="mid-button notif-enable-btn"
              @click="requestPermissionDirectly"
            >
              {{ isNative ? "Enable Notification Permission (Android Settings)" : "Request Browser Permission" }}
            </button>
            <button
              v-if="bannerDismissed && !isNative"
              type="button"
              class="mid-button"
              @click="restoreBannerPrompt"
            >
              Restore Banner Prompt
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 4px 16px;
  border-bottom: 1px solid var(--line-soft);
}

.settings-back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  padding: 0;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--button);
  cursor: pointer;
  flex: none;
}

.settings-back-btn:hover {
  background: var(--accent);
}

.settings-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.settings-container {
  max-width: 600px;
  margin: 20px auto 0;
}

.settings-card {
  background: var(--panel);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  padding: 20px;
}

.card-title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
}

.card-subtitle {
  margin: 0 0 16px;
  font-size: 13px;
  opacity: 0.8;
}

.theme-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.theme-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: var(--panel-deep);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.theme-option:hover:not(.disabled) {
  border-color: var(--accent);
}

.theme-option.selected {
  border-color: var(--accent);
  background: var(--raised);
}

.theme-option.disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.theme-option input[type="radio"] {
  margin-top: 3px;
  accent-color: var(--accent);
}

.option-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-title {
  font-weight: 600;
  font-size: 14px;
}

.phone-only-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--button);
  color: inherit;
  border: 1px solid var(--line);
}

.option-desc {
  font-size: 12px;
  opacity: 0.75;
}
.notif-box {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.notif-toggle-bar {
  max-width: 260px;
}

.notif-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.notif-status-info {
  font-size: 13px;
  opacity: 0.75;
}

.notif-actions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 4px;
}
</style>
