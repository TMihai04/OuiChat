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
            .remove(KEY_UNREAD_COUNTS)
            .remove(KEY_MUTED)
            .apply()
        Log.i(TAG, "All sessions cleared from secure preferences")
    }

    fun setActiveUser(context: Context, userKey: String) {
        getPrefs(context).edit().putString(KEY_ACTIVE_USER, userKey).apply()
    }

    fun getActiveUser(context: Context): String? {
        return getPrefs(context).getString(KEY_ACTIVE_USER, null)
    }

    fun saveMutedChats(context: Context, userKey: String, mutedChats: Set<String>) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_MUTED, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val array = JSONArray()
            mutedChats.forEach { array.put(it) }
            root.put(userKey, array)
            getPrefs(context).edit().putString(KEY_MUTED, root.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error saving muted chats for $userKey", e)
        }
    }

    fun getMutedChats(context: Context, userKey: String): Set<String> {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_MUTED, "{}") ?: "{}"
            val root = JSONObject(jsonStr)
            val array = root.optJSONArray(userKey) ?: return emptySet()
            val set = mutableSetOf<String>()
            for (i in 0 until array.length()) {
                set.add(array.getString(i))
            }
            set
        } catch (e: Exception) {
            emptySet()
        }
    }

    fun saveAllMutedChats(context: Context, jsonMapString: String) {
        try {
            val incoming = JSONObject(jsonMapString)
            val jsonStr = getPrefs(context).getString(KEY_MUTED, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val keys = incoming.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                root.put(k, incoming.getJSONArray(k))
            }
            getPrefs(context).edit().putString(KEY_MUTED, root.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error saving all muted chats", e)
        }
    }

    fun saveMutedChats(context: Context, jsonArrayString: String) {
        val active = getActiveUser(context) ?: "default"
        try {
            val array = JSONArray(jsonArrayString)
            val set = mutableSetOf<String>()
            for (i in 0 until array.length()) {
                set.add(array.getString(i))
            }
            saveMutedChats(context, active, set)
        } catch (e: Exception) {
            Log.e(TAG, "Error in legacy saveMutedChats", e)
        }
    }

    fun getMutedChats(context: Context): Set<String> {
        val active = getActiveUser(context) ?: "default"
        return getMutedChats(context, active)
    }

    fun saveThemeMode(context: Context, mode: String) {
        getPrefs(context).edit().putString(KEY_THEME, mode).apply()
    }

    fun getThemeMode(context: Context): String {
        return getPrefs(context).getString(KEY_THEME, "system") ?: "system"
    }

    @Synchronized
    fun incrementUnreadCount(context: Context, userKey: String, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val userObj = root.optJSONObject(userKey) ?: JSONObject()
            val current = userObj.optInt(chatId, 0)
            userObj.put(chatId, current + 1)
            root.put(userKey, userObj)
            getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, root.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error incrementing unread count for $userKey:$chatId", e)
        }
    }

    @Synchronized
    fun decrementUnreadCount(context: Context, userKey: String, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val userObj = root.optJSONObject(userKey) ?: return
            val current = userObj.optInt(chatId, 0)
            if (current <= 1) {
                userObj.remove(chatId)
            } else {
                userObj.put(chatId, current - 1)
            }
            root.put(userKey, userObj)
            getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, root.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Error decrementing unread count for $userKey:$chatId", e)
        }
    }

    @Synchronized
    fun clearUnreadCount(context: Context, userKey: String, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val userObj = root.optJSONObject(userKey) ?: return
            if (userObj.has(chatId)) {
                userObj.remove(chatId)
                root.put(userKey, userObj)
                getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, root.toString()).apply()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error clearing unread count for $userKey:$chatId", e)
        }
    }

    @Synchronized
    fun clearAllUnreadCountsForUser(context: Context, userKey: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            if (root.has(userKey)) {
                root.remove(userKey)
                getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, root.toString()).apply()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error clearing all unread counts for $userKey", e)
        }
    }

    fun getUnreadCountForUser(context: Context, userKey: String, chatId: String): Int {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = JSONObject(jsonStr)
            val userObj = root.optJSONObject(userKey) ?: return 0
            userObj.optInt(chatId, 0)
        } catch (_: Exception) {
            0
        }
    }

    fun getTotalUnreadCountForUser(context: Context, userKey: String): Int {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = JSONObject(jsonStr)
            val userObj = root.optJSONObject(userKey) ?: return 0
            var sum = 0
            val keys = userObj.keys()
            while (keys.hasNext()) {
                sum += userObj.optInt(keys.next(), 0)
            }
            sum
        } catch (_: Exception) {
            0
        }
    }

    fun getTotalUnreadCount(context: Context): Int {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = JSONObject(jsonStr)
            var totalSum = 0
            val userKeys = root.keys()
            while (userKeys.hasNext()) {
                val uKey = userKeys.next()
                val userObj = root.optJSONObject(uKey)
                if (userObj != null) {
                    val chatKeys = userObj.keys()
                    while (chatKeys.hasNext()) {
                        totalSum += userObj.optInt(chatKeys.next(), 0)
                    }
                } else {
                    totalSum += root.optInt(uKey, 0)
                }
            }
            totalSum
        } catch (_: Exception) {
            0
        }
    }

    fun getUnreadCountsJsonForUser(context: Context, userKey: String): String {
        return try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = JSONObject(jsonStr)
            val userObj = root.optJSONObject(userKey) ?: JSONObject()
            userObj.toString()
        } catch (_: Exception) {
            "{}"
        }
    }

    @Synchronized
    fun incrementUnreadCount(context: Context, chatId: String) {
        val userKey = getActiveUser(context) ?: "default"
        incrementUnreadCount(context, userKey, chatId)
    }

    @Synchronized
    fun decrementUnreadCount(context: Context, chatId: String) {
        val userKey = getActiveUser(context) ?: "default"
        decrementUnreadCount(context, userKey, chatId)
    }

    @Synchronized
    fun clearUnreadCount(context: Context, chatId: String) {
        try {
            val jsonStr = getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
            val root = try { JSONObject(jsonStr) } catch (_: Exception) { JSONObject() }
            val userKeys = root.keys()
            var modified = false
            while (userKeys.hasNext()) {
                val uKey = userKeys.next()
                val userObj = root.optJSONObject(uKey)
                if (userObj != null && userObj.has(chatId)) {
                    userObj.remove(chatId)
                    modified = true
                }
            }
            if (root.has(chatId)) {
                root.remove(chatId)
                modified = true
            }
            if (modified) {
                getPrefs(context).edit().putString(KEY_UNREAD_COUNTS, root.toString()).apply()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in legacy clearUnreadCount", e)
        }
    }

    fun getUnreadCountsJson(context: Context): String {
        val active = getActiveUser(context)
        return if (active != null) {
            getUnreadCountsJsonForUser(context, active)
        } else {
            getPrefs(context).getString(KEY_UNREAD_COUNTS, "{}") ?: "{}"
        }
    }

    fun getUnreadCount(context: Context, chatId: String): Int {
        val active = getActiveUser(context)
        return if (active != null) {
            getUnreadCountForUser(context, active, chatId)
        } else {
            0
        }
    }
}
