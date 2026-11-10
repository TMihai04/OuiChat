package com.example.ouichatandroid.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager

class LightSensorManager(
    context: Context,
    private val onThemeChanged: (theme: String) -> Unit
) : SensorEventListener {

    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val lightSensor = sensorManager.getDefaultSensor(Sensor.TYPE_LIGHT)

    private var currentAppliedTheme: String = "dark"
    private var isEnabled: Boolean = false

    fun isSensorAvailable(): Boolean = lightSensor != null

    fun setAutoModeEnabled(enabled: Boolean) {
        if (isEnabled == enabled) return
        isEnabled = enabled
        if (enabled) {
            lightSensor?.let {
                sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL)
            }
        } else {
            sensorManager.unregisterListener(this)
        }
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (!isEnabled || event == null || event.sensor.type != Sensor.TYPE_LIGHT) return
        val lux = event.values.getOrNull(0) ?: return

        // Hysteresis: <20 lux for dark, >50 lux for light
        if (lux < 20f && currentAppliedTheme != "dark") {
            currentAppliedTheme = "dark"
            onThemeChanged("dark")
        } else if (lux > 50f && currentAppliedTheme != "light") {
            currentAppliedTheme = "light"
            onThemeChanged("light")
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    fun stop() {
        sensorManager.unregisterListener(this)
        isEnabled = false
    }
}
