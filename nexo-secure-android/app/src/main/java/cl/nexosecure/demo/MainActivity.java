package cl.nexosecure.demo;

import android.Manifest;
import android.app.Activity;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.media.MediaPlayer;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public final class MainActivity extends Activity {
    private static final int MIC_REQUEST = 70;
    private static final int BG = Color.rgb(8, 11, 20);
    private static final int PANEL = Color.rgb(17, 24, 39);
    private static final int PANEL_2 = Color.rgb(25, 34, 52);
    private static final int ACCENT = Color.rgb(124, 92, 252);
    private static final int TEXT = Color.rgb(247, 248, 255);
    private static final int MUTED = Color.rgb(156, 163, 175);
    private static final int GREEN = Color.rgb(52, 211, 153);

    private final ExecutorService io = Executors.newCachedThreadPool();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final Set<Long> rendered = new HashSet<>();

    private SharedPreferences preferences;
    private ScheduledExecutorService poller;
    private LinearLayout root;
    private LinearLayout messageList;
    private ScrollView messageScroll;
    private EditText messageInput;
    private Button voiceButton;

    private String serverUrl = "";
    private String token = "";
    private String myId = "";
    private String myName = "";
    private String groupSecret = "";
    private String peerId = "";
    private String peerName = "";
    private long lastMessageId;

    private MediaRecorder recorder;
    private File recordingFile;
    private long recordingStarted;
    private boolean recording;
    private boolean micPending;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);
        preferences = getSharedPreferences("nexo_secure_alpha", MODE_PRIVATE);
        loadSession();
        showEntry();
    }

    private void loadSession() {
        serverUrl = preferences.getString("server", "");
        token = preferences.getString("token", "");
        myId = preferences.getString("userId", "");
        myName = preferences.getString("name", "");
        groupSecret = preferences.getString("secret", "");
    }

    private void showEntry() {
        if (!serverUrl.isEmpty() && !token.isEmpty() && !myId.isEmpty() && !groupSecret.isEmpty()) {
            showContacts();
        } else {
            showSetup();
        }
    }

    private void newScreen() {
        stopPolling();
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);
        root.setPadding(dp(16), dp(12), dp(16), dp(12));
        setContentView(root);
    }

    private void showSetup() {
        newScreen();
        TextView brand = text("NEXO SECURE", 28, TEXT, Typeface.BOLD);
        brand.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(brand, matchWrap());
        TextView subtitle = text("Alpha multi-teléfono · Cifrado en el dispositivo", 14, MUTED, Typeface.NORMAL);
        subtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(subtitle, matchWrap());
        root.addView(space(24));

        LinearLayout card = panel();
        card.addView(text("Conectar este teléfono", 20, TEXT, Typeface.BOLD), matchWrap());
        card.addView(label("Dirección del servidor"));
        EditText server = input("http://192.168.1.25:8080",
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        server.setText(serverUrl);
        card.addView(server, matchWrap());

        card.addView(label("Código de invitación"));
        EditText invite = input("NEXO-001",
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
        card.addView(invite, matchWrap());

        card.addView(label("Tu nombre visible"));
        EditText name = input("Esteban",
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        name.setText(myName);
        card.addView(name, matchWrap());

        card.addView(label("Clave privada del grupo"));
        EditText secret = input("La misma clave en todos los teléfonos",
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        secret.setText(groupSecret);
        card.addView(secret, matchWrap());

        TextView warning = text("La clave privada no se envía al servidor. Debe ser idéntica en los teléfonos que conversarán y tener al menos 8 caracteres.",
                13, MUTED, Typeface.NORMAL);
        warning.setPadding(0, dp(10), 0, dp(12));
        card.addView(warning, matchWrap());

        Button connect = primaryButton("REGISTRAR Y CONECTAR");
        card.addView(connect, matchWrap());
        root.addView(card, matchWrap());

        ProgressBar progress = new ProgressBar(this);
        progress.setVisibility(View.GONE);
        root.addView(progress, centerWrap());

        connect.setOnClickListener(view -> {
            String address = server.getText().toString().trim();
            String invitation = invite.getText().toString().trim();
            String displayName = name.getText().toString().trim();
            String privateSecret = secret.getText().toString();
            if (address.isEmpty() || invitation.isEmpty() || displayName.isEmpty() || privateSecret.length() < 8) {
                toast("Completa todos los datos. La clave debe tener 8 caracteres o más.");
                return;
            }
            connect.setEnabled(false);
            progress.setVisibility(View.VISIBLE);
            io.execute(() -> register(address, invitation, displayName, privateSecret,
                    connect, progress));
        });
    }

    private void register(String address, String invitation, String displayName,
                          String privateSecret, Button connect, ProgressBar progress) {
        try {
            String deviceId = preferences.getString("deviceId", "");
            if (deviceId.isEmpty()) deviceId = UUID.randomUUID().toString();
            JSONObject request = new JSONObject()
                    .put("Invite", invitation)
                    .put("DisplayName", displayName)
                    .put("DeviceID", deviceId);
            JSONObject response = new ApiClient(address, "").post("/api/register", request);
            JSONObject user = response.getJSONObject("user");
            preferences.edit()
                    .putString("server", address)
                    .putString("token", response.getString("token"))
                    .putString("userId", user.getString("id"))
                    .putString("name", user.getString("displayName"))
                    .putString("secret", privateSecret)
                    .putString("deviceId", deviceId)
                    .apply();
            ui.post(() -> {
                loadSession();
                showContacts();
            });
        } catch (Exception error) {
            ui.post(() -> {
                progress.setVisibility(View.GONE);
                connect.setEnabled(true);
                toast("No se pudo registrar: " + cleanError(error));
            });
        }
    }

    private void showContacts() {
        newScreen();
        root.addView(topBar("Nexo Secure", "Salir", view -> logout()), matchWrap());
        TextView identity = text("● Conectado como " + myName, 14, GREEN, Typeface.BOLD);
        identity.setPadding(dp(4), dp(8), 0, dp(8));
        root.addView(identity, matchWrap());
        TextView server = text("Servidor: " + serverUrl, 12, MUTED, Typeface.NORMAL);
        server.setPadding(dp(4), 0, 0, dp(12));
        root.addView(server, matchWrap());

        Button refresh = secondaryButton("ACTUALIZAR CONTACTOS");
        root.addView(refresh, matchWrap());
        LinearLayout list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(list, matchWrap());
        root.addView(scroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        refresh.setOnClickListener(view -> loadContacts(list));
        loadContacts(list);
    }

    private void loadContacts(LinearLayout list) {
        list.removeAllViews();
        TextView loading = text("Buscando teléfonos autorizados…", 15, MUTED, Typeface.NORMAL);
        loading.setPadding(dp(8), dp(20), dp(8), dp(20));
        list.addView(loading, matchWrap());
        io.execute(() -> {
            try {
                JSONArray array = new ApiClient(serverUrl, token)
                        .get("/api/contacts").getJSONArray("contacts");
                List<Contact> contacts = new ArrayList<>();
                for (int index = 0; index < array.length(); index++) {
                    JSONObject object = array.getJSONObject(index);
                    contacts.add(new Contact(object.getString("id"), object.getString("displayName")));
                }
                ui.post(() -> renderContacts(list, contacts));
            } catch (Exception error) {
                ui.post(() -> {
                    list.removeAllViews();
                    TextView message = text("No se pudo conectar: " + cleanError(error),
                            15, Color.rgb(248, 113, 113), Typeface.NORMAL);
                    message.setPadding(dp(8), dp(20), dp(8), dp(20));
                    list.addView(message, matchWrap());
                });
            }
        });
    }

    private void renderContacts(LinearLayout list, List<Contact> contacts) {
        list.removeAllViews();
        if (contacts.isEmpty()) {
            TextView empty = text("Aún no hay otros teléfonos registrados. Instala esta APK en otro celular y usa otra invitación.",
                    15, MUTED, Typeface.NORMAL);
            empty.setPadding(dp(8), dp(24), dp(8), dp(24));
            list.addView(empty, matchWrap());
            return;
        }
        for (Contact contact : contacts) {
            Button button = new Button(this);
            button.setAllCaps(false);
            button.setText("●  " + contact.name + "\n    Teléfono autorizado");
            button.setTextColor(TEXT);
            button.setTextSize(17);
            button.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
            button.setBackgroundColor(PANEL);
            button.setPadding(dp(16), dp(14), dp(16), dp(14));
            LinearLayout.LayoutParams params = matchWrap();
            params.setMargins(0, dp(7), 0, dp(7));
            list.addView(button, params);
            button.setOnClickListener(view -> showChat(contact));
        }
    }

    private void showChat(Contact contact) {
        peerId = contact.id;
        peerName = contact.name;
        lastMessageId = 0;
        rendered.clear();
        newScreen();
        root.addView(topBar("‹  " + peerName, "Info",
                view -> toast("Canal cifrado Alpha AES-256-GCM")), matchWrap());
        TextView secure = text("🔒 Cifrado de extremo a extremo Alpha", 13, GREEN, Typeface.BOLD);
        secure.setGravity(Gravity.CENTER);
        secure.setPadding(0, dp(6), 0, dp(8));
        root.addView(secure, matchWrap());

        messageList = new LinearLayout(this);
        messageList.setOrientation(LinearLayout.VERTICAL);
        messageList.setPadding(0, dp(8), 0, dp(8));
        messageScroll = new ScrollView(this);
        messageScroll.addView(messageList, matchWrap());
        root.addView(messageScroll, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout composer = new LinearLayout(this);
        composer.setOrientation(LinearLayout.HORIZONTAL);
        composer.setGravity(Gravity.CENTER_VERTICAL);
        messageInput = input("Mensaje privado",
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                        | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        composer.addView(messageInput, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button send = primaryButton("ENVIAR");
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(
                dp(96), ViewGroup.LayoutParams.WRAP_CONTENT);
        sendParams.setMargins(dp(8), 0, 0, 0);
        composer.addView(send, sendParams);
        root.addView(composer, matchWrap());

        voiceButton = secondaryButton("🎙 INICIAR NOTA DE VOZ");
        root.addView(voiceButton, matchWrap());
        send.setOnClickListener(view -> sendText());
        voiceButton.setOnClickListener(view -> toggleRecording());
        startPolling();
    }

    private void sendText() {
        String text = messageInput.getText().toString().trim();
        if (text.isEmpty()) return;
        messageInput.setText("");
        io.execute(() -> {
            try {
                CryptoBox.Encrypted encrypted = CryptoBox.encryptText(
                        groupSecret, myId, peerId, text);
                JSONObject message = new JSONObject()
                        .put("to", peerId)
                        .put("kind", "text")
                        .put("nonce", encrypted.nonce)
                        .put("body", encrypted.ciphertextBase64());
                new ApiClient(serverUrl, token).post("/api/messages", message);
                pollMessages();
            } catch (Exception error) {
                ui.post(() -> toast("No se pudo enviar: " + cleanError(error)));
            }
        });
    }

    private void startPolling() {
        stopPolling();
        poller = Executors.newSingleThreadScheduledExecutor();
        poller.scheduleWithFixedDelay(this::pollMessages, 0, 2, TimeUnit.SECONDS);
    }

    private void stopPolling() {
        if (poller != null) {
            poller.shutdownNow();
            poller = null;
        }
    }

    private void pollMessages() {
        if (peerId.isEmpty() || token.isEmpty()) return;
        try {
            JSONObject response = new ApiClient(serverUrl, token).get(
                    "/api/messages?peer=" + peerId + "&after=" + lastMessageId);
            JSONArray array = response.getJSONArray("messages");
            List<MessageView> newMessages = new ArrayList<>();
            long maximum = lastMessageId;
            for (int index = 0; index < array.length(); index++) {
                JSONObject object = array.getJSONObject(index);
                long id = object.getLong("id");
                maximum = Math.max(maximum, id);
                if (rendered.contains(id)) continue;
                boolean mine = object.getString("from").equals(myId);
                String kind = object.getString("kind");
                String nonce = object.getString("nonce");
                if ("text".equals(kind)) {
                    String plain;
                    try {
                        plain = CryptoBox.decryptText(groupSecret, myId, peerId,
                                nonce, object.getString("body"));
                    } catch (Exception cryptoError) {
                        plain = "⚠ No se pudo descifrar. Revisa la clave privada del grupo.";
                    }
                    newMessages.add(MessageView.text(id, mine, plain));
                } else if ("voice".equals(kind)) {
                    newMessages.add(MessageView.voice(id, mine, nonce,
                            object.getString("mediaId"), object.optInt("durationMs", 0)));
                }
            }
            lastMessageId = maximum;
            if (!newMessages.isEmpty()) {
                ui.post(() -> {
                    for (MessageView message : newMessages) {
                        if (rendered.add(message.id)) renderMessage(message);
                    }
                    messageScroll.post(() -> messageScroll.fullScroll(View.FOCUS_DOWN));
                });
            }
        } catch (Exception ignored) {
            // La aplicación vuelve a intentar automáticamente.
        }
    }

    private void renderMessage(MessageView message) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(message.mine ? Gravity.END : Gravity.START);
        row.setPadding(0, dp(4), 0, dp(4));
        if ("text".equals(message.kind)) {
            TextView bubble = text(message.text, 16, TEXT, Typeface.NORMAL);
            bubble.setBackgroundColor(message.mine ? ACCENT : PANEL_2);
            bubble.setPadding(dp(14), dp(10), dp(14), dp(10));
            row.addView(bubble, new LinearLayout.LayoutParams(
                    dp(290), ViewGroup.LayoutParams.WRAP_CONTENT));
        } else {
            Button play = new Button(this);
            play.setAllCaps(false);
            play.setText("▶  Nota de voz · " + Math.max(1, message.durationMs / 1000) + " s");
            play.setTextColor(TEXT);
            play.setTextSize(15);
            play.setBackgroundColor(message.mine ? ACCENT : PANEL_2);
            play.setPadding(dp(14), dp(8), dp(14), dp(8));
            play.setOnClickListener(view -> playVoice(message, play));
            row.addView(play, new LinearLayout.LayoutParams(
                    dp(250), ViewGroup.LayoutParams.WRAP_CONTENT));
        }
        messageList.addView(row, matchWrap());
    }

    private void toggleRecording() {
        if (recording) stopAndSendRecording();
        else requestAndStartRecording();
    }

    private void requestAndStartRecording() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            micPending = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_REQUEST);
            return;
        }
        startRecording();
    }

    private void startRecording() {
        try {
            recordingFile = new File(getCacheDir(),
                    "nexo-voice-" + System.currentTimeMillis() + ".m4a");
            recorder = new MediaRecorder();
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioEncodingBitRate(64_000);
            recorder.setAudioSamplingRate(44_100);
            recorder.setOutputFile(recordingFile.getAbsolutePath());
            recorder.prepare();
            recorder.start();
            recordingStarted = System.currentTimeMillis();
            recording = true;
            voiceButton.setText("■ DETENER Y ENVIAR");
            voiceButton.setBackgroundColor(Color.rgb(190, 24, 93));
        } catch (Exception error) {
            releaseRecorder();
            toast("No se pudo iniciar el micrófono: " + cleanError(error));
        }
    }

    private void stopAndSendRecording() {
        long duration = Math.max(500, System.currentTimeMillis() - recordingStarted);
        try {
            recorder.stop();
        } catch (Exception error) {
            toast("La grabación fue demasiado corta");
            releaseRecorder();
            resetVoiceButton();
            return;
        }
        releaseRecorder();
        resetVoiceButton();
        File voiceFile = recordingFile;
        io.execute(() -> uploadVoice(voiceFile, duration));
    }

    private void uploadVoice(File voiceFile, long duration) {
        try {
            byte[] plain = Files.readAllBytes(voiceFile.toPath());
            CryptoBox.Encrypted encrypted = CryptoBox.encrypt(
                    groupSecret, myId, peerId, plain);
            JSONObject upload = new ApiClient(serverUrl, token)
                    .postBytes("/api/media", encrypted.ciphertext);
            JSONObject message = new JSONObject()
                    .put("to", peerId)
                    .put("kind", "voice")
                    .put("nonce", encrypted.nonce)
                    .put("mediaId", upload.getString("mediaId"))
                    .put("durationMs", duration);
            new ApiClient(serverUrl, token).post("/api/messages", message);
            Files.deleteIfExists(voiceFile.toPath());
            pollMessages();
        } catch (Exception error) {
            ui.post(() -> toast("No se pudo enviar la nota de voz: " + cleanError(error)));
        }
    }

    private void playVoice(MessageView message, Button button) {
        button.setEnabled(false);
        button.setText("Descargando y descifrando…");
        io.execute(() -> {
            try {
                byte[] encrypted = new ApiClient(serverUrl, token)
                        .getBytes("/api/media/" + message.mediaId);
                byte[] plain = CryptoBox.decrypt(groupSecret, myId, peerId,
                        message.nonce, encrypted);
                File file = new File(getCacheDir(), "play-" + message.id + ".m4a");
                Files.write(file.toPath(), plain);
                ui.post(() -> playLocalFile(file, button));
            } catch (Exception error) {
                ui.post(() -> {
                    button.setEnabled(true);
                    button.setText("⚠ No se pudo descifrar");
                    toast(cleanError(error));
                });
            }
        });
    }

    private void playLocalFile(File file, Button button) {
        try {
            MediaPlayer player = new MediaPlayer();
            player.setDataSource(file.getAbsolutePath());
            player.setOnCompletionListener(mediaPlayer -> {
                mediaPlayer.release();
                file.delete();
                button.setEnabled(true);
                button.setText("▶  Reproducir nuevamente");
            });
            player.prepare();
            player.start();
            button.setText("🔊 Reproduciendo…");
        } catch (Exception error) {
            button.setEnabled(true);
            button.setText("⚠ Error de reproducción");
        }
    }

    private void releaseRecorder() {
        if (recorder != null) {
            try { recorder.reset(); } catch (Exception ignored) {}
            try { recorder.release(); } catch (Exception ignored) {}
            recorder = null;
        }
        recording = false;
    }

    private void resetVoiceButton() {
        recording = false;
        if (voiceButton != null) {
            voiceButton.setText("🎙 INICIAR NOTA DE VOZ");
            voiceButton.setBackgroundColor(PANEL_2);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == MIC_REQUEST && micPending) {
            micPending = false;
            if (grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startRecording();
            } else {
                toast("El micrófono es necesario para notas de voz.");
            }
        }
    }

    private void logout() {
        preferences.edit().clear().apply();
        serverUrl = token = myId = myName = groupSecret = peerId = peerName = "";
        showSetup();
    }

    @Override
    public void onBackPressed() {
        if (!peerId.isEmpty()) {
            peerId = peerName = "";
            releaseRecorder();
            showContacts();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        stopPolling();
        releaseRecorder();
        io.shutdownNow();
        super.onDestroy();
    }

    private LinearLayout topBar(String title, String action,
                                View.OnClickListener listener) {
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.addView(text(title, 22, TEXT, Typeface.BOLD),
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button button = secondaryButton(action);
        button.setOnClickListener(listener);
        bar.addView(button, new LinearLayout.LayoutParams(
                dp(88), ViewGroup.LayoutParams.WRAP_CONTENT));
        return bar;
    }

    private LinearLayout panel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setBackgroundColor(PANEL);
        panel.setPadding(dp(18), dp(18), dp(18), dp(18));
        return panel;
    }

    private TextView label(String value) {
        TextView label = text(value, 13, MUTED, Typeface.BOLD);
        label.setPadding(0, dp(14), 0, dp(5));
        return label;
    }

    private EditText input(String hint, int inputType) {
        EditText input = new EditText(this);
        input.setHint(hint);
        input.setHintTextColor(Color.rgb(107, 114, 128));
        input.setTextColor(TEXT);
        input.setTextSize(16);
        input.setSingleLine((inputType & InputType.TYPE_TEXT_FLAG_MULTI_LINE) == 0);
        input.setInputType(inputType);
        input.setBackgroundColor(PANEL_2);
        input.setPadding(dp(12), dp(10), dp(12), dp(10));
        return input;
    }

    private Button primaryButton(String value) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextColor(Color.WHITE);
        button.setTextSize(14);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setBackgroundColor(ACCENT);
        button.setPadding(dp(10), dp(9), dp(10), dp(9));
        return button;
    }

    private Button secondaryButton(String value) {
        Button button = new Button(this);
        button.setText(value);
        button.setTextColor(TEXT);
        button.setTextSize(13);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setBackgroundColor(PANEL_2);
        button.setPadding(dp(8), dp(8), dp(8), dp(8));
        return button;
    }

    private TextView text(String value, int size, int color, int style) {
        TextView text = new TextView(this);
        text.setText(value);
        text.setTextColor(color);
        text.setTextSize(size);
        text.setTypeface(Typeface.DEFAULT, style);
        return text;
    }

    private Space space(int height) {
        Space space = new Space(this);
        space.setLayoutParams(new LinearLayout.LayoutParams(1, dp(height)));
        return space;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams centerWrap() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.gravity = Gravity.CENTER_HORIZONTAL;
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void toast(String value) {
        Toast.makeText(this, value, Toast.LENGTH_LONG).show();
    }

    private static String cleanError(Exception error) {
        String message = error.getMessage();
        if (message == null || message.trim().isEmpty()) {
            return error.getClass().getSimpleName();
        }
        return message.replace("java.net.", "").replace("java.io.", "");
    }

    private static final class Contact {
        final String id;
        final String name;

        Contact(String id, String name) {
            this.id = id;
            this.name = name;
        }
    }

    private static final class MessageView {
        final long id;
        final boolean mine;
        final String kind;
        final String text;
        final String nonce;
        final String mediaId;
        final int durationMs;

        private MessageView(long id, boolean mine, String kind, String text,
                            String nonce, String mediaId, int durationMs) {
            this.id = id;
            this.mine = mine;
            this.kind = kind;
            this.text = text;
            this.nonce = nonce;
            this.mediaId = mediaId;
            this.durationMs = durationMs;
        }

        static MessageView text(long id, boolean mine, String text) {
            return new MessageView(id, mine, "text", text, "", "", 0);
        }

        static MessageView voice(long id, boolean mine, String nonce,
                                 String mediaId, int durationMs) {
            return new MessageView(id, mine, "voice", "", nonce, mediaId, durationMs);
        }
    }
}
