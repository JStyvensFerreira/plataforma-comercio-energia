package com.energia.plataforma;

/**
 * Punto de entrada de prueba: simula lecturas de dos dispositivos IoT
 * llegando al hub y consultas desde otros "módulos" del sistema.
 */
public class Main {

    public static void main(String[] args) {
        // "Módulo IoT": panel solar reportando producción
        MonitorEnergeticoHub.getInstance()
                .registrarLectura(new LecturaMedidor("panel-01", 3.2, 0.0, System.currentTimeMillis()));

        // "Módulo IoT": medidor de consumo de la casa
        MonitorEnergeticoHub.getInstance()
                .registrarLectura(new LecturaMedidor("medidor-casa-01", 0.0, 1.5, System.currentTimeMillis()));

        // "Módulo de predicción" consultando el mismo hub, sin saber cómo llegan los datos
        double produccionActual = MonitorEnergeticoHub.getInstance().produccionTotalActualKwh();
        double consumoActual = MonitorEnergeticoHub.getInstance().consumoTotalActualKwh();

        System.out.println("Producción total actual: " + produccionActual + " kWh");
        System.out.println("Consumo total actual: " + consumoActual + " kWh");

        // Prueba de que es la MISMA instancia en todo el sistema (evidencia del Singleton)
        boolean esLaMismaInstancia = MonitorEnergeticoHub.getInstance() == MonitorEnergeticoHub.getInstance();
        System.out.println("¿Es Singleton (misma instancia)?: " + esLaMismaInstancia);
    }
}
