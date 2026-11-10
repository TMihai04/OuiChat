package com.example.ouichatandroid.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.BitmapShader
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.Shader
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.util.LruCache
import com.example.ouichatandroid.R
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.concurrent.TimeUnit

object AvatarManager {
    private const val TAG = "AvatarManager"
    private const val AVATARS_DIR = "avatars"

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val memoryCache = object : LruCache<String, Bitmap>(50) {
        override fun sizeOf(key: String, value: Bitmap): Int = 1
    }

    private val mainHandler = Handler(Looper.getMainLooper())

    private fun getAvatarDir(context: Context): File {
        val dir = File(context.cacheDir, AVATARS_DIR)
        if (!dir.exists()) {
            dir.mkdirs()
        }
        return dir
    }

    fun getCircularBitmap(bitmap: Bitmap): Bitmap {
        val size = minOf(bitmap.width, bitmap.height)
        val output = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(output)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        val shader = BitmapShader(bitmap, Shader.TileMode.CLAMP, Shader.TileMode.CLAMP)
        paint.shader = shader
        val radius = size / 2f
        canvas.drawCircle(radius, radius, radius, paint)
        return output
    }

    fun getDefaultAvatar(context: Context, isGroup: Boolean, size: Int = 192): Bitmap {
        val cacheKey = if (isGroup) "default_group" else "default_user"
        memoryCache.get(cacheKey)?.let { return it }

        val resId = if (isGroup) R.drawable.ic_chat_room else R.drawable.ic_default_user
        val sourceBitmap = BitmapFactory.decodeResource(context.resources, resId)

        val output = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(output)

        // Soft neutral circular background (#E2E0E6)
        val bgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xFFE2E0E6.toInt()
            style = Paint.Style.FILL
        }
        val radius = size / 2f
        canvas.drawCircle(radius, radius, radius, bgPaint)

        if (sourceBitmap != null) {
            val iconSize = (size * 0.55f).toInt()
            val left = (size - iconSize) / 2
            val top = (size - iconSize) / 2
            val destRect = Rect(left, top, left + iconSize, top + iconSize)
            val iconPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
            canvas.drawBitmap(sourceBitmap, null, destRect, iconPaint)
        }

        memoryCache.put(cacheKey, output)
        return output
    }

    fun getCachedAvatar(context: Context, pictureId: String): Bitmap? {
        if (pictureId.isBlank()) return null

        memoryCache.get(pictureId)?.let { return it }

        val file = File(getAvatarDir(context), "$pictureId.png")
        if (file.exists()) {
            try {
                val raw = BitmapFactory.decodeFile(file.absolutePath)
                if (raw != null) {
                    val circle = getCircularBitmap(raw)
                    memoryCache.put(pictureId, circle)
                    return circle
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error loading cached avatar $pictureId", e)
            }
        }
        return null
    }

    fun fetchAvatar(
        context: Context,
        session: UserSession,
        pictureId: String,
        onLoaded: (Bitmap) -> Unit
    ) {
        if (pictureId.isBlank()) return

        getCachedAvatar(context, pictureId)?.let {
            onLoaded(it)
            return
        }

        val rawDomain = session.domain
        val httpProtocol = if (rawDomain.startsWith("https://")) "https://" else "http://"
        val cleanHost = rawDomain
            .removePrefix("https://")
            .removePrefix("http://")
            .trimEnd('/')
        val resolvedHost = DeviceUtils.resolveHost(cleanHost)
        val url = "$httpProtocol$resolvedHost/api/attachments/download?file_id=$pictureId"

        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer ${session.accessToken}")
            .build()

        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.w(TAG, "Failed to download avatar $pictureId: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    if (!response.isSuccessful) {
                        Log.w(TAG, "Avatar download returned HTTP ${response.code} for $pictureId")
                        return
                    }
                    val bytes = response.body?.bytes() ?: return
                    val rawBitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return
                    val circleBitmap = getCircularBitmap(rawBitmap)

                    memoryCache.put(pictureId, circleBitmap)

                    try {
                        val file = File(getAvatarDir(context), "$pictureId.png")
                        FileOutputStream(file).use { out ->
                            circleBitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
                        }
                    } catch (e: Exception) {
                        Log.w(TAG, "Failed saving avatar to disk cache", e)
                    }

                    mainHandler.post {
                        onLoaded(circleBitmap)
                    }
                }
            }
        })
    }
}
