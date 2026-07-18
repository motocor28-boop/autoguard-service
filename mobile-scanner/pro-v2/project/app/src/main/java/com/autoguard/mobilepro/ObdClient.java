package com.autoguard.mobilepro;

import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ObdClient implements Closeable {
    public enum Mode { WIFI, BLUETOOTH, SIMULATOR }

    public static final class DtcEntry {
        public final String code;
        public final String state;
        public final String description;
        DtcEntry(String code, String state, String description) {
            this.code = code; this.state = state; this.description = description;
        }
    }

    public static final class SessionInfo {
        public final String adapter;
        public final String protocol;
        public final String vin;
        SessionInfo(String adapter, String protocol, String vin) {
            this.adapter = adapter; this.protocol = protocol; this.vin = vin;
        }
    }

    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");
    private final Mode mode;
    private final String host;
    private final int port;
    private final BluetoothDevice bluetoothDevice;
    private Socket wifiSocket;
    private BluetoothSocket bluetoothSocket;
    private InputStream input;
    private OutputStream output;
    private boolean connected;
    private int simulatorCycle;

    public ObdClient(Mode mode, String host, int port, BluetoothDevice bluetoothDevice) {
        this.mode = mode; this.host = host; this.port = port; this.bluetoothDevice = bluetoothDevice;
    }

    public synchronized SessionInfo connect() throws IOException {
        close();
        if (mode == Mode.SIMULATOR) {
            connected = true;
            return new SessionInfo("Autoguard Simulator Pro", "ISO 15765-4 CAN 11/500", "KL1TD5660CB000001");
        }
        if (mode == Mode.WIFI) {
            wifiSocket = new Socket();
            wifiSocket.connect(new InetSocketAddress(host, port), 6000);
            wifiSocket.setSoTimeout(5000);
            input = new BufferedInputStream(wifiSocket.getInputStream());
            output = new BufferedOutputStream(wifiSocket.getOutputStream());
        } else {
            if (bluetoothDevice == null) throw new IOException("Seleccione un adaptador Bluetooth enlazado.");
            bluetoothSocket = bluetoothDevice.createRfcommSocketToServiceRecord(SPP_UUID);
            bluetoothSocket.connect();
            input = new BufferedInputStream(bluetoothSocket.getInputStream());
            output = new BufferedOutputStream(bluetoothSocket.getOutputStream());
        }
        connected = true;
        safeQuery("ATZ"); safeQuery("ATE0"); safeQuery("ATL0"); safeQuery("ATS1"); safeQuery("ATH0");
        safeQuery("ATCAF1"); safeQuery("ATCFC1"); safeQuery("ATAT2"); safeQuery("ATSP0");
        String adapter = cleanText(safeQuery("ATI"));
        String protocol = cleanText(safeQuery("ATDP"));
        safeQuery("0100");
        String vin = parseVin(safeQuery("0902"));
        return new SessionInfo(adapter.isBlank() ? "ELM327" : adapter, protocol.isBlank() ? "Automático" : protocol, vin);
    }

    public synchronized boolean isConnected() { return connected; }

    public synchronized String query(String command) throws IOException {
        if (!connected) throw new IOException("Adaptador no conectado.");
        String normalized = command.trim().toUpperCase(Locale.ROOT).replace(" ", "");
        if (mode == Mode.SIMULATOR) return simulatorResponse(normalized);
        while (input.available() > 0) input.read();
        output.write((normalized + "\r").getBytes(StandardCharsets.US_ASCII));
        output.flush();
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        long deadline = System.currentTimeMillis() + 5500L;
        while (System.currentTimeMillis() < deadline) {
            int value = input.read();
            if (value < 0 || value == '>') break;
            buffer.write(value);
        }
        String response = buffer.toString(StandardCharsets.US_ASCII);
        if (response.isBlank()) throw new IOException("ELM327 no respondió a " + normalized);
        return response;
    }

    private String safeQuery(String command) { try { return query(command); } catch (Exception ignored) { return ""; } }

    public synchronized Map<String, Double> readSensors(List<SensorSpec> selected) throws IOException {
        LinkedHashMap<String, Double> values = new LinkedHashMap<>();
        for (SensorSpec spec : selected) {
            try { values.put(spec.key, spec.decode(query(spec.command))); }
            catch (Exception error) { values.put(spec.key, null); }
        }
        try {
            Matcher matcher = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*V", Pattern.CASE_INSENSITIVE).matcher(query("ATRV"));
            if (matcher.find()) values.put("battery", Double.parseDouble(matcher.group(1)));
        } catch (Exception ignored) { values.put("battery", null); }
        return values;
    }

    public synchronized List<DtcEntry> readAllDtcs() throws IOException {
        ArrayList<DtcEntry> entries = new ArrayList<>();
        parseDtcResponse(query("03"), "Confirmado", entries);
        parseDtcResponse(query("07"), "Pendiente", entries);
        parseDtcResponse(query("0A"), "Permanente", entries);
        return entries;
    }

    public synchronized boolean clearDtcs() throws IOException {
        String response = normalizeHex(query("04"));
        return !response.contains("ERROR") && !response.contains("NODATA") && !response.isBlank();
    }

    private static void parseDtcResponse(String response, String state, List<DtcEntry> destination) {
        String normalized = normalizeHex(response);
        String service = state.equals("Confirmado") ? "43" : state.equals("Pendiente") ? "47" : "4A";
        int index = normalized.indexOf(service);
        if (index < 0) return;
        String data = normalized.substring(index + 2).replaceAll("[^0-9A-F]", "");
        for (int offset = 0; offset + 4 <= data.length(); offset += 4) {
            String word = data.substring(offset, offset + 4);
            if (word.equals("0000")) continue;
            String code = decodeDtc(word);
            destination.add(new DtcEntry(code, state, descriptionFor(code)));
        }
    }

    private static String decodeDtc(String word) {
        int a = Integer.parseInt(word.substring(0, 2), 16);
        int b = Integer.parseInt(word.substring(2, 4), 16);
        char system = new char[]{'P', 'C', 'B', 'U'}[(a >> 6) & 0x03];
        int firstDigit = (a >> 4) & 0x03;
        return String.format(Locale.US, "%c%d%X%02X", system, firstDigit, a & 0x0F, b);
    }

    private static String descriptionFor(String code) {
        if (code.equals("P0101")) return "Rango/rendimiento del circuito MAF";
        if (code.equals("P0113")) return "Entrada alta del sensor IAT";
        if (code.equals("P0128")) return "Temperatura de refrigerante inferior a regulación";
        if (code.equals("P0171")) return "Sistema demasiado pobre, banco 1";
        if (code.equals("P0300")) return "Falla de encendido aleatoria/múltiple";
        if (code.equals("P0420")) return "Eficiencia del catalizador por debajo del umbral";
        if (code.equals("P0442")) return "Fuga pequeña del sistema EVAP";
        return "Código OBD-II; validar descripción OEM según marca y modelo";
    }

    public static int[] findPidPayload(String response, int pid, int length) {
        String hex = normalizeHex(response);
        String marker = String.format(Locale.US, "41%02X", pid);
        int index = hex.indexOf(marker);
        while (index >= 0) {
            int start = index + marker.length();
            int end = start + length * 2;
            if (end <= hex.length()) {
                int[] result = new int[length];
                try {
                    for (int i = 0; i < length; i++) result[i] = Integer.parseInt(hex.substring(start + i * 2, start + i * 2 + 2), 16);
                    return result;
                } catch (NumberFormatException ignored) { }
            }
            index = hex.indexOf(marker, index + 2);
        }
        return null;
    }

    private static String normalizeHex(String value) {
        if (value == null) return "";
        return value.toUpperCase(Locale.ROOT).replaceAll("SEARCHING\\.\\.\\.", "").replaceAll("BUSINIT:OK", "").replaceAll("[^0-9A-F]", "");
    }

    private static String cleanText(String value) {
        if (value == null) return "";
        return value.replace(">", "").replace("\r", " ").replace("\n", " ").replaceAll("\\s+", " ").trim();
    }

    private static String parseVin(String response) {
        String hex = normalizeHex(response);
        int marker = hex.indexOf("4902");
        if (marker < 0) return "";
        String data = hex.substring(marker + 4);
        StringBuilder vin = new StringBuilder();
        for (int i = 0; i + 2 <= data.length(); i += 2) {
            int value;
            try { value = Integer.parseInt(data.substring(i, i + 2), 16); } catch (Exception ignored) { continue; }
            if (value >= 32 && value <= 126) vin.append((char) value);
        }
        String cleaned = vin.toString().replaceAll("[^A-Z0-9]", "");
        return cleaned.length() >= 17 ? cleaned.substring(cleaned.length() - 17) : cleaned;
    }

    private String simulatorResponse(String command) {
        simulatorCycle++;
        double angle = simulatorCycle / 4.0;
        if (command.equals("ATI")) return "AUTOGUARD ELM327 PRO v2.0\r>";
        if (command.equals("ATDP")) return "AUTO, ISO 15765-4 (CAN 11/500)\r>";
        if (command.equals("ATRV")) return "13.7V\r>";
        if (command.equals("0902")) return "49 02 01 4B 4C 31 54 44 35 36 36 30 43 42 30 30 30 30 30 31\r>";
        if (command.equals("03") || command.equals("07") || command.equals("0A")) return command.equals("03") ? "43 00 00\r>" : (command.equals("07") ? "47 00 00\r>" : "4A 00 00\r>");
        if (command.equals("04")) return "44\r>";
        if (command.startsWith("AT")) return "OK\r>";
        Map<String, Integer> oneByte = new LinkedHashMap<>();
        oneByte.put("010D", 0); oneByte.put("0105", 130 + (int)(Math.sin(angle) * 2)); oneByte.put("010F", 78);
        oneByte.put("0104", 55 + (int)(Math.sin(angle) * 8)); oneByte.put("0111", 34 + (int)(Math.sin(angle) * 3));
        oneByte.put("010B", 42 + (int)(Math.sin(angle) * 4)); oneByte.put("0106", 124); oneByte.put("0107", 128);
        oneByte.put("010E", 137); oneByte.put("010A", 100); oneByte.put("012F", 172); oneByte.put("0133", 101);
        oneByte.put("0146", 68); oneByte.put("012E", 40);
        if (oneByte.containsKey(command)) {
            int pid = Integer.parseInt(command.substring(2), 16);
            return String.format(Locale.US, "41 %02X %02X\r>", pid, oneByte.get(command));
        }
        if (command.equals("010C")) {
            int rpm = 720 + (int)(Math.sin(angle) * 35); int raw = rpm * 4;
            return String.format(Locale.US, "41 0C %02X %02X\r>", (raw >> 8) & 0xFF, raw & 0xFF);
        }
        if (command.equals("0110")) return "41 10 01 95\r>";
        if (command.equals("0114")) return "41 14 88 80\r>";
        if (command.equals("011F")) return "41 1F 00 78\r>";
        if (command.equals("0142")) return "41 42 35 84\r>";
        if (command.equals("0100")) return "41 00 BE 3E B8 13\r>";
        return "NO DATA\r>";
    }

    @Override
    public synchronized void close() {
        connected = false; input = null; output = null;
        try { if (wifiSocket != null) wifiSocket.close(); } catch (Exception ignored) { }
        try { if (bluetoothSocket != null) bluetoothSocket.close(); } catch (Exception ignored) { }
        wifiSocket = null; bluetoothSocket = null;
    }
}
