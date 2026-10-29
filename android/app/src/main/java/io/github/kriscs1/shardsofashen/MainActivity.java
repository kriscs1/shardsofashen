package io.github.kriscs1.shardsofashen;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.window.OnBackInvokedDispatcher;

import org.json.JSONObject;

/** The app's one screen: a WebView, full screen and sideways. It starts on the start screen (assets/home: host a
 *  game, the games on this network, join by address) and goes to a game's own page to play. */
public class MainActivity extends Activity {
    static final String HOME = "file:///android_asset/home/index.html";

    private WebView web;
    private volatile String shown = HOME;           // (the page showing: the start screen may do more than a game's page)

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (BuildConfig.DEBUG) WebView.setWebContentsDebuggingEnabled(true);   // (chrome://inspect, for testing)
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);     // (the music and sounds start with the game)
        s.setAllowFileAccess(true);
        s.setTextZoom(100);
        web.setBackgroundColor(0xFF180E0A);
        web.addJavascriptInterface(new Bridge(), "DSApp");
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageStarted(WebView view, String url, Bitmap icon) {
                shown = url;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                // (the game couldn't be reached: back to the start screen, saying so)
                if (req.isForMainFrame() && !req.getUrl().toString().startsWith(HOME))
                    view.loadUrl(HOME + "#error=" + Uri.encode("Couldn't reach " + req.getUrl().getHost() + ": "
                        + err.getDescription()));
            }
        });
        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::back);
        }
        web.loadUrl(HOME);
    }

    private void back() {
        // (in a game: what's open there shuts first, then back to the start screen; on it: out of the app, a hosted
        // game going on)
        if (shown.startsWith(HOME)) {
            finish();
            return;
        }
        web.evaluateJavascript("!!(window.dsBack && window.dsBack())", (shut) -> {
            if (!"true".equals(shut)) web.loadUrl(HOME);
        });
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        back();
    }

    @Override
    public void onWindowFocusChanged(boolean focus) {
        super.onWindowFocusChanged(focus);
        if (focus) immersive();
    }

    @SuppressWarnings("deprecation")
    private void immersive() {
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(WindowInsets.Type.systemBars());
                c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }

    /** What the pages can ask of the app (window.DSApp). A game's page (from wherever it's served) may only go back to
     *  the start screen; the rest is the start screen's. */
    class Bridge {
        private boolean home() { return shown.startsWith(HOME); }

        private SharedPreferences prefs() { return getSharedPreferences("start", Context.MODE_PRIVATE); }

        @JavascriptInterface
        public void goHome() {
            runOnUiThread(() -> web.loadUrl(HOME));
        }

        @JavascriptInterface
        public String state() {
            if (!home()) return "{}";
            try {
                JSONObject o = new JSONObject();
                o.put("status", HostService.status);
                o.put("error", HostService.error);
                o.put("name", HostService.name);
                o.put("port", HostService.PORT);
                o.put("addresses", Net.addresses());
                o.put("device", Build.MODEL);
                o.put("version", BuildConfig.VERSION_NAME);
                return o.toString();
            } catch (Exception e) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void host(String name) {
            if (!home()) return;
            if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                requestPermissions(new String[] {Manifest.permission.POST_NOTIFICATIONS}, 1);
            Intent i = new Intent(MainActivity.this, HostService.class).putExtra("name", name);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(i);
            else startService(i);
        }

        @JavascriptInterface
        public void stopHosting() {
            if (!home()) return;
            startService(new Intent(MainActivity.this, HostService.class).setAction(HostService.STOP));
        }

        @JavascriptInterface
        public void find() {
            if (!home()) return;
            new Thread(() -> {
                String found = Net.find(1500).toString();
                runOnUiThread(() -> web.evaluateJavascript("window.onGames && window.onGames(" + found + ")", null));
            }, "find-games").start();
        }

        @JavascriptInterface
        public void play(String url) {
            if (!home()) return;
            runOnUiThread(() -> web.loadUrl(url));
        }

        @JavascriptInterface
        public String get(String key) {
            return home() ? prefs().getString(key, "") : "";
        }

        @JavascriptInterface
        public void set(String key, String value) {
            if (home()) prefs().edit().putString(key, value).apply();
        }
    }
}
