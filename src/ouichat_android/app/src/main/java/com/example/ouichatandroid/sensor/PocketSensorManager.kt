package com.example.ouichatandroid.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

class PocketSensorManager(
    context: Context,
    private val onPocketStateChanged: (isActive: Boolean) -> Unit
) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val proximitySensor = sensorManager.getDefaultSensor(Sensor.TYPE_PROXIMITY)
    private val lightSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

    private var currentLux: Float = 100f
    private var isNear: Boolean = false
    private var isPocketActive: Boolean = false

    fun start() {
        proximitySensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        lightSensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        if (isPocketActive) {
            isPocketActive = false
            onPocketStateChanged(false)
        }
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return

        when (event.sensor.type) {
            Sensor.TYPE_PROXIMITY -> {
                val distance = event.values.getOrNull(0) ?: return
                val maxRange = proximitySensor?.maximumRange ?: 5f
                isNear = distance < maxRange.coerceAtMost(5f)
            }
            Sensor.TYPE_LIGHT -> {
                currentLux = event.values.getOrNull(0) ?: currentLux
            }
        }

        // Pocket mode active when proximity is covered AND ambient light is pitch dark (<= 2 lux)
        val shouldBeInPocket = isNear && (currentLux <= 2.0f)
        if (shouldBeInPocket != isPocketActive) {
            isPocketActive = shouldBeInPocket
            onPocketStateChanged(isPocketActive)
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
}
