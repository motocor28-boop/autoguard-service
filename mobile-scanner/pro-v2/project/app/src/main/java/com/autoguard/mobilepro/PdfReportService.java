package com.autoguard.mobilepro;

import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import java.io.OutputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

public final class PdfReportService {
    private PdfReportService() {}

    public static Uri createReport(
            Context context,
            Map<String, String> vehicle,
            ObdClient.SessionInfo session,
            List<ObdClient.DtcEntry> dtcs,
            Map<String, Double> sensors,
            LicenseManager.LicenseStatus license
    ) throws Exception {
        String plate = vehicle.getOrDefault("plate", "SIN_PATENTE").replaceAll("[^A-Za-z0-9_-]", "_");
        String fileName = "Informe_Autoguard_" + plate + "_" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmm")) + ".pdf";

        ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, fileName);
        values.put(MediaStore.MediaColumns.MIME_TYPE, "application/pdf");
        values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Autoguard");
        ContentResolver resolver = context.getContentResolver();
        Uri uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("No fue posible crear el archivo PDF.");

        PdfDocument document = new PdfDocument();
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        Paint title = new Paint(Paint.ANTI_ALIAS_FLAG);
        title.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
        title.setColor(Color.rgb(249, 115, 22));
        title.setTextSize(26f);
        Paint heading = new Paint(Paint.ANTI_ALIAS_FLAG);
        heading.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
        heading.setColor(Color.rgb(31, 41, 55));
        heading.setTextSize(15f);
        paint.setColor(Color.rgb(17, 24, 39));
        paint.setTextSize(11.5f);

        int pageNumber = 1;
        PdfDocument.Page page = document.startPage(new PdfDocument.PageInfo.Builder(595, 842, pageNumber).create());
        Canvas canvas = page.getCanvas();
        int y = 48;
        canvas.drawText("AUTOGUARD SERVICIOS", 42, y, title);
        y += 26;
        heading.setTextSize(14f);
        canvas.drawText("Informe técnico móvil profesional", 42, y, heading);
        y += 20;
        paint.setColor(Color.DKGRAY);
        canvas.drawText("Fecha: " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm")), 42, y, paint);
        y += 14;
        canvas.drawText("Licencia: " + license.plan + " | " + license.licenseId + " | " + license.expires, 42, y, paint);
        y += 24;

        y = section(canvas, heading, paint, "CLIENTE Y VEHÍCULO", y);
        y = line(canvas, paint, "Cliente", vehicle.getOrDefault("client", "No informado"), y);
        y = line(canvas, paint, "Patente", vehicle.getOrDefault("plate", "No informada"), y);
        y = line(canvas, paint, "Marca / modelo", vehicle.getOrDefault("brand", "") + " " + vehicle.getOrDefault("model", ""), y);
        y = line(canvas, paint, "Año / kilometraje", vehicle.getOrDefault("year", "") + " / " + vehicle.getOrDefault("mileage", ""), y);
        y = line(canvas, paint, "VIN", vehicle.getOrDefault("vin", session == null ? "" : session.vin), y);
        y = line(canvas, paint, "Síntomas", vehicle.getOrDefault("symptoms", "No informados"), y);
        y += 8;

        y = section(canvas, heading, paint, "CONEXIÓN OBD-II", y);
        y = line(canvas, paint, "Adaptador", session == null ? "No conectado" : session.adapter, y);
        y = line(canvas, paint, "Protocolo", session == null ? "N/D" : session.protocol, y);
        y += 8;

        y = section(canvas, heading, paint, "CÓDIGOS DTC", y);
        if (dtcs == null || dtcs.isEmpty()) {
            y = line(canvas, paint, "Resultado", "Sin códigos registrados", y);
        } else {
            for (ObdClient.DtcEntry dtc : dtcs) {
                if (y > 790) {
                    document.finishPage(page);
                    page = document.startPage(new PdfDocument.PageInfo.Builder(595, 842, ++pageNumber).create());
                    canvas = page.getCanvas();
                    y = 48;
                }
                canvas.drawText(dtc.code + " | " + dtc.state + " | " + dtc.description, 50, y, paint);
                y += 15;
            }
        }
        y += 8;

        y = section(canvas, heading, paint, "DATOS EN VIVO", y);
        if (sensors == null || sensors.isEmpty()) {
            y = line(canvas, paint, "Resultado", "Sin lecturas guardadas", y);
        } else {
            Map<String, SensorSpec> catalog = SensorSpec.catalog();
            for (Map.Entry<String, Double> entry : sensors.entrySet()) {
                if (y > 790) {
                    document.finishPage(page);
                    page = document.startPage(new PdfDocument.PageInfo.Builder(595, 842, ++pageNumber).create());
                    canvas = page.getCanvas();
                    y = 48;
                }
                SensorSpec spec = catalog.get(entry.getKey());
                String label = spec == null ? entry.getKey() : spec.label;
                String value = spec == null ? String.valueOf(entry.getValue()) : spec.format(entry.getValue());
                y = line(canvas, paint, label, value, y);
            }
        }

        y += 10;
        heading.setTextSize(12f);
        canvas.drawText("Conclusión Autoguard", 42, y, heading);
        y += 16;
        paint.setColor(Color.DKGRAY);
        canvas.drawText("Este informe registra información OBD-II y pruebas guiadas. Debe complementarse con inspección técnica presencial.", 42, y, paint);

        document.finishPage(page);
        try (OutputStream output = resolver.openOutputStream(uri)) {
            if (output == null) throw new IllegalStateException("No fue posible abrir el archivo PDF.");
            document.writeTo(output);
        } finally {
            document.close();
        }
        return uri;
    }

    private static int section(Canvas canvas, Paint heading, Paint paint, String text, int y) {
        heading.setTextSize(13f);
        canvas.drawText(text, 42, y, heading);
        paint.setColor(Color.rgb(249, 115, 22));
        paint.setStrokeWidth(2f);
        canvas.drawLine(42, y + 5, 552, y + 5, paint);
        paint.setColor(Color.DKGRAY);
        return y + 22;
    }

    private static int line(Canvas canvas, Paint paint, String label, String value, int y) {
        canvas.drawText(label + ": " + (value == null || value.isBlank() ? "N/D" : value), 50, y, paint);
        return y + 15;
    }
}
