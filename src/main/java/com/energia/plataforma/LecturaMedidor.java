package com.energia.plataforma;

/**
 * LecturaMedidor: dato inmutable que reporta un dispositivo IoT
 * (panel solar, batería, medidor de consumo, etc.)
 */
public record LecturaMedidor(String dispositivoId, double produccionKwh, double consumoKwh, long timestampEpoch) {
}
