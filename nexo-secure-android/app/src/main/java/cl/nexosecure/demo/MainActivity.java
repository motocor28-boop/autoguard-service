package cl.nexosecure.demo;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final int MICROPHONE_REQUEST = 41;
    private static final String APP_ORIGIN = "https://nexo.local/";

    private WebView webView;
    private PermissionRequest pendingWebPermission;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(8, 11, 20));
        getWindow().setNavigationBarColor(Color.rgb(8, 11, 20));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(8, 11, 20));
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setUserAgentString(settings.getUserAgentString() + " NexoSecureAndroid/0.2");

        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(() -> handleWebPermission(request));
            }
        });

        if (savedInstanceState == null) {
            webView.loadDataWithBaseURL(APP_ORIGIN, HtmlBundle.html(), "text/html", "UTF-8", null);
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    private void handleWebPermission(PermissionRequest request) {
        boolean asksAudio = false;
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)) {
                asksAudio = true;
                break;
            }
        }

        Uri origin = request.getOrigin();
        boolean trustedOrigin = origin != null
            && "https".equals(origin.getScheme())
            && "nexo.local".equals(origin.getHost());

        if (!asksAudio || !trustedOrigin) {
            request.deny();
            return;
        }

        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            pendingWebPermission = request;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MICROPHONE_REQUEST);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != MICROPHONE_REQUEST || pendingWebPermission == null) return;

        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            pendingWebPermission.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            pendingWebPermission.deny();
            Toast.makeText(this, "El micrófono es necesario para notas de voz y radio PTT.", Toast.LENGTH_LONG).show();
        }
        pendingWebPermission = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        webView.evaluateJavascript(
            "(() => { const d=[...document.querySelectorAll('dialog[open]')].pop(); if(d){d.close();return 'closed'} return 'none'; })()",
            result -> {
                if ("\"closed\"".equals(result)) return;
                if (webView.canGoBack()) webView.goBack(); else super.onBackPressed();
            }
        );
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.stopLoading();
            webView.destroy();
        }
        super.onDestroy();
    }
}
