package com.energia.plataforma;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * MonitorEnergeticoHub — Singleton
 *
 * Punto único de acceso al estado más reciente de producción/consumo
 * reportado por todos los dispositivos IoT registrados en la plataforma.
 * Módulos como Subastas, Predicción y el Panel de visualización consultan
 * aquí en vez de conectarse cada uno directamente a cada dispositivo.
 *
 * Justificación (ver references/catalogo_patrones.md de la skill de patrones):
 * - Problema: sin un punto único, cada módulo repetiría la lógica de
 *   conexión a cada dispositivo (code smell "Duplicated Code" / conexión
 *   hardcodeada visto en la Semana 1 del curso).
 * - Cuidado: esta clase debe limitarse a "guardar y exponer la última
 *   lectura conocida". Si empieza a calcular predicciones o precios, se
 *   convierte en God Class y viola SRP.
 */
public final class MonitorEnergeticoHub {

    private static volatile MonitorEnergeticoHub instancia;

    // Estado compartido: última lectura conocida por dispositivo
    private final Map<String, LecturaMedidor> ultimasLecturas = new ConcurrentHashMap<>();

    private MonitorEnergeticoHub() {
        // Constructor privado: nadie fuera de esta clase puede instanciarla
    }

    public static MonitorEnergeticoHub getInstance() {
        // Double-checked locking: evita sincronizar en cada llamada,
        // solo la primera vez que se crea la instancia.
        if (instancia == null) {
            synchronized (MonitorEnergeticoHub.class) {
                if (instancia == null) {
                    instancia = new MonitorEnergeticoHub();
                }
            }
        }
        return instancia;
    }

    /** Llamado por el adaptador de cada dispositivo IoT cuando llega un dato nuevo. */
    public void registrarLectura(LecturaMedidor lectura) {
        ultimasLecturas.put(lectura.dispositivoId(), lectura);
    }

    public Optional<LecturaMedidor> obtenerUltimaLectura(String dispositivoId) {
        return Optional.ofNullable(ultimasLecturas.get(dispositivoId));
    }

    public double produccionTotalActualKwh() {
        return ultimasLecturas.values().stream()
                .mapToDouble(LecturaMedidor::produccionKwh)
                .sum();
    }

    public double consumoTotalActualKwh() {
        return ultimasLecturas.values().stream()
                .mapToDouble(LecturaMedidor::consumoKwh)
                .sum();
    }

    /** Útil para pruebas unitarias: resetea el estado global del Singleton. */
    public void limpiarParaPruebas() {
        ultimasLecturas.clear();
    }
}
