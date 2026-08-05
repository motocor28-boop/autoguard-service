package cl.nexosecure.demo;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.zip.GZIPInputStream;

final class HtmlBundle {
    private HtmlBundle() {}
    private static final String DATA =
        "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" +
        "nhzz//PNR/8HE3+iGI0zAAA=";
    static String html() {
        byte[] compressed = Base64.getDecoder().decode(DATA);
        try (GZIPInputStream gzip = new GZIPInputStream(new ByteArrayInputStream(compressed)); ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int read;
            while ((read = gzip.read(buffer)) != -1) output.write(buffer, 0, read);
            return output.toString(StandardCharsets.UTF_8.name());
        } catch (IOException error) { throw new IllegalStateException("No se pudo cargar la interfaz", error); }
    }
}
