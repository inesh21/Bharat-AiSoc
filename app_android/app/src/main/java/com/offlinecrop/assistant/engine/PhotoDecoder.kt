package com.offlinecrop.assistant.engine

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri

internal fun decodePhoto(resolver: ContentResolver, uri: Uri): Bitmap {
    fun open() = checkNotNull(resolver.openInputStream(uri)) { "Could not read the selected photo." }
    val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    open().use { BitmapFactory.decodeStream(it, null, options) }
    check(options.outWidth > 0 && options.outHeight > 0) { "The selected file is not a readable photo." }

    options.inJustDecodeBounds = false
    options.inSampleSize = 1
    while (maxOf(options.outWidth, options.outHeight) / options.inSampleSize > 2048) {
        options.inSampleSize *= 2
    }
    options.inPreferredConfig = Bitmap.Config.ARGB_8888
    val orientation = open().use { stream ->
        try {
            ExifInterface(stream).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        } catch (_: java.io.IOException) {
            ExifInterface.ORIENTATION_NORMAL
        }
    }
    val bitmap = open().use { BitmapFactory.decodeStream(it, null, options) }
        ?: error("The selected file could not be decoded.")
    val transform = Matrix()
    when (orientation) {
        ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> transform.setScale(-1f, 1f)
        ExifInterface.ORIENTATION_ROTATE_180 -> transform.setRotate(180f)
        ExifInterface.ORIENTATION_FLIP_VERTICAL -> transform.setScale(1f, -1f)
        ExifInterface.ORIENTATION_TRANSPOSE -> {
            transform.setRotate(90f)
            transform.postScale(-1f, 1f)
        }
        ExifInterface.ORIENTATION_ROTATE_90 -> transform.setRotate(90f)
        ExifInterface.ORIENTATION_TRANSVERSE -> {
            transform.setRotate(-90f)
            transform.postScale(-1f, 1f)
        }
        ExifInterface.ORIENTATION_ROTATE_270 -> transform.setRotate(-90f)
    }
    return if (transform.isIdentity) bitmap else try {
        Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, transform, true)
    } finally {
        bitmap.recycle()
    }
}
