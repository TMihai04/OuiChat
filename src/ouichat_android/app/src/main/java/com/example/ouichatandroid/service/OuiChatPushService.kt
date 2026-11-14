package com.example.ouichatandroid.service

import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.Log
import com.example.ouichatandroid.util.AvatarManager
import com.example.ouichatandroid.util.DeviceUtils
import com.example.ouichatandroid.util.NotificationHelper
import com.example.ouichatandroid.util.PreferenceManager
import com.example.ouichatandroid.util.UserSession
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

class OuiChatPushService : Service() {

    companion object {
        private const val TAG = "OuiChatPushService"
        const val ACTION_START = "com.example.ouichatandroid.action.START"
        const val ACTION_STOP = "com.example.ouichatandroid.action.STOP"
        const val ACTION_MARK_AS_READ = "com.example.ouichatandroid.action.MARK_AS_READ"
        const val ACTION_RESTORE_NOTIFICATION = "com.example.ouichatandroid.action.RESTORE_NOTIFICATION"

        @Volatile
        var isAppInForeground: Boolean = false
    }

    private var client: OkHttpClient? = null
    private val activeSockets = ConcurrentHashMap<String, WebSocket>()
    private val retryCounts = ConcurrentHashMap<String, Int>()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var isDestroyed = false

    override fun onCreate() {
        super.onCreate()
        client = OkHttpClient.Builder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .pingInterval(30, TimeUnit.SECONDS)
            .build()
        Log.i(TAG, "Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_RESTORE_NOTIFICATION) {
            Log.i(TAG, "Persistent notification was dismissed; immediately restoring it")
            val count = PreferenceManager.getSessions(this).size.coerceAtLeast(1)
            updateNotificationStatus(count)
            return START_STICKY
        }

        if (intent?.action == ACTION_MARK_AS_READ) {
            val chatId = intent.getStringExtra("chat_id")
            val recipientUser = intent.getStringExtra("recipient_user")
            if (!chatId.isNullOrBlank()) {
                Log.i(TAG, "Marking chat as read from notification: $chatId")
                NotificationHelper.cancelMessageNotification(this, chatId)
                PreferenceManager.clearUnreadCount(this, chatId)
                com.example.ouichatandroid.MainActivity.activeInstance?.markChatReadInWebView(chatId)
                markChatSeenInBackground(chatId, recipientUser)
            }
            return START_NOT_STICKY
        }

        if (intent?.action == ACTION_STOP) {
            Log.i(TAG, "Received ACTION_STOP, stopping foreground service")
            val closeApp = intent.getBooleanExtra("close_app", false)
            stopForegroundService()
            if (closeApp) {
                val exitIntent = Intent(applicationContext, com.example.ouichatandroid.MainActivity::class.java).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                    putExtra("action_exit", true)
                }
                startActivity(exitIntent)
            }
            return START_NOT_STICKY
        }

        val sessions = PreferenceManager.getSessions(this)
        if (sessions.isEmpty()) {
            Log.i(TAG, "No logged-in sessions found, stopping service")
            stopForegroundService()
            return START_NOT_STICKY
        }

        // Start ongoing foreground service notification
        try {
            val notification = NotificationHelper.buildServiceNotification(this, sessions.size)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(
                    NotificationHelper.SERVICE_NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
                )
            } else {
                startForeground(
                    NotificationHelper.SERVICE_NOTIFICATION_ID,
                    notification
                )
            }
            Log.i(TAG, "startForeground initialized with ${sessions.size} account(s)")
        } catch (e: Exception) {
            Log.e(TAG, "Error starting foreground service: ${e.message}", e)
        }

        syncSockets()
        return START_STICKY
    }

    private fun syncSockets() {
        if (isDestroyed) return
        val sessions = PreferenceManager.getSessions(this)
        val sessionKeys = sessions.map { "${it.username}@${it.domain}" }.toSet()

        // Disconnect sockets for removed accounts
        val currentKeys = activeSockets.keys().toList()
        for (key in currentKeys) {
            if (!sessionKeys.contains(key)) {
                Log.i(TAG, "Disconnecting socket for removed account $key")
                activeSockets[key]?.cancel()
                activeSockets.remove(key)
                retryCounts.remove(key)
            }
        }

        // Connect or maintain sockets for active sessions
        for (session in sessions) {
            val key = "${session.username}@${session.domain}"
            if (!activeSockets.containsKey(key)) {
                connectWebSocket(session)
            }
        }

        updateNotificationStatus(sessions.size)
    }

    private fun updateNotificationStatus(count: Int) {
        try {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.notify(
                NotificationHelper.SERVICE_NOTIFICATION_ID,
                NotificationHelper.buildServiceNotification(this, count)
            )
        } catch (e: Exception) {
            Log.e(TAG, "Error updating status notification", e)
        }
    }

    private fun connectWebSocket(session: UserSession) {
        if (isDestroyed) return
        val key = "${session.username}@${session.domain}"

        val target = DeviceUtils.parseDomainTarget(session.domain)
        val encodedToken = try {
            URLEncoder.encode(session.accessToken, "UTF-8")
        } catch (_: Exception) {
            session.accessToken
        }
        val wsUrl = "${target.wsUrl}/ws/global?token=$encodedToken&presence=false"

        Log.i(TAG, "Connecting WebSocket for $key to $wsUrl")
        val request = Request.Builder().url(wsUrl).build()

        activeSockets[key]?.cancel()
        val socket = client?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "WebSocket connected successfully for $key")
                retryCounts[key] = 0
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleWebSocketMessage(session, text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                handleWebSocketMessage(session, bytes.utf8())
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                val statusCode = response?.code
                Log.w(TAG, "WebSocket failure for $key: code=$statusCode, error=${t.message}")
                activeSockets.remove(key)

                if (statusCode == 401 || statusCode == 403 || t.message?.contains("401") == true) {
                    Log.i(TAG, "Authorization error on $key, attempting background token refresh")
                    refreshTokensInBackground(session)
                } else {
                    scheduleReconnect(session)
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WebSocket closed for $key: code=$code, reason=$reason")
                activeSockets.remove(key)
                if (code == 4001 || code == 401) {
                    refreshTokensInBackground(session)
                } else {
                    scheduleReconnect(session)
                }
            }
        })

        if (socket != null) {
            activeSockets[key] = socket
        }
    }

    private fun handleWebSocketMessage(session: UserSession, payload: String) {
        try {
            val json = JSONObject(payload)
            val type = json.optString("type")
            val scope = json.optString("scope")
            val data = json.optJSONObject("data") ?: return

            val parts = scope.split(".")
            val root = parts.getOrNull(0) ?: ""
            val child = parts.getOrNull(1)

            // Handle server-side mute update event
            if (root == "user" && type == "update" && child == "muted_chats") {
                val chatId = data.optString("chat_id")
                val isMuted = data.optBoolean("is_muted", false)
                val currentMuted = PreferenceManager.getMutedChats(this).toMutableSet()
                if (isMuted) currentMuted.add(chatId) else currentMuted.remove(chatId)
                PreferenceManager.saveMutedChats(this, org.json.JSONArray(currentMuted).toString())
                return
            }

            // Handle message edit
            if (root == "message" && child == "content" && type == "update") {
                val chatId = data.optString("chat_id")
                val messageId = data.optString("message_id")
                val newContent = data.optString("content")
                if (chatId.isNotBlank() && messageId.isNotBlank()) {
                    mainHandler.post {
                        NotificationHelper.updateMessageContent(applicationContext, chatId, messageId, newContent)
                    }
                }
                return
            }

            // Handle message delete (Option B - clean style)
            if (root == "message" && child == null && type == "delete") {
                val chatId = data.optString("chat_id")
                val messageId = data.optString("message_id")
                if (chatId.isNotBlank() && messageId.isNotBlank()) {
                    mainHandler.post {
                        val allCleared = NotificationHelper.deleteMessage(applicationContext, chatId, messageId)
                        if (allCleared) {
                            PreferenceManager.clearUnreadCount(applicationContext, chatId)
                        } else {
                            PreferenceManager.decrementUnreadCount(applicationContext, chatId)
                        }
                    }
                }
                return
            }

            // Handle conversation delete
            if (root == "conversation" && child == null && type == "delete") {
                val chatId = data.optString("conversation_id")
                if (chatId.isNotBlank()) {
                    PreferenceManager.clearUnreadCount(applicationContext, chatId)
                    mainHandler.post {
                        NotificationHelper.cancelMessageNotification(applicationContext, chatId)
                    }
                }
                return
            }

            // Handle conversation name update
            if (root == "conversation" && child == "name" && type == "update") {
                val chatId = data.optString("conversation_id")
                val newName = data.optString("name")
                if (chatId.isNotBlank() && newName.isNotBlank()) {
                    mainHandler.post {
                        NotificationHelper.updateChatName(applicationContext, chatId, newName)
                    }
                }
                return
            }

            // Handle conversation picture update
            if (root == "conversation" && child == "picture" && type == "update") {
                val chatId = data.optString("conversation_id")
                val pictureId = data.optString("picture_id").takeIf { it.isNotBlank() && it != "null" }
                if (chatId.isNotBlank() && pictureId != null) {
                    AvatarManager.fetchAvatar(applicationContext, session, pictureId) { bitmap ->
                        NotificationHelper.updateNotificationIcon(applicationContext, chatId, bitmap)
                    }
                }
                return
            }

            // Handle user picture update (for direct chats)
            if (root == "user" && child == "picture" && type == "update") {
                val username = data.optString("username")
                val pictureId = data.optString("picture_id").takeIf { it.isNotBlank() && it != "null" }
                if (username.isNotBlank() && pictureId != null) {
                    AvatarManager.fetchAvatar(applicationContext, session, pictureId) { bitmap ->
                        NotificationHelper.updateUserAvatar(applicationContext, username, pictureId, bitmap)
                    }
                }
                return
            }

            // Handle incoming message event
            if (root == "message" && child == null && type == "create") {
                val chatId = data.optString("chat_id")
                val messageId = data.optString("message_id")
                val sender = data.optString("sender")
                val chatType = data.optString("chat_type")
                val isGroup = chatType == "group"
                val rawChatName = if (data.isNull("chat_name")) null else data.optString("chat_name")
                val groupTitle = if (!rawChatName.isNullOrBlank() && rawChatName != "null") rawChatName else null
                val pictureId = if (data.isNull("chat_picture_id")) null else data.optString("chat_picture_id").takeIf { it.isNotBlank() && it != "null" }
                val senderPictureId = if (data.isNull("sender_picture_id")) null else data.optString("sender_picture_id").takeIf { it.isNotBlank() && it != "null" }

                // Skip own messages
                if (sender == session.username) return

                // Increment background unread count
                PreferenceManager.incrementUnreadCount(this, chatId)

                // Check if chat is muted
                val muted = PreferenceManager.getMutedChats(this)
                if (muted.contains(chatId)) {
                    Log.d(TAG, "Message from muted chat $chatId suppressed for ${session.username}")
                    return
                }

                // If app is currently in foreground, skip the system notification card
                if (isAppInForeground) {
                    Log.d(TAG, "App is in foreground - skipping system heads-up notification")
                    return
                }

                val content = data.optString("content").trim().ifEmpty {
                    val attachments = data.optJSONArray("attachments")
                    if (attachments != null && attachments.length() > 0) "[Attachment]" else "Sent a message"
                }

                val totalSessions = PreferenceManager.getSessions(this).size
                val recipientTag = if (totalSessions > 1) session.username else null

                mainHandler.post {
                    NotificationHelper.showMessageNotification(
                        context = applicationContext,
                        chatId = chatId,
                        sender = sender,
                        content = content,
                        messageId = messageId,
                        groupTitle = groupTitle,
                        isGroup = isGroup,
                        pictureId = pictureId,
                        senderPictureId = senderPictureId,
                        recipientUser = recipientTag
                    )

                    if (pictureId != null) {
                        AvatarManager.fetchAvatar(applicationContext, session, pictureId) { bitmap ->
                            NotificationHelper.updateNotificationIcon(applicationContext, chatId, bitmap)
                        }
                    }

                    if (senderPictureId != null) {
                        AvatarManager.fetchAvatar(applicationContext, session, senderPictureId) { _ ->
                            NotificationHelper.updateSenderAvatar(applicationContext, chatId)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error handling message for ${session.username}", e)
        }
    }

    private fun markChatSeenInBackground(chatId: String, recipientUser: String?) {
        val sessions = PreferenceManager.getSessions(this)
        val session = if (!recipientUser.isNullOrBlank()) {
            sessions.find { it.username == recipientUser } ?: sessions.firstOrNull()
        } else {
            sessions.firstOrNull()
        } ?: return

        val target = DeviceUtils.parseDomainTarget(session.domain)
        val url = "${target.httpUrl}/api/chats/participant/seen?chat_id=$chatId"

        val emptyBody = "".toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer ${session.accessToken}")
            .post(emptyBody)
            .build()

        client?.newCall(request)?.enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.w(TAG, "Failed to mark chat $chatId seen on backend: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (response.isSuccessful) {
                        Log.i(TAG, "Chat $chatId successfully marked seen on backend")
                    } else {
                        Log.w(TAG, "Mark seen returned HTTP ${response.code} for $chatId")
                    }
                }
            }
        })
    }

    private fun refreshTokensInBackground(session: UserSession) {
        if (isDestroyed || session.refreshToken.isBlank()) return
        val key = "${session.username}@${session.domain}"
        Log.i(TAG, "Refreshing token in background for $key")

        val target = DeviceUtils.parseDomainTarget(session.domain)
        val refreshUrl = "${target.httpUrl}/api/refresh"

        val emptyBody = "".toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(refreshUrl)
            .post(emptyBody)
            .header("Authorization", "Bearer ${session.refreshToken}")
            .build()

        client?.newCall(request)?.enqueue(object : okhttp3.Callback {
            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                Log.e(TAG, "Background refresh failed for $key: ${e.message}")
                scheduleReconnect(session)
            }

            override fun onResponse(call: okhttp3.Call, response: Response) {
                response.use {
                    if (response.isSuccessful) {
                        val body = response.body?.string() ?: ""
                        try {
                            val json = JSONObject(body)
                            val newAccess = json.getString("access_token")
                            val newRefresh = json.optString("refresh_token", session.refreshToken)

                            PreferenceManager.updateTokens(
                                this@OuiChatPushService,
                                session.username,
                                session.domain,
                                newAccess,
                                newRefresh
                            )
                            Log.i(TAG, "Successfully refreshed tokens in background for $key")
                            val updatedSession = UserSession(session.username, session.domain, newAccess, newRefresh)
                            connectWebSocket(updatedSession)
                        } catch (e: Exception) {
                            Log.e(TAG, "Failed parsing refresh response for $key", e)
                        }
                    } else {
                        Log.w(TAG, "Refresh endpoint returned status ${response.code} for $key")
                        scheduleReconnect(session)
                    }
                }
            }
        })
    }

    private fun scheduleReconnect(session: UserSession) {
        if (isDestroyed) return
        val key = "${session.username}@${session.domain}"
        val currentRetries = retryCounts[key] ?: 0
        val nextRetry = (currentRetries + 1).coerceAtMost(6)
        retryCounts[key] = nextRetry

        val delayMs = (1000L * (1 shl nextRetry)).coerceAtMost(30_000L)
        Log.i(TAG, "Scheduling reconnect for $key in ${delayMs}ms (attempt $nextRetry)")

        mainHandler.postDelayed({
            if (!isDestroyed && !activeSockets.containsKey(key)) {
                val currentSessions = PreferenceManager.getSessions(this)
                val liveSession = currentSessions.find { it.username == session.username && it.domain == session.domain }
                if (liveSession != null) {
                    connectWebSocket(liveSession)
                }
            }
        }, delayMs)
    }

    private fun stopForegroundService() {
        isDestroyed = true
        for ((_, socket) in activeSockets) {
            socket.cancel()
        }
        activeSockets.clear()
        retryCounts.clear()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        isAppInForeground = false
        Log.i(TAG, "Task removed - OuiChatPushService continues listening in background for ${activeSockets.size} account(s)")
    }

    override fun onDestroy() {
        super.onDestroy()
        isDestroyed = true
        for ((_, socket) in activeSockets) {
            socket.cancel()
        }
        activeSockets.clear()
        retryCounts.clear()
        Log.i(TAG, "OuiChatPushService destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
