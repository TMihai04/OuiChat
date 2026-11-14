package com.example.ouichatandroid

import android.Manifest
import android.annotation.SuppressLint
import android.content.ContentResolver
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.webkit.MimeTypeMap
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import androidx.webkit.WebViewAssetLoader
import com.example.ouichatandroid.bridge.AndroidBridge
import com.example.ouichatandroid.sensor.LightSensorManager
import com.example.ouichatandroid.sensor.PocketSensorManager
import com.example.ouichatandroid.service.OuiChatPushService
import com.example.ouichatandroid.util.DeviceUtils
import com.example.ouichatandroid.util.NotificationHelper
import com.example.ouichatandroid.util.PreferenceManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID

class MainActivity : ComponentActivity() {

    companion object {
        @Volatile
        var activeInstance: MainActivity? = null
    }

    private lateinit var webView: WebView
    private lateinit var rootLayout: FrameLayout
    private lateinit var pocketOverlay: View
    private lateinit var lightSensorManager: LightSensorManager
    private lateinit var pocketSensorManager: PocketSensorManager
    private lateinit var bridge: AndroidBridge

    private var isPocketActive = false
    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null

    // Supports both Emulator (10.0.2.2) and Physical USB Phone (localhost via adb reverse)
    private val devUrl: String
        get() = DeviceUtils.resolveHost("http://localhost:5173")

    // If embedded web assets exist, load directly from inside the APK.
    // Otherwise fall back to local dev server (Vite on port 5173).
    private val appUrl: String
        get() {
            return try {
                assets.open("index.html").close()
                "https://appassets.androidplatform.net/index.html"
            } catch (_: Exception) {
                devUrl
            }
        }

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val callback = fileUploadCallback
        fileUploadCallback = null

        val data = result.data
        if (result.resultCode != RESULT_OK || data == null) {
            callback?.onReceiveValue(null)
            return@registerForActivityResult
        }

        val rawUris = mutableListOf<Uri>()
        if (data.clipData != null) {
            val clip = data.clipData!!
            for (i in 0 until clip.itemCount) {
                val uri = clip.getItemAt(i).uri
                if (uri != null) {
                    rawUris.add(uri)
                }
            }
        } else if (data.data != null) {
            rawUris.add(data.data!!)
        }

        if (rawUris.isEmpty()) {
            val parsed = WebChromeClient.FileChooserParams.parseResult(result.resultCode, data)
            if (parsed != null) {
                rawUris.addAll(parsed)
            }
        }

        if (rawUris.isEmpty()) {
            callback?.onReceiveValue(null)
            return@registerForActivityResult
        }

        lifecycleScope.launch(Dispatchers.IO) {
            val safeUris = mutableListOf<Uri>()
            for (uri in rawUris) {
                val safeUri = copyUriToCache(uri)
                if (safeUri != null) {
                    safeUris.add(safeUri)
                }
            }
            withContext(Dispatchers.Main) {
                callback?.onReceiveValue(
                    if (safeUris.isNotEmpty()) safeUris.toTypedArray() else null
                )
            }
        }
    }

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startPushServiceIfLoggedIn()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent?.getBooleanExtra("action_exit", false) == true) {
            finishAffinity()
            finishAndRemoveTask()
            return
        }

        NotificationHelper.createChannels(this)
        checkNotificationPermission()
        startPushServiceIfLoggedIn()
        cleanOldStagedUploads()

        // 1. Initialize Sensor Managers
        lightSensorManager = LightSensorManager(this) { theme ->
            runOnUiThread {
                webView.evaluateJavascript("if (window.applyTheme) window.applyTheme('$theme')", null)
            }
        }

        pocketSensorManager = PocketSensorManager(this) { active ->
            runOnUiThread {
                setPocketMode(active)
            }
        }

        // 2. Initialize Bridge
        bridge = AndroidBridge(this, lightSensorManager)

        // 3. Set up root container and WebView
        val assetLoader = WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        rootLayout = FrameLayout(this).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(Color.parseColor("#343232"))
        }

        WebView.setWebContentsDebuggingEnabled(true)

        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(Color.TRANSPARENT)

            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                useWideViewPort = true
                loadWithOverviewMode = true
                allowFileAccess = true
                allowContentAccess = true
                allowFileAccessFromFileURLs = true
                allowUniversalAccessFromFileURLs = true
                mediaPlaybackRequiresUserGesture = false
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            }

            addJavascriptInterface(bridge, "AndroidBridge")

            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView?,
                    request: WebResourceRequest?
                ): WebResourceResponse? {
                    return request?.url?.let { assetLoader.shouldInterceptRequest(it) }
                        ?: super.shouldInterceptRequest(view, request)
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    val savedMode = PreferenceManager.getThemeMode(this@MainActivity)
                    lightSensorManager.setAutoModeEnabled(savedMode == "auto")
                    handleNotificationIntent(intent)
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    super.onReceivedError(view, request, error)
                    if (request?.isForMainFrame == true && !appUrl.startsWith("https://appassets.androidplatform.net")) {
                        showDevServerNotice(view)
                    }
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    wv: WebView?,
                    filePathCallback: ValueCallback<Array<Uri>>?,
                    fileChooserParams: FileChooserParams?
                ): Boolean {
                    fileUploadCallback?.onReceiveValue(null)
                    fileUploadCallback = filePathCallback

                    val isMultiple = fileChooserParams?.mode == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE

                    val contentIntent = (fileChooserParams?.createIntent() ?: Intent(Intent.ACTION_GET_CONTENT)).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        if (type.isNullOrEmpty()) {
                            type = "*/*"
                        }
                        if (isMultiple) {
                            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                        }
                    }

                    val chooserIntent = Intent.createChooser(contentIntent, "Select File").apply {
                        if (isMultiple) {
                            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                        }
                    }

                    try {
                        filePickerLauncher.launch(chooserIntent)
                    } catch (_: Exception) {
                        try {
                            filePickerLauncher.launch(contentIntent)
                        } catch (_: Exception) {
                            fileUploadCallback?.onReceiveValue(null)
                            fileUploadCallback = null
                            return false
                        }
                    }
                    return true
                }
            }
        }
        rootLayout.addView(webView)

        // 4. Set up Pocket Mode blackout overlay
        pocketOverlay = View(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(Color.BLACK)
            visibility = View.GONE
        }
        rootLayout.addView(pocketOverlay)

        setContentView(rootLayout)

        // 5. Native Back Button Handling
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                webView.evaluateJavascript(
                    "typeof window.onNativeBackPressed === 'function' ? window.onNativeBackPressed() : false"
                ) { result ->
                    val handled = result?.replace("\"", "")?.toBoolean() ?: false
                    if (!handled) {
                        moveTaskToBack(true)
                    }
                }
            }
        })

        // 6. Load App URL
        webView.loadUrl(appUrl)
    }

    private fun checkNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        } else {
            if (!NotificationManagerCompat.from(this).areNotificationsEnabled()) {
                Toast.makeText(this, "Please enable notifications for OuiChat to receive alerts", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun startPushServiceIfLoggedIn() {
        val sessions = PreferenceManager.getSessions(this)
        if (sessions.isNotEmpty()) {
            val serviceIntent = Intent(applicationContext, OuiChatPushService::class.java).apply {
                action = OuiChatPushService.ACTION_START
            }
            try {
                ContextCompat.startForegroundService(applicationContext, serviceIntent)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun showDevServerNotice(view: WebView?) {
        val html = """
            <!DOCTYPE html>
            <html>
            <head>
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <style>
                body {
                  margin: 0; padding: 24px;
                  background: #343232; color: #f4f0f8;
                  font-family: sans-serif; text-align: center;
                  display: flex; flex-direction: column; justify-content: center; height: 100vh; box-sizing: border-box;
                }
                h2 { color: #e3ddec; margin-bottom: 8px; }
                p { font-size: 14px; opacity: 0.8; line-height: 1.5; }
                code { background: #4a484e; padding: 4px 8px; border-radius: 6px; font-size: 13px; }
                button {
                  margin-top: 20px; padding: 12px 24px;
                  background: #9A76B7; color: white; border: none;
                  border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer;
                }
              </style>
            </head>
            <body>
              <h2>Connecting to OuiChat...</h2>
              <p>Waiting for Vite dev server at <code>$devUrl</code>.</p>
              <p>If connecting over USB-C cable, run:<br><code>adb reverse tcp:5173 tcp:5173</code></p>
              <button onclick="location.reload()">Retry Connection</button>
            </body>
            </html>
        """.trimIndent()
        view?.loadDataWithBaseURL(null, html, "text/html", "utf-8", null)
    }

    private fun setPocketMode(active: Boolean) {
        if (isPocketActive == active) return
        isPocketActive = active
        pocketOverlay.visibility = if (active) View.VISIBLE else View.GONE

        // Dim OLED screen to minimum when in pocket
        val lp = window.attributes
        lp.screenBrightness = if (active) 0.01f else WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
        window.attributes = lp
    }

    override fun dispatchTouchEvent(ev: MotionEvent?): Boolean {
        // Block and swallow all touches when phone is in pocket
        if (isPocketActive) return true
        return super.dispatchTouchEvent(ev)
    }

    override fun onResume() {
        super.onResume()
        activeInstance = this
        OuiChatPushService.isAppInForeground = true
        pocketSensorManager.start()
        val savedMode = PreferenceManager.getThemeMode(this)
        lightSensorManager.setAutoModeEnabled(savedMode == "auto")
        webView.onResume()
        webView.evaluateJavascript(
            "if (window.onNativeAppResumed) window.onNativeAppResumed()",
            null
        )
    }

    override fun onPause() {
        super.onPause()
        OuiChatPushService.isAppInForeground = false
        pocketSensorManager.stop()
        lightSensorManager.stop()
        webView.onPause()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (intent.getBooleanExtra("action_exit", false)) {
            finishAffinity()
            finishAndRemoveTask()
            return
        }
        handleNotificationIntent(intent)
    }

    private fun handleNotificationIntent(intent: Intent?) {
        val chatId = intent?.getStringExtra("chat_id") ?: return
        intent.removeExtra("chat_id")
        bridge.pendingChatId = chatId
        NotificationHelper.cancelMessageNotification(this, chatId)
        PreferenceManager.clearUnreadCount(this, chatId)
        webView.evaluateJavascript(
            "if (window.selectChatFromNative) window.selectChatFromNative('$chatId')",
            null
        )
    }

    fun markChatReadInWebView(chatId: String) {
        runOnUiThread {
            webView.evaluateJavascript(
                "if (window.markChatReadFromNative) window.markChatReadFromNative('$chatId')",
                null
            )
        }
    }

    private fun getFileNameFromUri(uri: Uri): String {
        var name: String? = null
        if (uri.scheme == ContentResolver.SCHEME_CONTENT) {
            try {
                contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if (index >= 0) {
                            name = cursor.getString(index)
                        }
                    }
                }
            } catch (_: Exception) {}
        }
        if (name.isNullOrBlank()) {
            name = uri.lastPathSegment
        }
        if (name.isNullOrBlank()) {
            name = "file_${System.currentTimeMillis()}"
        }
        if (!name.contains(".") || name.endsWith(".")) {
            try {
                val mimeType = contentResolver.getType(uri)
                val ext = if (mimeType != null) MimeTypeMap.getSingleton().getExtensionFromMimeType(mimeType) else null
                if (!ext.isNullOrBlank()) {
                    name = if (name.endsWith(".")) "$name$ext" else "$name.$ext"
                }
            } catch (_: Exception) {}
        }
        val sanitized = name.replace("[/\\\\:*?\"<>|]".toRegex(), "_").trim()
        return if (sanitized.isNotEmpty()) sanitized else "file_${System.currentTimeMillis()}"
    }

    private fun copyUriToCache(uri: Uri): Uri? {
        return try {
            val fileName = getFileNameFromUri(uri)
            val subFolder = File(cacheDir, "staged_uploads/${System.currentTimeMillis()}_${UUID.randomUUID().toString().take(6)}")
            if (!subFolder.exists()) {
                subFolder.mkdirs()
            }
            val destFile = File(subFolder, fileName)

            contentResolver.openInputStream(uri)?.use { inputStream ->
                destFile.outputStream().use { outputStream ->
                    inputStream.copyTo(outputStream)
                }
            } ?: return null

            val providerUri = FileProvider.getUriForFile(this, "${packageName}.fileprovider", destFile)
            grantUriPermission(packageName, providerUri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            providerUri
        } catch (e: Exception) {
            android.util.Log.e("OuiChat", "Failed to cache picked file from uri: $uri", e)
            null
        }
    }

    private fun cleanOldStagedUploads() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val stagedDir = File(cacheDir, "staged_uploads")
                if (stagedDir.exists() && stagedDir.isDirectory) {
                    val oneDayAgo = System.currentTimeMillis() - 24 * 60 * 60 * 1000L
                    stagedDir.listFiles()?.forEach { file ->
                        if (file.lastModified() < oneDayAgo) {
                            file.deleteRecursively()
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.w("OuiChat", "Failed to clean old staged uploads", e)
            }
        }
    }

    override fun onDestroy() {
        if (activeInstance == this) {
            activeInstance = null
        }
        webView.destroy()
        super.onDestroy()
    }
}
