package com.example.ouichatandroid.bridge

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.SoundPool
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.webkit.JavascriptInterface
import android.widget.Toast
import androidx.core.content.ContextCompat
import com.example.ouichatandroid.R
import com.example.ouichatandroid.sensor.LightSensorManager
import com.example.ouichatandroid.service.OuiChatPushService
import com.example.ouichatandroid.util.NotificationHelper
import com.example.ouichatandroid.util.PreferenceManager
import com.example.ouichatandroid.util.UserSession
import java.io.File
import java.io.FileOutputStream
import org.json.JSONArray

class AndroidBridge(
    private val context: Context,
    private val lightSensorManager: LightSensorManager
) {
    companion object {
        private const val TAG = "AndroidBridge"
    }

    private val soundPool: SoundPool
    private var chimeSoundId: Int = 0
    private val mainHandler = Handler(Looper.getMainLooper())

    @Volatile
    var pendingChatId: String? = null

    init {
        val audioAttributes = AudioAttributes.Builder()
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .build()

        soundPool = SoundPool.Builder()
            .setMaxStreams(3)
            .setAudioAttributes(audioAttributes)
            .build()

        chimeSoundId = soundPool.load(context, R.raw.ouichat_chime, 1)
    }

    @JavascriptInterface
    fun syncSessions(jsonArrayString: String) {
        try {
            val array = JSONArray(jsonArrayString)
            val list = mutableListOf<UserSession>()
            for (i in 0 until array.length()) {
                val obj = array.getJSONObject(i)
                val username = obj.optString("username")
                val domain = obj.optString("domain")
                val accessToken = obj.optString("accessToken")
                val refreshToken = obj.optString("refreshToken")
                if (username.isNotBlank() && domain.isNotBlank()) {
                    list.add(UserSession(username, domain, accessToken, refreshToken))
                }
            }

            PreferenceManager.saveSessions(context, list)
            Log.i(TAG, "syncSessions: Saved ${list.size} session(s)")

            if (list.isNotEmpty()) {
                mainHandler.post {
                    val serviceIntent = Intent(context.applicationContext, OuiChatPushService::class.java).apply {
                        action = OuiChatPushService.ACTION_START
                    }
                    try {
                        ContextCompat.startForegroundService(context.applicationContext, serviceIntent)
                        Log.i(TAG, "Started OuiChatPushService for ${list.size} user(s)")
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to start foreground service", e)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in syncSessions", e)
        }
    }

    @JavascriptInterface
    fun onLoginSuccess(domain: String, username: String, token: String) {
        try {
            val sessions = PreferenceManager.getSessions(context).toMutableList()
            val index = sessions.indexOfFirst { it.username == username && it.domain == domain }
            if (index != -1) {
                sessions[index] = UserSession(username, domain, token, sessions[index].refreshToken)
            } else {
                sessions.add(UserSession(username, domain, token, ""))
            }
            PreferenceManager.saveSessions(context, sessions)

            mainHandler.post {
                val serviceIntent = Intent(context.applicationContext, OuiChatPushService::class.java).apply {
                    action = OuiChatPushService.ACTION_START
                }
                try {
                    ContextCompat.startForegroundService(context.applicationContext, serviceIntent)
                } catch (e: Exception) {
                    Log.e(TAG, "Error starting foreground service: ${e.message}", e)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in onLoginSuccess", e)
        }
    }

    @JavascriptInterface
    fun onLogout() {
        try {
            PreferenceManager.clearAllSessions(context)

            mainHandler.post {
                val serviceIntent = Intent(context.applicationContext, OuiChatPushService::class.java).apply {
                    action = OuiChatPushService.ACTION_STOP
                }
                try {
                    context.applicationContext.stopService(serviceIntent)
                    Log.i(TAG, "Stopped OuiChatPushService on logout")
                } catch (e: Exception) {
                    Log.e(TAG, "Error stopping service on logout", e)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in onLogout", e)
        }
    }

    @JavascriptInterface
    fun consumePendingChatId(): String? {
        val id = pendingChatId
        pendingChatId = null
        return id
    }

    @JavascriptInterface
    fun getUnreadCounts(): String {
        return PreferenceManager.getUnreadCountsJson(context)
    }

    @JavascriptInterface
    fun clearUnreadCount(chatId: String) {
        PreferenceManager.clearUnreadCount(context, chatId)
    }

    @JavascriptInterface
    fun showNotification(chatId: String, sender: String, content: String, groupTitle: String?, isGroup: Boolean) {
        mainHandler.post {
            NotificationHelper.showMessageNotification(
                context = context.applicationContext,
                chatId = chatId,
                sender = sender,
                content = content,
                groupTitle = if (groupTitle.isNullOrBlank()) null else groupTitle,
                isGroup = isGroup
            )
        }
    }

    @JavascriptInterface
    fun showNotification(chatId: String, sender: String, content: String, groupTitle: String?) {
        showNotification(chatId, sender, content, groupTitle, !groupTitle.isNullOrBlank())
    }

    @JavascriptInterface
    fun clearNotification(chatId: String) {
        PreferenceManager.clearUnreadCount(context, chatId)
        mainHandler.post {
            NotificationHelper.cancelMessageNotification(context.applicationContext, chatId)
        }
    }

    @JavascriptInterface
    fun syncMutedChats(jsonArrayString: String) {
        PreferenceManager.saveMutedChats(context, jsonArrayString)
    }

    @JavascriptInterface
    fun onThemeModeConfigured(mode: String) {
        PreferenceManager.saveThemeMode(context, mode)
        lightSensorManager.setAutoModeEnabled(mode == "auto")
    }

    @JavascriptInterface
    fun onThemeModeChanged(mode: String) {
        onThemeModeConfigured(mode)
    }

    @JavascriptInterface
    fun isDynamicSensorSupported(): Boolean {
        return lightSensorManager.isSensorAvailable()
    }

    @JavascriptInterface
    fun playChime() {
        try {
            if (chimeSoundId != 0) {
                soundPool.play(chimeSoundId, 1f, 1f, 1, 0, 1f)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error playing chime", e)
        }
    }

    @JavascriptInterface
    fun vibrate(durationMs: Long) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
                val vibrator = vibratorManager.defaultVibrator
                vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
                } else {
                    vibrator.vibrate(durationMs)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error triggering vibration", e)
        }
    }

    @JavascriptInterface
    fun saveBlob(base64Data: String, mimeType: String, fileName: String): Boolean {
        return try {
            val cleanBase64 = if (base64Data.contains(",")) {
                base64Data.substringAfter(",")
            } else {
                base64Data
            }
            val bytes = Base64.decode(cleanBase64, Base64.DEFAULT)
            val cleanMime = if (mimeType.isBlank()) "application/octet-stream" else mimeType
            val cleanName = if (fileName.isBlank()) "download" else fileName

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, cleanName)
                    put(MediaStore.MediaColumns.MIME_TYPE, cleanMime)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                if (uri != null) {
                    context.contentResolver.openOutputStream(uri)?.use { os ->
                        os.write(bytes)
                        os.flush()
                    }
                } else {
                    throw IllegalStateException("Failed to create download record in MediaStore")
                }
            } else {
                @Suppress("DEPRECATION")
                val dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                if (!dir.exists()) dir.mkdirs()
                val targetFile = File(dir, cleanName)
                FileOutputStream(targetFile).use { fos ->
                    fos.write(bytes)
                    fos.flush()
                }
            }

            mainHandler.post {
                Toast.makeText(context, "Saved to Downloads: $cleanName", Toast.LENGTH_LONG).show()
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "Error saving file: ${e.message}", e)
            mainHandler.post {
                Toast.makeText(context, "Failed to download $fileName: ${e.message}", Toast.LENGTH_LONG).show()
            }
            false
        }
    }
}
