# =======================================================================
# OuiChat ProGuard / R8 Optimization Rules
# =======================================================================

# 1. Keep your own app classes and members completely intact
# This ensures none of your classes, methods, or fields are stripped or renamed.
-keep class com.example.ouichatandroid.** { *; }
-keepclassmembers class com.example.ouichatandroid.** { *; }

# 2. Preserve JavascriptInterface methods for the WebView <-> Native bridge
-keepattributes JavascriptInterface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# 3. AndroidX Security Crypto & Google Tink (uses reflection internally)
-keep class com.google.crypto.tink.** { *; }
-dontwarn com.google.crypto.tink.**

# 4. OkHttp & Okio
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn javax.annotation.**
-dontwarn org.conscrypt.**
