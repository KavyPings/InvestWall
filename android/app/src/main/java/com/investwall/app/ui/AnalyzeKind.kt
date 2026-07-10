package com.investwall.app.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Description
import androidx.compose.material.icons.outlined.GraphicEq
import androidx.compose.material.icons.outlined.Image
import androidx.compose.material.icons.outlined.Message
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * The content sources the app analyzes, each with its own section: text, docs,
 * images/videos, and audio (PRD §5 supported inputs). Text runs on-device; the
 * others upload a file to the backend.
 */
enum class AnalyzeKind(
    val id: String,
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
    val isText: Boolean,
    val pickerLabel: String,
    val mimeTypes: Array<String>,
) {
    TEXT(
        id = "text",
        title = "Text & messages",
        subtitle = "Paste an SMS, email, or WhatsApp forward. Checked privately on your device.",
        icon = Icons.Outlined.Message,
        isText = true,
        pickerLabel = "",
        mimeTypes = emptyArray(),
    ),
    DOCUMENT(
        id = "document",
        title = "Documents",
        subtitle = "Analyze a PDF, DOCX, or TXT — e.g. a circular or notice.",
        icon = Icons.Outlined.Description,
        isText = false,
        pickerLabel = "Choose a document",
        mimeTypes = arrayOf(
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/plain",
        ),
    ),
    MEDIA(
        id = "media",
        title = "Images & videos",
        subtitle = "Check a photo or video for deepfakes and AI generation.",
        icon = Icons.Outlined.Image,
        isText = false,
        pickerLabel = "Choose an image or video",
        mimeTypes = arrayOf("image/*", "video/*"),
    ),
    AUDIO(
        id = "audio",
        title = "Audio & voice notes",
        subtitle = "Detect cloned or synthetic voices in a recording.",
        icon = Icons.Outlined.GraphicEq,
        isText = false,
        pickerLabel = "Choose an audio file",
        mimeTypes = arrayOf("audio/*"),
    );

    companion object {
        fun fromId(id: String?): AnalyzeKind = entries.firstOrNull { it.id == id } ?: TEXT
    }
}
