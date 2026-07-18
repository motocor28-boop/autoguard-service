package com.autoguard.mobilepro;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public final class SensorSpec {
    public interface Decoder {
        Double decode(int[] data);
    }

    public final String key;
    public final String label;
    public final String unit;
    public final String command;
    public final int pid;
    public final int bytes;
    public final String note;
    private final Decoder decoder;

    public SensorSpec(String key, String label, String unit, String command, int pid, int bytes, String note, Decoder decoder) {
        this.key = key;
        this.label = label;
        this.unit = unit;
        this.command = command;
        this.pid = pid;
        this.bytes = bytes;
        this.note = note;
        this.decoder = decoder;
    }

    public Double decode(String response) {
        int[] data = ObdClient.findPidPayload(response, pid, bytes);
        return data == null ? null : decoder.decode(data);
    }

    public String format(Double value) {
        if (value == null) return "--";
        int decimals = (unit.equals("V") || unit.equals("g/s") || unit.equals("%") || unit.equals("kPa")) ? 1 : 0;
        return String.format(Locale.US, "% ." + decimals + "f %s", value, unit).trim();
    }

    public static Map<String, SensorSpec> catalog() {
        LinkedHashMap<String, SensorSpec> map = new LinkedHashMap<>();
        add(map, new SensorSpec("rpm", "RPM motor", "rpm", "010C", 0x0C, 2, "Velocidad calculada por la ECU.", d -> ((d[0] * 256.0) + d[1]) / 4.0));
        add(map, new SensorSpec("speed", "Velocidad vehículo", "km/h", "010D", 0x0D, 1, "Valor informado por ECU/ABS según vehículo.", d -> (double) d[0]));
        add(map, new SensorSpec("coolant", "Temperatura refrigerante", "°C", "0105", 0x05, 1, "Útil para controlar termostato y ventilador.", d -> d[0] - 40.0));
        add(map, new SensorSpec("intake", "Temperatura admisión", "°C", "010F", 0x0F, 1, "Comparar con temperatura ambiente al arrancar.", d -> d[0] - 40.0));
        add(map, new SensorSpec("load", "Carga calculada", "%", "0104", 0x04, 1, "Carga instantánea calculada.", d -> d[0] * 100.0 / 255.0));
        add(map, new SensorSpec("throttle", "Posición mariposa", "%", "0111", 0x11, 1, "Debe variar de forma suave.", d -> d[0] * 100.0 / 255.0));
        add(map, new SensorSpec("maf", "Flujo MAF", "g/s", "0110", 0x10, 2, "Depende de cilindrada, rpm y carga.", d -> ((d[0] * 256.0) + d[1]) / 100.0));
        add(map, new SensorSpec("map", "Presión MAP", "kPa", "010B", 0x0B, 1, "KOEO debe aproximarse a presión barométrica.", d -> (double) d[0]));
        add(map, new SensorSpec("o2b1s1", "O2 B1S1", "V", "0114", 0x14, 2, "Sensor estrecho cuando el PID es compatible.", d -> d[0] / 200.0));
        add(map, new SensorSpec("stft", "STFT banco 1", "%", "0106", 0x06, 1, "Corrección de mezcla a corto plazo.", d -> (d[0] - 128.0) * 100.0 / 128.0));
        add(map, new SensorSpec("ltft", "LTFT banco 1", "%", "0107", 0x07, 1, "Corrección de mezcla aprendida.", d -> (d[0] - 128.0) * 100.0 / 128.0));
        add(map, new SensorSpec("advance", "Avance encendido", "°", "010E", 0x0E, 1, "Depende de carga, rpm y estrategia ECU.", d -> d[0] / 2.0 - 64.0));
        add(map, new SensorSpec("fuelPressure", "Presión combustible", "kPa", "010A", 0x0A, 1, "PID genérico; no todos los vehículos lo soportan.", d -> d[0] * 3.0));
        add(map, new SensorSpec("fuelLevel", "Nivel combustible", "%", "012F", 0x2F, 1, "Referencial para aforador/tablero.", d -> d[0] * 100.0 / 255.0));
        add(map, new SensorSpec("barometric", "Presión barométrica", "kPa", "0133", 0x33, 1, "Comparar con MAP con contacto ON y motor detenido.", d -> (double) d[0]));
        add(map, new SensorSpec("runtime", "Tiempo motor", "s", "011F", 0x1F, 2, "Tiempo desde el arranque actual.", d -> (double) (d[0] * 256 + d[1])));
        add(map, new SensorSpec("controlVoltage", "Voltaje módulo", "V", "0142", 0x42, 2, "Voltaje visto por ECU.", d -> (d[0] * 256.0 + d[1]) / 1000.0));
        add(map, new SensorSpec("ambient", "Temperatura ambiente", "°C", "0146", 0x46, 1, "PID opcional.", d -> d[0] - 40.0));
        add(map, new SensorSpec("evapPurge", "Purgado EVAP", "%", "012E", 0x2E, 1, "Comando de purga cuando esté soportado.", d -> d[0] * 100.0 / 255.0));
        return Collections.unmodifiableMap(map);
    }

    private static void add(Map<String, SensorSpec> map, SensorSpec spec) {
        map.put(spec.key, spec);
    }

    public static List<String> essentialKeys() {
        ArrayList<String> list = new ArrayList<>();
        Collections.addAll(list, "rpm", "coolant", "load", "throttle", "maf", "map", "o2b1s1", "stft", "ltft", "controlVoltage");
        return list;
    }
}
