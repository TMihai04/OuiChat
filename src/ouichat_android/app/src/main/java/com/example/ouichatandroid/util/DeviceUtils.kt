package com.example.ouichatandroid.util

import android.os.Build

object DeviceUtils {

    /**
     * Determines whether the app is running on an Android Emulator
     * (Goldfish, Ranchu, Google APIs, Genymotion, or SDK phone).
     */
    fun isEmulator(): Boolean {
        return (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic"))
                || Build.FINGERPRINT.startsWith("generic")
                || Build.FINGERPRINT.startsWith("unknown")
                || Build.HARDWARE.contains("goldfish")
                || Build.HARDWARE.contains("ranchu")
                || Build.MODEL.contains("google_sdk")
                || Build.MODEL.contains("Emulator")
                || Build.MODEL.contains("Android SDK built for x86")
                || Build.MANUFACTURER.contains("Genymotion")
                || Build.PRODUCT.contains("sdk_gphone")
                || Build.PRODUCT.contains("google_sdk")
                || Build.PRODUCT.contains("sdk")
                || Build.PRODUCT.contains("sdk_x86")
                || Build.PRODUCT.contains("vbox86p")
                || Build.PRODUCT.contains("emulator")
                || Build.PRODUCT.contains("simulator")
    }

    /**
     * Translates localhost or 127.0.0.1 to 10.0.2.2 on Android Emulators
     * so that the virtual device connects to the development computer host.
     * On physical USB/Wi-Fi devices, the original host is preserved.
     */
    fun resolveHost(rawHost: String): String {
        if (!isEmulator()) return rawHost

        val prefixes = listOf("http://", "https://", "ws://", "wss://")
        var matchedPrefix = ""
        var hostWithoutPrefix = rawHost
        for (prefix in prefixes) {
            if (rawHost.startsWith(prefix, ignoreCase = true)) {
                matchedPrefix = prefix
                hostWithoutPrefix = rawHost.substring(prefix.length)
                break
            }
        }

        val resolved = if (hostWithoutPrefix.startsWith("localhost", ignoreCase = true)) {
            hostWithoutPrefix.replaceFirst("localhost", "10.0.2.2", ignoreCase = true)
        } else if (hostWithoutPrefix.startsWith("127.0.0.1")) {
            hostWithoutPrefix.replaceFirst("127.0.0.1", "10.0.2.2")
        } else {
            hostWithoutPrefix
        }

        return "$matchedPrefix$resolved"
    }

    data class DomainTarget(
        val isSecure: Boolean,
        val cleanHost: String
    ) {
        val httpUrl: String get() = "${if (isSecure) "https://" else "http://"}$cleanHost"
        val wsUrl: String get() = "${if (isSecure) "wss://" else "ws://"}$cleanHost"
    }

    fun parseDomainTarget(rawDomain: String): DomainTarget {
        val trimmed = rawDomain.trim()
        val isSecureExplicit = trimmed.startsWith("https://", ignoreCase = true) || trimmed.startsWith("wss://", ignoreCase = true)
        val isInsecureExplicit = trimmed.startsWith("http://", ignoreCase = true) || trimmed.startsWith("ws://", ignoreCase = true)

        val cleanHost = trimmed
            .removePrefix("https://")
            .removePrefix("http://")
            .removePrefix("wss://")
            .removePrefix("ws://")
            .trimEnd('/')

        val resolvedHost = resolveHost(cleanHost)

        val isLocalHost = resolvedHost.startsWith("localhost", ignoreCase = true) ||
                resolvedHost.startsWith("127.0.0.1") ||
                resolvedHost.startsWith("10.0.2.2") ||
                resolvedHost.startsWith("192.168.") ||
                resolvedHost.startsWith("10.") ||
                resolvedHost.endsWith(".local", ignoreCase = true)

        val isSecure = when {
            isSecureExplicit -> true
            isInsecureExplicit -> false
            else -> !isLocalHost
        }

        return DomainTarget(isSecure, resolvedHost)
    }
}
