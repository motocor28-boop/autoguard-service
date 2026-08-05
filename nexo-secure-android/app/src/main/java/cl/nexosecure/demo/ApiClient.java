package cl.nexosecure.demo;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

final class ApiClient {
    private final String baseUrl;
    private final String token;

    ApiClient(String baseUrl, String token) {
        String value = baseUrl == null ? "" : baseUrl.trim();
        while (value.endsWith("/")) value = value.substring(0, value.length() - 1);
        this.baseUrl = value;
        this.token = token == null ? "" : token;
    }

    JSONObject get(String path) throws Exception {
        return readJson(open("GET", path));
    }

    JSONObject post(String path, JSONObject body) throws Exception {
        HttpURLConnection connection = open("POST", path);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setDoOutput(true);
        byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(bytes);
        }
        return readJson(connection);
    }

    JSONObject postBytes(String path, byte[] body) throws Exception {
        HttpURLConnection connection = open("POST", path);
        connection.setRequestProperty("Content-Type", "application/octet-stream");
        connection.setFixedLengthStreamingMode(body.length);
        connection.setDoOutput(true);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }
        return readJson(connection);
    }

    byte[] getBytes(String path) throws Exception {
        HttpURLConnection connection = open("GET", path);
        int status = connection.getResponseCode();
        byte[] bytes = readAll(status >= 200 && status < 300
                ? connection.getInputStream() : connection.getErrorStream());
        connection.disconnect();
        if (status < 200 || status >= 300) {
            throw new IOException("Error del servidor " + status + ": "
                    + new String(bytes, StandardCharsets.UTF_8));
        }
        return bytes;
    }

    private HttpURLConnection open(String method, String path) throws Exception {
        if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
            throw new IllegalArgumentException("La dirección debe comenzar con http:// o https://");
        }
        HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(10_000);
        connection.setReadTimeout(20_000);
        connection.setUseCaches(false);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("User-Agent", "NexoSecureAlphaAndroid/1.0");
        if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
        return connection;
    }

    private JSONObject readJson(HttpURLConnection connection) throws Exception {
        int status = connection.getResponseCode();
        byte[] bytes = readAll(status >= 200 && status < 300
                ? connection.getInputStream() : connection.getErrorStream());
        connection.disconnect();
        String text = new String(bytes, StandardCharsets.UTF_8);
        JSONObject object = text.isEmpty() ? new JSONObject() : new JSONObject(text);
        if (status < 200 || status >= 300) {
            throw new IOException(object.optString("error", "Error del servidor " + status));
        }
        return object;
    }

    private static byte[] readAll(InputStream input) throws IOException {
        if (input == null) return new byte[0];
        try (InputStream source = input; ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = source.read(buffer)) != -1) output.write(buffer, 0, count);
            return output.toByteArray();
        }
    }
}
