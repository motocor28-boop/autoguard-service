package com.autoguard.mobilepro;

import android.content.Context;
import android.content.SharedPreferences;
import android.provider.Settings;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;

public final class LicenseManager {
    private static final String PREFS = "autoguard_license";
    private static final String PUBLIC_KEY_B64 = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2qgrogv6wvfg+wWajzJ/8qbp/xfrmx6Bs6l/2E/l/H4NQlAH0Ie4VkfWqCuMbID9o5i7yYe57+CSHvCEJTFkC6WN2H/F/kXE10nDgQr+BubLk8TWU+NO6DH+jPO6ecW0yxuY2zJ5MmexU6PIhiuO/KvEigwy12xvUbQ7UChuptANpKfSHFnid0XAiUlGFqeoTOJnaHArkVZu2Fy99MMzD8oNf3tESiSn+EV/sjCW+QvY620yBiiGwsxInhhOVKssoyq8g/GQjq3PIHB+pUM3MrGSoW2QwT31pxkl9iIthB3W1ZoELTakJjfD1eEbT/wwUavbR+xULrnMb2xyz0tCWwIDAQAB";
    private static final int DEMO_DAYS = 7;

    public static final class LicenseStatus {
        public final boolean active;
        public final boolean demo;
        public final String plan;
        public final String licenseId;
        public final String expires;
        public final String message;

        LicenseStatus(boolean active, boolean demo, String plan, String licenseId, String expires, String message) {
            this.active = active;
            this.demo = demo;
            this.plan = plan;
            this.licenseId = licenseId;
            this.expires = expires;
            this.message = message;
        }
    }

    private LicenseManager() {}

    public static String deviceId(Context context) {
        String value = Settings.Secure.getString(context.getContentResolver(), Settings.Secure.ANDROID_ID);
        return value == null || value.isBlank() ? "ANDROID-UNKNOWN" : value.toUpperCase();
    }

    public static LicenseStatus status(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String token = prefs.getString("token", "");
        if (!token.isBlank()) {
            LicenseStatus verified = verifyToken(context, token);
            if (verified.active) return verified;
        }

        long installed = prefs.getLong("demo_start", 0L);
        if (installed == 0L) {
            installed = System.currentTimeMillis();
            prefs.edit().putLong("demo_start", installed).apply();
        }
        long days = Math.max(0L, (System.currentTimeMillis() - installed) / 86_400_000L);
        long remaining = DEMO_DAYS - days;
        if (remaining >= 0) {
            return new LicenseStatus(true, true, "DEMO PRO", "DEMO", "En " + remaining + " día(s)", "Modo demostración activo");
        }
        return new LicenseStatus(false, true, "DEMO VENCIDA", "DEMO", "Vencida", "Ingrese una licencia Autoguard válida");
    }

    public static LicenseStatus activate(Context context, String token) {
        LicenseStatus result = verifyToken(context, token == null ? "" : token.trim());
        if (result.active) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("token", token.trim()).apply();
        }
        return result;
    }

    private static LicenseStatus verifyToken(Context context, String token) {
        try {
            String[] parts = token.split("\\.");
            if (parts.length != 2) throw new IllegalArgumentException("Formato de licencia inválido");
            byte[] payloadBytes = Base64.decode(parts[0], Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
            byte[] signatureBytes = Base64.decode(parts[1], Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
            PublicKey publicKey = KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(Base64.decode(PUBLIC_KEY_B64, Base64.DEFAULT)));
            Signature signature = Signature.getInstance("SHA256withRSA");
            signature.initVerify(publicKey);
            signature.update(parts[0].getBytes(StandardCharsets.UTF_8));
            if (!signature.verify(signatureBytes)) throw new IllegalArgumentException("Firma de licencia inválida");

            String payload = new String(payloadBytes, StandardCharsets.UTF_8);
            Map<String, String> values = parsePayload(payload);
            String expiry = values.getOrDefault("expiry", "1970-01-01");
            LocalDate expiryDate = LocalDate.parse(expiry);
            if (expiryDate.isBefore(LocalDate.now(ZoneOffset.UTC))) throw new IllegalArgumentException("Licencia vencida");
            String boundDevice = values.getOrDefault("device", "ANY");
            if (!boundDevice.equalsIgnoreCase("ANY") && !boundDevice.equalsIgnoreCase(deviceId(context))) {
                throw new IllegalArgumentException("Licencia asignada a otro dispositivo");
            }
            return new LicenseStatus(true, false, values.getOrDefault("plan", "PRO"), values.getOrDefault("licenseId", "AUTOGUARD"), expiry, "Licencia Autoguard activa");
        } catch (Exception error) {
            return new LicenseStatus(false, false, "SIN LICENCIA", "N/D", "N/D", error.getMessage() == null ? "Licencia inválida" : error.getMessage());
        }
    }

    private static Map<String, String> parsePayload(String payload) {
        HashMap<String, String> map = new HashMap<>();
        for (String entry : payload.split(";")) {
            int index = entry.indexOf('=');
            if (index > 0) map.put(entry.substring(0, index).trim(), entry.substring(index + 1).trim());
        }
        return map;
    }
}
