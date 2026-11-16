package com.example.ouichatandroid.util

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.AudioAttributes
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.Person
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import com.example.ouichatandroid.MainActivity
import com.example.ouichatandroid.R
import java.util.concurrent.ConcurrentHashMap

object NotificationHelper {
    const val CHANNEL_MESSAGES = "ouichat_messages_v3"
    const val CHANNEL_SERVICE = "ouichat_service_v3"
    const val SERVICE_NOTIFICATION_ID = 1001
    const val SUMMARY_NOTIFICATION_ID = 1000
    const val NOTIFICATION_GROUP_KEY = "com.example.ouichatandroid.MESSAGES"
    const val BRAND_COLOR = 0xFF5C546C.toInt()

    data class StackedMessage(
        val messageId: String,
        val sender: String,
        var content: String,
        val senderPictureId: String? = null,
        val timestamp: Long = System.currentTimeMillis()
    )

    data class ChatNotificationStack(
        val chatId: String,
        val userKey: String = "default",
        var roomTitle: String? = null,
        var isGroup: Boolean = false,
        var pictureId: String? = null,
        var iconBitmap: Bitmap? = null,
        var recipientUser: String? = null,
        var totalCount: Int = 0,
        val messages: MutableList<StackedMessage> = mutableListOf()
    )

    private val activeNotifiedChats = ConcurrentHashMap.newKeySet<String>()
    private val chatStacks = ConcurrentHashMap<String, ChatNotificationStack>()

    fun getStackKey(userKey: String, chatId: String): String = "$userKey:$chatId"

    fun getGroupKey(userKey: String): String {
        val safeKey = userKey.replace(":", "_").replace("@", "_")
        return "com.example.ouichatandroid.GROUP_$safeKey"
    }

    fun getSummaryNotificationId(userKey: String): Int {
        return ("summary_$userKey").hashCode() and 0x7FFFFFFF
    }

    fun getChildNotificationId(userKey: String, chatId: String): Int {
        return ("$userKey:$chatId").hashCode() and 0x7FFFFFFF
    }

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

            if (manager.getNotificationChannel(CHANNEL_SERVICE) == null) {
                val serviceChannel = NotificationChannel(
                    CHANNEL_SERVICE,
                    "OuiChat Background Service",
                    NotificationManager.IMPORTANCE_LOW
                ).apply {
                    description = "Maintains connection for real-time messages"
                    setShowBadge(false)
                }
                manager.createNotificationChannel(serviceChannel)
            }

            if (manager.getNotificationChannel(CHANNEL_MESSAGES) == null) {
                val soundUri = Uri.parse("android.resource://" + context.packageName + "/" + R.raw.ouichat_chime)
                val audioAttributes = AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                    .build()
                val vibrationPattern = longArrayOf(0, 250, 200, 250)

                val messageChannel = NotificationChannel(
                    CHANNEL_MESSAGES,
                    "OuiChat Messages",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Incoming chat message alerts"
                    setSound(soundUri, audioAttributes)
                    enableVibration(true)
                    this.vibrationPattern = vibrationPattern
                    enableLights(true)
                }
                manager.createNotificationChannel(messageChannel)
            }
        }
    }

    fun buildServiceNotification(context: Context, accountCount: Int = 1): Notification {
        createChannels(context)

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getActivity(context, 0, intent, flags)

        val statusText = if (accountCount > 1) {
            "Connected • Listening on $accountCount accounts"
        } else {
            "Connected • Listening for messages"
        }

        val stopIntent = Intent(context, com.example.ouichatandroid.service.OuiChatPushService::class.java).apply {
            action = com.example.ouichatandroid.service.OuiChatPushService.ACTION_STOP
            putExtra("close_app", true)
        }
        val stopPendingIntent = PendingIntent.getService(context, 1002, stopIntent, flags)
        val stopAction = NotificationCompat.Action.Builder(
            R.drawable.ic_notification,
            "Exit & Stop",
            stopPendingIntent
        ).build()

        val restoreIntent = Intent(context, com.example.ouichatandroid.service.OuiChatPushService::class.java).apply {
            action = com.example.ouichatandroid.service.OuiChatPushService.ACTION_RESTORE_NOTIFICATION
        }
        val deletePendingIntent = PendingIntent.getService(context, 1003, restoreIntent, flags)

        val notification = NotificationCompat.Builder(context, CHANNEL_SERVICE)
            .setContentTitle("OuiChat")
            .setContentText(statusText)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .addAction(stopAction)
            .setDeleteIntent(deletePendingIntent)
            .setOngoing(true)
            .setAutoCancel(false)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        notification.flags = notification.flags or Notification.FLAG_ONGOING_EVENT or Notification.FLAG_NO_CLEAR
        return notification
    }

    fun showMessageNotification(
        context: Context,
        chatId: String,
        sender: String,
        content: String,
        messageId: String = "",
        groupTitle: String? = null,
        isGroup: Boolean = false,
        pictureId: String? = null,
        senderPictureId: String? = null,
        recipientUser: String? = null,
        userKey: String = recipientUser ?: "default"
    ) {
        val cleanGroupTitle = if (!groupTitle.isNullOrBlank() && groupTitle != "null") groupTitle else null
        val cleanPictureId = if (!pictureId.isNullOrBlank() && pictureId != "null") pictureId else null
        val cleanSenderPictureId = if (!senderPictureId.isNullOrBlank() && senderPictureId != "null") senderPictureId else null

        val stackKey = getStackKey(userKey, chatId)
        val stack = chatStacks.compute(stackKey) { _, existing ->
            val s = existing ?: ChatNotificationStack(chatId = chatId, userKey = userKey)
            if (cleanGroupTitle != null) {
                s.roomTitle = cleanGroupTitle
            }
            s.isGroup = isGroup
            if (cleanPictureId != null) {
                s.pictureId = cleanPictureId
            }
            if (recipientUser != null) {
                s.recipientUser = recipientUser
            }
            s.totalCount += 1
            s.messages.add(
                StackedMessage(
                    messageId = messageId,
                    sender = sender,
                    content = content,
                    senderPictureId = cleanSenderPictureId
                )
            )
            s
        }!!

        // If icon is not yet loaded into stack, check cache
        if (stack.iconBitmap == null && !stack.pictureId.isNullOrBlank()) {
            stack.iconBitmap = AvatarManager.getCachedAvatar(context, stack.pictureId!!)
        }

        val isAlreadyNotified = activeNotifiedChats.contains(stackKey)
        renderNotification(context, stackKey, stack, alertOnce = isAlreadyNotified)
    }

    private fun postChildNotification(
        context: Context,
        stackKey: String,
        stack: ChatNotificationStack,
        alertOnce: Boolean
    ) {
        createChannels(context)
        val notifId = getChildNotificationId(stack.userKey, stack.chatId)

        val intent = Intent(context, MainActivity::class.java).apply {
            action = "com.example.ouichatandroid.ACTION_OPEN_CHAT_${stack.userKey}_${stack.chatId}"
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("chat_id", stack.chatId)
            putExtra("user_key", stack.userKey)
            putExtra("recipient_user", stack.recipientUser)
        }
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getActivity(context, notifId, intent, flags)

        val targetUser = (stack.recipientUser ?: stack.userKey.substringBefore("@")).trim()
        val hasTargetUser = targetUser.isNotBlank() && targetUser != "default"

        val rawTitle = if (stack.isGroup && !stack.roomTitle.isNullOrBlank()) {
            stack.roomTitle!!
        } else {
            stack.messages.lastOrNull()?.sender ?: "OuiChat"
        }
        val title = if (hasTargetUser) "$rawTitle (to @$targetUser)" else rawTitle

        // Conversation avatar bitmap: custom picture or default (group or user)
        val conversationAvatar = stack.iconBitmap ?: AvatarManager.getDefaultAvatar(context, stack.isGroup)

        // Publish dynamic conversation shortcut for Android 11+ Conversation space & collapsed avatar
        val shortcutKey = "${stack.userKey}:${stack.chatId}"
        val chatPerson = Person.Builder()
            .setName(title)
            .setKey(shortcutKey)
            .setIcon(IconCompat.createWithBitmap(conversationAvatar))
            .build()

        val shortcut = ShortcutInfoCompat.Builder(context, shortcutKey)
            .setShortLabel(title)
            .setLongLabel(title)
            .setIcon(IconCompat.createWithBitmap(conversationAvatar))
            .setIntent(intent)
            .setPerson(chatPerson)
            .setLongLived(true)
            .build()

        try {
            ShortcutManagerCompat.pushDynamicShortcut(context, shortcut)
        } catch (e: Exception) {
            Log.w("NotificationHelper", "Failed to push dynamic shortcut: ${e.message}")
        }

        // MessagingStyle user and conversation setup
        val mePerson = Person.Builder()
            .setName(if (hasTargetUser) targetUser else "Me")
            .setKey(stack.recipientUser ?: "me")
            .build()

        val messagingStyle = NotificationCompat.MessagingStyle(mePerson)
            .setGroupConversation(stack.isGroup)

        if (stack.isGroup) {
            messagingStyle.setConversationTitle(title)
        }

        val displayed = stack.messages.takeLast(7)
        val colCount = stack.totalCount

        for (msg in displayed) {
            val senderAvatar = (if (!msg.senderPictureId.isNullOrBlank()) {
                AvatarManager.getCachedAvatar(context, msg.senderPictureId)
            } else null) ?: AvatarManager.getDefaultAvatar(context, isGroup = false)

            val senderPerson = Person.Builder()
                .setName(msg.sender)
                .setKey(msg.sender)
                .setIcon(IconCompat.createWithBitmap(senderAvatar))
                .build()

            messagingStyle.addMessage(
                msg.content,
                msg.timestamp,
                senderPerson
            )
        }

        val soundUri = Uri.parse("android.resource://" + context.packageName + "/" + R.raw.ouichat_chime)
        val vibrationPattern = longArrayOf(0, 250, 200, 250)

        val latestMessage = displayed.lastOrNull()
        val baseCollapsed = if (latestMessage != null && stack.isGroup) {
            "${latestMessage.sender}: ${latestMessage.content}"
        } else {
            latestMessage?.content ?: "New message"
        }
        val collapsedText = if (hasTargetUser) {
            "[to @$targetUser] $baseCollapsed"
        } else {
            baseCollapsed
        }

        // Mark as read action
        val markAsReadIntent = Intent(context, com.example.ouichatandroid.service.OuiChatPushService::class.java).apply {
            action = com.example.ouichatandroid.service.OuiChatPushService.ACTION_MARK_AS_READ
            putExtra("chat_id", stack.chatId)
            putExtra("user_key", stack.userKey)
            putExtra("recipient_user", stack.recipientUser)
        }
        val markAsReadPendingIntent = PendingIntent.getService(
            context,
            ("read_${stack.userKey}_${stack.chatId}").hashCode() and 0x7FFFFFFF,
            markAsReadIntent,
            flags
        )
        val markAsReadAction = NotificationCompat.Action.Builder(
            R.drawable.ic_notification,
            "Mark as read",
            markAsReadPendingIntent
        ).build()

        val userGroupKey = getGroupKey(stack.userKey)

        val notificationBuilder = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
            .setContentTitle(title)
            .setContentText(collapsedText)
            .setStyle(messagingStyle)
            .setSmallIcon(R.drawable.ic_notification)
            .setBadgeIconType(NotificationCompat.BADGE_ICON_SMALL)
            .setColor(BRAND_COLOR)
            .setGroup(userGroupKey)
            .setGroupSummary(false)
            .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
            .setLargeIcon(conversationAvatar)
            .setShortcutId(shortcutKey)
            .setContentIntent(pendingIntent)
            .addAction(markAsReadAction)
            .setAutoCancel(true)
            .setNumber(colCount)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            notificationBuilder.setCategory(NotificationCompat.CATEGORY_MESSAGE)
        }

        if (alertOnce) {
            notificationBuilder.setOnlyAlertOnce(true)
        } else {
            notificationBuilder
                .setSound(soundUri)
                .setVibrate(vibrationPattern)
                .setOnlyAlertOnce(false)
        }

        if (hasTargetUser) {
            notificationBuilder.setSubText("to @$targetUser")
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(notifId, notificationBuilder.build())
    }

    private fun renderNotification(
        context: Context,
        stackKey: String,
        stack: ChatNotificationStack,
        alertOnce: Boolean
    ) {
        activeNotifiedChats.add(stackKey)

        // 1. Post/update Group Summary FIRST for this user and resync any existing sibling children
        updateGroupSummary(context, stack.userKey, excludeStackKey = stackKey)

        // 2. Post incoming Child notification SECOND into the active user's bundle
        postChildNotification(context, stackKey, stack, alertOnce = alertOnce)
    }

    fun updateNotificationIcon(context: Context, chatId: String, bitmap: Bitmap) {
        for ((key, stack) in chatStacks) {
            if (stack.chatId == chatId) {
                stack.iconBitmap = bitmap
                renderNotification(context, key, stack, alertOnce = true)
            }
        }
    }

    fun updateUserAvatar(context: Context, username: String, pictureId: String, bitmap: Bitmap) {
        for ((key, stack) in chatStacks) {
            if (!stack.isGroup && stack.messages.any { it.sender == username }) {
                stack.pictureId = pictureId
                stack.iconBitmap = bitmap
                renderNotification(context, key, stack, alertOnce = true)
            }
        }
    }

    fun updateChatName(context: Context, chatId: String, newName: String) {
        for ((key, stack) in chatStacks) {
            if (stack.chatId == chatId) {
                stack.roomTitle = newName
                renderNotification(context, key, stack, alertOnce = true)
            }
        }
    }

    fun updateMessageContent(context: Context, chatId: String, messageId: String, newContent: String) {
        for ((key, stack) in chatStacks) {
            if (stack.chatId == chatId) {
                val msg = stack.messages.find { it.messageId == messageId }
                if (msg != null) {
                    msg.content = "$newContent (edited)"
                    renderNotification(context, key, stack, alertOnce = true)
                }
            }
        }
    }

    fun deleteMessage(context: Context, userKey: String, chatId: String, messageId: String): Boolean {
        val stackKey = getStackKey(userKey, chatId)
        val stack = chatStacks[stackKey] ?: return false
        val removed = stack.messages.removeAll { it.messageId == messageId }
        if (removed) {
            stack.totalCount = (stack.totalCount - 1).coerceAtLeast(0)
        }
        if (stack.messages.isEmpty() || stack.totalCount <= 0) {
            cancelMessageNotification(context, userKey, chatId)
            return true
        } else {
            renderNotification(context, stackKey, stack, alertOnce = true)
            return false
        }
    }

    fun deleteMessage(context: Context, chatId: String, messageId: String): Boolean {
        var anyCleared = false
        val matchingKeys = activeNotifiedChats.filter { it.endsWith(":$chatId") || it == chatId }
        for (key in matchingKeys) {
            val stack = chatStacks[key] ?: continue
            val cleared = deleteMessage(context, stack.userKey, chatId, messageId)
            if (cleared) anyCleared = true
        }
        return anyCleared
    }

    fun updateGroupSummary(context: Context, userKey: String, excludeStackKey: String? = null, isDismissal: Boolean = false) {
        createChannels(context)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val userChatKeys = activeNotifiedChats.filter { it.startsWith("$userKey:") }
        val summaryId = getSummaryNotificationId(userKey)

        if (userChatKeys.isNotEmpty()) {
            val userTotalMessages = userChatKeys.sumOf { chatStacks[it]?.totalCount ?: 0 }
            val globalTotal = PreferenceManager.getTotalUnreadCount(context).coerceAtLeast(chatStacks.values.sumOf { it.totalCount })
            val firstStack = chatStacks[userChatKeys.first()]
            val userDisplayName = (firstStack?.recipientUser ?: userKey.substringBefore("@")).trim()
            val hasUser = userDisplayName.isNotBlank() && userDisplayName != "default"
            val summaryTitle = if (hasUser) "Messages for @$userDisplayName" else "OuiChat"
            val chatCount = userChatKeys.size
            val summaryText = if (chatCount > 1) {
                "$userTotalMessages new messages from $chatCount chats"
            } else {
                val s = firstStack
                val title = if (s?.isGroup == true && !s.roomTitle.isNullOrBlank()) {
                    s.roomTitle
                } else {
                    s?.messages?.lastOrNull()?.sender ?: "OuiChat"
                }
                if (userTotalMessages > 1) "$userTotalMessages new messages from $title" else "1 new message from $title"
            }

            val inboxStyle = NotificationCompat.InboxStyle()
                .setBigContentTitle(summaryTitle)
                .setSummaryText(if (hasUser) "to @$userDisplayName" else summaryText)

            for (chatKey in userChatKeys) {
                val s = chatStacks[chatKey] ?: continue
                val lastMsg = s.messages.lastOrNull() ?: continue
                val senderName = if (s.isGroup) "${lastMsg.sender} (${s.roomTitle ?: "Group"})" else lastMsg.sender
                inboxStyle.addLine("$senderName: ${lastMsg.content}")
            }

            val summaryIntent = Intent(context, MainActivity::class.java).apply {
                action = "com.example.ouichatandroid.ACTION_OPEN_USER_$userKey"
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("user_key", userKey)
                putExtra("recipient_user", firstStack?.recipientUser)
            }
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
            val pendingIntent = PendingIntent.getActivity(context, summaryId, summaryIntent, flags)

            val summaryBuilder = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
                .setSmallIcon(R.drawable.ic_notification)
                .setBadgeIconType(NotificationCompat.BADGE_ICON_SMALL)
                .setColor(BRAND_COLOR)
                .setContentTitle(summaryTitle)
                .setContentText(summaryText)
                .setStyle(inboxStyle)
                .setGroup(getGroupKey(userKey))
                .setGroupSummary(true)
                .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
                .setOnlyAlertOnce(true)
                .setNumber(globalTotal) // Sets app icon badge to sum of all accounts!
                .setSound(null)
                .setVibrate(null)
                .setContentIntent(pendingIntent)
                .setAutoCancel(false)
                .setPriority(NotificationCompat.PRIORITY_HIGH)

            if (hasUser) {
                summaryBuilder.setSubText("to @$userDisplayName")
            }

            val summaryNotification = summaryBuilder.build()
            manager.notify(summaryId, summaryNotification)

            // Resync sibling active chats for this user only on incoming messages, NEVER on dismissal
            if (!isDismissal) {
                for (otherKey in userChatKeys) {
                    if (otherKey != excludeStackKey) {
                        val otherStack = chatStacks[otherKey] ?: continue
                        postChildNotification(context, otherKey, otherStack, alertOnce = true)
                    }
                }
            }
        } else {
            manager.cancel(summaryId)
        }

        // On dismissal, refresh the badge number on any other active user summaries
        if (isDismissal) {
            refreshOtherSummariesBadge(context, excludeUserKey = userKey)
        }
    }

    private fun refreshOtherSummariesBadge(context: Context, excludeUserKey: String? = null) {
        val uniqueUsers = chatStacks.values.map { it.userKey }.distinct()
        for (u in uniqueUsers) {
            if (u != excludeUserKey) {
                val userChatKeys = activeNotifiedChats.filter { it.startsWith("$u:") }
                if (userChatKeys.isNotEmpty()) {
                    updateGroupSummary(context, u, isDismissal = false)
                }
            }
        }
    }

    fun updateSenderAvatar(context: Context, chatId: String) {
        for ((key, stack) in chatStacks) {
            if (stack.chatId == chatId) {
                renderNotification(context, key, stack, alertOnce = true)
            }
        }
    }

    fun cancelMessageNotification(context: Context, userKey: String, chatId: String) {
        val stackKey = getStackKey(userKey, chatId)
        chatStacks.remove(stackKey)
        activeNotifiedChats.remove(stackKey)
        try {
            ShortcutManagerCompat.removeDynamicShortcuts(context, listOf(stackKey, chatId))
        } catch (_: Exception) {}
        val notifId = getChildNotificationId(userKey, chatId)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(notifId)
        updateGroupSummary(context, userKey, isDismissal = true)
    }

    fun cancelMessageNotification(context: Context, chatId: String) {
        val matchingKeys = activeNotifiedChats.filter { it.endsWith(":$chatId") || it == chatId }
        if (matchingKeys.isEmpty()) {
            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.cancel(chatId.hashCode() and 0x7FFFFFFF)
            return
        }
        for (key in matchingKeys) {
            val stack = chatStacks[key]
            val userKey = stack?.userKey ?: key.substringBefore(":")
            cancelMessageNotification(context, userKey, chatId)
        }
    }

    fun cancelAllMessageNotifications(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        for (chatKey in activeNotifiedChats) {
            val stack = chatStacks[chatKey]
            val notifId = if (stack != null) getChildNotificationId(stack.userKey, stack.chatId) else (chatKey.hashCode() and 0x7FFFFFFF)
            manager.cancel(notifId)
        }
        val uniqueUsers = chatStacks.values.map { it.userKey }.distinct()
        for (u in uniqueUsers) {
            manager.cancel(getSummaryNotificationId(u))
        }
        manager.cancel(SUMMARY_NOTIFICATION_ID)
        try {
            ShortcutManagerCompat.removeAllDynamicShortcuts(context)
        } catch (_: Exception) {}
        chatStacks.clear()
        activeNotifiedChats.clear()
    }
}
