package com.example.ouichatandroid.util

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.json.JSONArray
import org.json.JSONObject

data class UserSession(
    val username: String,
    val domain: String,
    val accessToken: String,
    val refreshToken: String
)

object PreferenceManager {
    private const val TAG = "PreferenceManager"
    private const val SECURE_PREFS_NAME = "ouichat_secure_prefs"
    private const val FALLBACK_PREFS_NAME = "ouichat_prefs"

    private const val KEY_SESSIONS = "user_sessions_json"
    private const val KEY_ACTIVE_USER = "active_user_key"
    private const val KEY_MUTED = "muted_chats"
    private const val KEY_THEME = "theme_mode"
    private const val KEY_UNREAD_COUNTS = "ouichat_unread_counts"

    @Volatile
    private var prefsInstance: SharedPreferences? = null

    private fun getPrefs(context: Context): SharedPreferences {
        prefsInstance?.let { return it }
        synchronized(this) {
            prefsInstance?.let { return it }
            val prefs = createEncryptedPrefs(context) ?: context.getSharedPreferences(FALLBACK_PREFS_NAME, Context.MODE_PRIVATE)
            prefsInstance = prefs
            return prefs
        }
    }

    private fun createEncryptedPrefs(context: Context): SharedPreferences? {
        return try {
            val masterKey = MasterKey.Builder(context.applicationContext)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            EncryptedSharedPreferences.create(
                context.applicationContext,
                SECURE_PREFS_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize EncryptedSharedPreferences, falling back to private prefs", e)
            null
        }
    }

    fun saveSessions(context: Context, sessions: List<UserSession>) {
        val array = JSONArray()
        for (session in sessions) {
            val obj = JSONObject().apply {
                put("username", session.username)
                put("domain", session.domain)
                put("accessToken", session.accessToken)
                put("refreshToken", session.refreshToken)
            }
            array.put(obj)
        }
        getPrefs(context).edit().putString(KEY_SESSIONS, array.toString()).apply()
        Log.i(TAG, "Saved ${sessions.size} user session(s) securely")
    }

    fun getSessions(context: Context): List<UserSession> {
        val raw = getPrefs(context).getString(KEY_SESSIONS, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            val list = mutableListOf<UserSession>()
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                list.add(
                    UserSession(
                        username = obj.optString("username"),
                        domain = obj.optString("domain"),
                        accessToken = obj.optString("accessToken"),
                        refreshToken = obj.optString("refreshToken")
                    )
                )
            }
            list
        } catch (e: Exception) {
            Log.e(TAG, "Error deserializing user sessions", e)
            emptyList()
        }
    }

    fun updateTokens(context: Context, username: String, domain: String, accessToken: String, refreshToken: String) {
        val sessions = getSessions(context).toMutableList()
        val index = sessions.indexOfFirst { it.username == username && it.domain == domain }
        if (index != -1) {
            sessions[index] = UserSession(username, domain, accessToken, refreshToken)
            saveSessions(context, sessions)
            Log.i(TAG, "Updated tokens for $username@$domain")
        }
    }

    fun clearAllSessions(context: Context) {
        getPrefs(context).edit()
            .remove(KEY_SESSIONS)
            .remove(KEY_ACTIVE_USER)
            .apply()
        Log.i(TAG, "All sessions cleared from secure preferences")
    }

    fun setActiveUser(context: Context, userKey: String) {
        getPrefs(context).edit().putString(KEY_ACTIVE_USER, userKey).apply()
    }

    fun getActiveUser(context: Context): String? {
        return getPrefs(context).getString(KEY_ACTIVE_USER, null)
    }

    fun saveMutedChats(context: Context, jsonArrayString: String) {
        try {
            val array = JSONArray(jsonArrayString)
            val set = mutableSetOf<String>()
            for (i in 0 until array.length()) {
                set.add(array.getString(i))
            }
            getPrefs(context).edit().putStringSet(KEY_MUTED, set).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error saving muted chats", e)
        }
    }

    fun getMutedChats(context: Context): Set<String> {
        return getPrefs(context).getStringSet(KEY_MUTED, emptySet()) ?: emptySet()
    }

    fun saveThemeMode(context: Context, mode: String) {
        getPrefs(context).edit().putString(KEY_THEME, mode).apply()
    }

    fun getThemeMode(context: Context): String {
        return getPrefs(context).getString(KEY_THEME, "system") ?: "system"
    }

    @Synchronized
    fun incrementUnreadCount(context: Context, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val obj = org.json.JSONObject(jsonStr)
            val current = obj.optInt(chatId, 0)
            obj.put(chatId, current + 1)
            getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, obj.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error incrementing unread count for $chatId", e)
        }
    }

    @Synchronized
    fun decrementUnreadCount(context: Context, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val obj = org.json.JSONObject(jsonStr)
            val current = obj.optInt(chatId, 0)
            if (current <= 1) {
                obj.remove(chatId)
            } else {
                obj.put(chatId, current - 1)
            }
            getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, obj.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error decrementing unread count for $chatId", e)
        }
    }

    @Synchronized
    fun clearUnreadCount(context: Context, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val obj = org.json.JSONObject(jsonStr)
            if (obj.has(chatId)) {
                obj.remove(chatId)
                getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, obj.toString()).apply()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error clearing unread count for $chatId", e)
        }
    }

    fun getUnreadCountsJson(context: Context): String {
        return getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
    }

    fun getUnreadCount(context: Context, chatId: String): Int {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val obj = org.json.JSONObject(jsonStr)
            obj.optInt(chatId, 0)
        } catch (_: Exception) {
            0
        }
    }
}
