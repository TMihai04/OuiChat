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
        recipientUser: String? = null
    ) {
        val cleanGroupTitle = if (!groupTitle.isNullOrBlank() && groupTitle != "null") groupTitle else null
        val cleanPictureId = if (!pictureId.isNullOrBlank() && pictureId != "null") pictureId else null
        val cleanSenderPictureId = if (!senderPictureId.isNullOrBlank() && senderPictureId != "null") senderPictureId else null

        val stack = chatStacks.compute(chatId) { _, existing ->
            val s = existing ?: ChatNotificationStack(chatId = chatId)
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

        val isAlreadyNotified = activeNotifiedChats.contains(chatId)
        renderNotification(context, chatId, stack, alertOnce = isAlreadyNotified)
    }

    private fun postChildNotification(
        context: Context,
        chatId: String,
        stack: ChatNotificationStack,
        alertOnce: Boolean
    ) {
        createChannels(context)
        val notifId = chatId.hashCode() and 0x7FFFFFFF

        val intent = Intent(context, MainActivity::class.java).apply {
            action = "com.example.ouichatandroid.ACTION_OPEN_CHAT_$chatId"
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("chat_id", chatId)
        }
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getActivity(context, notifId, intent, flags)

        val title = if (stack.isGroup && !stack.roomTitle.isNullOrBlank()) {
            stack.roomTitle!!
        } else {
            stack.messages.lastOrNull()?.sender ?: "OuiChat"
        }

        // Conversation avatar bitmap: custom picture or default (group or user)
        val conversationAvatar = stack.iconBitmap ?: AvatarManager.getDefaultAvatar(context, stack.isGroup)

        // Publish dynamic conversation shortcut for Android 11+ Conversation space & collapsed avatar
        val chatPerson = Person.Builder()
            .setName(title)
            .setKey(chatId)
            .setIcon(IconCompat.createWithBitmap(conversationAvatar))
            .build()

        val shortcut = ShortcutInfoCompat.Builder(context, chatId)
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
            .setName("Me")
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
        val collapsedText = if (latestMessage != null && stack.isGroup) {
            "${latestMessage.sender}: ${latestMessage.content}"
        } else {
            latestMessage?.content ?: "New message"
        }

        // Mark as read action
        val markAsReadIntent = Intent(context, com.example.ouichatandroid.service.OuiChatPushService::class.java).apply {
            action = com.example.ouichatandroid.service.OuiChatPushService.ACTION_MARK_AS_READ
            putExtra("chat_id", chatId)
            putExtra("recipient_user", stack.recipientUser)
        }
        val markAsReadPendingIntent = PendingIntent.getService(
            context,
            ("read_$chatId").hashCode() and 0x7FFFFFFF,
            markAsReadIntent,
            flags
        )
        val markAsReadAction = NotificationCompat.Action.Builder(
            R.drawable.ic_notification,
            "Mark as read",
            markAsReadPendingIntent
        ).build()

        val notificationBuilder = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
            .setContentTitle(title)
            .setContentText(collapsedText)
            .setStyle(messagingStyle)
            .setSmallIcon(R.drawable.ic_notification)
            .setBadgeIconType(NotificationCompat.BADGE_ICON_SMALL)
            .setColor(BRAND_COLOR)
            .setGroup(NOTIFICATION_GROUP_KEY)
            .setGroupSummary(false)
            .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
            .setLargeIcon(conversationAvatar)
            .setShortcutId(chatId)
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

        if (!stack.recipientUser.isNullOrBlank()) {
            notificationBuilder.setSubText("to @${stack.recipientUser}")
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(notifId, notificationBuilder.build())
    }

    private fun renderNotification(
        context: Context,
        chatId: String,
        stack: ChatNotificationStack,
        alertOnce: Boolean
    ) {
        activeNotifiedChats.add(chatId)

        // 1. Post/update Group Summary FIRST and resync any existing sibling children
        updateGroupSummary(context, excludeChatId = chatId)

        // 2. Post incoming Child notification SECOND into the active bundle
        postChildNotification(context, chatId, stack, alertOnce = alertOnce)
    }

    fun updateNotificationIcon(context: Context, chatId: String, bitmap: Bitmap) {
        val stack = chatStacks[chatId] ?: return
        stack.iconBitmap = bitmap
        renderNotification(context, chatId, stack, alertOnce = true)
    }

    fun updateUserAvatar(context: Context, username: String, pictureId: String, bitmap: Bitmap) {
        for ((chatId, stack) in chatStacks) {
            if (!stack.isGroup && stack.messages.any { it.sender == username }) {
                stack.pictureId = pictureId
                stack.iconBitmap = bitmap
                renderNotification(context, chatId, stack, alertOnce = true)
            }
        }
    }

    fun updateChatName(context: Context, chatId: String, newName: String) {
        val stack = chatStacks[chatId] ?: return
        stack.roomTitle = newName
        renderNotification(context, chatId, stack, alertOnce = true)
    }

    fun updateMessageContent(context: Context, chatId: String, messageId: String, newContent: String) {
        val stack = chatStacks[chatId] ?: return
        val msg = stack.messages.find { it.messageId == messageId } ?: return
        msg.content = "$newContent (edited)"
        renderNotification(context, chatId, stack, alertOnce = true)
    }

    fun deleteMessage(context: Context, chatId: String, messageId: String): Boolean {
        val stack = chatStacks[chatId] ?: return false
        val removed = stack.messages.removeAll { it.messageId == messageId }
        if (removed) {
            stack.totalCount = (stack.totalCount - 1).coerceAtLeast(0)
        }
        if (stack.messages.isEmpty() || stack.totalCount <= 0) {
            cancelMessageNotification(context, chatId)
            return true
        } else {
            renderNotification(context, chatId, stack, alertOnce = true)
            return false
        }
    }

    fun updateGroupSummary(context: Context, excludeChatId: String? = null, isDismissal: Boolean = false) {
        createChannels(context)
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (activeNotifiedChats.isNotEmpty()) {
            val totalMessages = chatStacks.values.sumOf { it.totalCount }
            val chatCount = activeNotifiedChats.size
            val summaryTitle = "OuiChat"
            val summaryText = if (chatCount > 1) {
                "$totalMessages new messages from $chatCount chats"
            } else {
                val s = activeNotifiedChats.firstOrNull()?.let { chatStacks[it] }
                val title = if (s?.isGroup == true && !s.roomTitle.isNullOrBlank()) {
                    s.roomTitle
                } else {
                    s?.messages?.lastOrNull()?.sender ?: "OuiChat"
                }
                if (totalMessages > 1) "$totalMessages new messages from $title" else "1 new message from $title"
            }

            val inboxStyle = NotificationCompat.InboxStyle()
                .setBigContentTitle(summaryTitle)
                .setSummaryText(summaryText)

            for (chat in activeNotifiedChats) {
                val s = chatStacks[chat] ?: continue
                val lastMsg = s.messages.lastOrNull() ?: continue
                val senderName = if (s.isGroup) "${lastMsg.sender} (${s.roomTitle ?: "Group"})" else lastMsg.sender
                inboxStyle.addLine("$senderName: ${lastMsg.content}")
            }

            val summaryIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
            val pendingIntent = PendingIntent.getActivity(context, SUMMARY_NOTIFICATION_ID, summaryIntent, flags)

            val summaryNotification = NotificationCompat.Builder(context, CHANNEL_MESSAGES)
                .setSmallIcon(R.drawable.ic_notification)
                .setBadgeIconType(NotificationCompat.BADGE_ICON_SMALL)
                .setColor(BRAND_COLOR)
                .setContentTitle(summaryTitle)
                .setContentText(summaryText)
                .setStyle(inboxStyle)
                .setGroup(NOTIFICATION_GROUP_KEY)
                .setGroupSummary(true)
                .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_CHILDREN)
                .setOnlyAlertOnce(true)
                .setNumber(totalMessages)
                .setSound(null)
                .setVibrate(null)
                .setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()

            manager.notify(SUMMARY_NOTIFICATION_ID, summaryNotification)

            // Resync sibling active chats only on incoming messages, NEVER on dismissal
            if (!isDismissal) {
                for (otherChatId in activeNotifiedChats) {
                    if (otherChatId != excludeChatId) {
                        val otherStack = chatStacks[otherChatId] ?: continue
                        postChildNotification(context, otherChatId, otherStack, alertOnce = true)
                    }
                }
            }
        } else {
            manager.cancel(SUMMARY_NOTIFICATION_ID)
        }
    }

    fun updateSenderAvatar(context: Context, chatId: String) {
        val stack = chatStacks[chatId] ?: return
        renderNotification(context, chatId, stack, alertOnce = true)
    }

    fun cancelMessageNotification(context: Context, chatId: String) {
        chatStacks.remove(chatId)
        activeNotifiedChats.remove(chatId)
        try {
            ShortcutManagerCompat.removeDynamicShortcuts(context, listOf(chatId))
        } catch (_: Exception) {}
        val notifId = chatId.hashCode() and 0x7FFFFFFF
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.cancel(notifId)
        updateGroupSummary(context, isDismissal = true)
    }

    fun cancelAllMessageNotifications(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        for (chatId in activeNotifiedChats) {
            manager.cancel(chatId.hashCode() and 0x7FFFFFFF)
        }
        manager.cancel(SUMMARY_NOTIFICATION_ID)
        try {
            ShortcutManagerCompat.removeAllDynamicShortcuts(context)
        } catch (_: Exception) {}
        chatStacks.clear()
        activeNotifiedChats.clear()
    }
}
