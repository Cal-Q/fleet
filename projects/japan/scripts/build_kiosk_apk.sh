#!/bin/bash
# scripts/build_kiosk_apk.sh — Compile & Package Japan Dedicated Web Kiosk APK
# Strictly <= 200 lines invariant. Zero-dependency offline Android Kiosk.
set -e
export PATH="/data/data/com.termux/files/usr/bin:$PATH"

BUILD_DIR="/data/data/com.termux/files/home/japan_kiosk_build"
rm -rf "$BUILD_DIR" 2>/dev/null || su -c "rm -rf $BUILD_DIR"
mkdir -p "$BUILD_DIR/src/it/calq/japan" "$BUILD_DIR/res/values" "$BUILD_DIR/res/drawable" "$BUILD_DIR/obj" "$BUILD_DIR/bin" "$BUILD_DIR/assets"

cat << 'EOF' > "$BUILD_DIR/AndroidManifest.xml"
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="it.calq.japan" android:versionCode="256" android:versionName="2.5.6">
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="29" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <application android:label="@string/app_name" android:icon="@drawable/icon" android:hardwareAccelerated="true" android:usesCleartextTraffic="true" android:requestLegacyExternalStorage="true" android:theme="@android:style/Theme.NoTitleBar.Fullscreen">
        <activity android:name=".MainActivity" android:label="@string/app_name" android:configChanges="orientation|screenSize|keyboardHidden|smallestScreenSize|screenLayout" android:screenOrientation="portrait" android:windowSoftInputMode="adjustResize" android:launchMode="singleTask">
            <intent-filter><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent-filter>
        </activity>
    </application>
</manifest>
EOF

cat << 'EOF' > "$BUILD_DIR/res/values/strings.xml"
<?xml version="1.0" encoding="utf-8"?><resources><string name="app_name">Japan Mastery</string></resources>
EOF

cat << 'EOF' > "$BUILD_DIR/src/it/calq/japan/MainActivity.java"
package it.calq.japan;

import android.app.Activity;
import android.os.*;
import android.view.*;
import android.webkit.*;
import android.graphics.Color;
import android.widget.FrameLayout;
import java.io.*;

public class MainActivity extends Activity {
    private WebView mWebView;
    private static final String PRIMARY_URL = "https://japan.calq.it/anki";
    private static final String FALLBACK_URL = "file:///android_asset/anki.html";
    private static final String SETTINGS_PATH = "/sdcard/JapanMastery/settings.json";
    private final Handler mH = new Handler(Looper.getMainLooper());
    private final Runnable mOff = new Runnable() { @Override public void run() { getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); } };
    private void touchWake() { getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); mH.removeCallbacks(mOff); mH.postDelayed(mOff, 180000); }
    @Override public void onUserInteraction() { super.onUserInteraction(); touchWake(); }
    @Override protected void onResume() { super.onResume(); touchWake(); }
    @Override protected void onPause() { super.onPause(); mH.removeCallbacks(mOff); getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        touchWake();
        getWindow().setBackgroundDrawableResource(android.R.color.black);

        mWebView = new WebView(this);
        mWebView.setBackgroundColor(Color.parseColor("#121212"));

        WebSettings s = mWebView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAppCacheEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setSupportZoom(false);

        if (Build.VERSION.SDK_INT >= 19) WebView.setWebContentsDebuggingEnabled(true);

        mWebView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public String getPersistedSettings() {
                try {
                    File f = new File(SETTINGS_PATH);
                    if (f.exists()) {
                        FileInputStream fis = new FileInputStream(f);
                        byte[] b = new byte[(int) f.length()];
                        fis.read(b); fis.close();
                        return new String(b, "UTF-8");
                    }
                } catch (Exception ignored) {}
                return "";
            }

            @JavascriptInterface
            public boolean savePersistedSettings(String json) {
                try {
                    File f = new File(SETTINGS_PATH);
                    f.getParentFile().mkdirs();
                    FileOutputStream fos = new FileOutputStream(f);
                    fos.write(json.getBytes("UTF-8"));
                    fos.close();
                    return true;
                } catch (Exception ignored) {}
                return false;
            }
        }, "AndroidSettingsBridge");

        mWebView.setWebChromeClient(new WebChromeClient());
        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) { return handleAssetIntercept(req.getUrl().toString()); }
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, String url) { return handleAssetIntercept(url); }

            private boolean isOnline() {
                try {
                    android.net.ConnectivityManager cm = (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
                    android.net.NetworkInfo ni = cm != null ? cm.getActiveNetworkInfo() : null;
                    return ni != null && ni.isConnected();
                } catch (Exception ignored) { return false; }
            }

            private WebResourceResponse handleAssetIntercept(String url) {
                if (isOnline()) return null; // Pass through to server for 100% OTA updates
                try {
                    if (url.contains("/anki") && !url.contains("/api/") && !url.contains("/static/") && !url.contains("/media/")) return new WebResourceResponse("text/html", "UTF-8", getAssets().open("anki.html"));
                    if (url.contains("anki_bundle.js")) return new WebResourceResponse("application/javascript", "UTF-8", getAssets().open("anki_bundle.js"));
                    if (url.contains("sw_anki.js")) return new WebResourceResponse("application/javascript", "UTF-8", getAssets().open("sw_anki.js"));
                    if (url.contains("tailwind.js")) return new WebResourceResponse("application/javascript", "UTF-8", getAssets().open("tailwind.js"));
                    if (url.contains("_HGSKyokashotai.ttf")) return new WebResourceResponse("font/ttf", "binary", getAssets().open("_HGSKyokashotai.ttf"));
                } catch (Exception ignored) {}
                return null;
            }

            @Override
            public void onReceivedError(WebView view, int errorCode, String desc, String failUrl) {}
        });

        FrameLayout layout = new FrameLayout(this);
        layout.addView(mWebView);
        setContentView(layout);
        hideSystemUI();
        mWebView.loadUrl(PRIMARY_URL);
    }

    private void hideSystemUI() {
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_STABLE |
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN |
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_FULLSCREEN
        );
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUI();
    }

    @Override
    public void onBackPressed() {
        if (mWebView != null && mWebView.canGoBack()) mWebView.goBack();
        else super.onBackPressed();
    }
}
EOF

# Copy assets into APK package
for src in "/data/data/com.termux/files/home/anki.html" "/data/data/com.termux/files/home/anki_standalone.html"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/anki.html" && break; done
for src in "/data/data/com.termux/files/home/anki_bundle.js" "/data/data/com.termux/files/home/japan/static/js/anki_bundle.js"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/anki_bundle.js" && break; done
for src in "/data/data/com.termux/files/home/sw_anki.js" "/data/data/com.termux/files/home/japan/sw_anki.js"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/sw_anki.js" && break; done
for src in "/data/data/com.termux/files/home/tailwind.js" "/data/data/com.termux/files/home/japan/static/js/tailwind.js"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/tailwind.js" && break; done
for src in "/data/data/com.termux/files/home/_HGSKyokashotai.ttf" "/data/data/com.termux/files/home/japan/static/fonts/_HGSKyokashotai.ttf"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/_HGSKyokashotai.ttf" && break; done
for src in "/data/data/com.termux/files/home/anki_settings.json" "/data/data/com.termux/files/home/japan/data/anki_settings.json"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/assets/anki_settings.json" && break; done
for src in "/data/data/com.termux/files/home/icon.png" "/data/data/com.termux/files/home/japan/static/icon-192.png"; do [ -f "$src" ] && cp "$src" "$BUILD_DIR/res/drawable/icon.png" && break; done

ANDROID_JAR="/data/data/com.termux/files/home/android-29.jar"
echo "[*] 1. Compiling resources with aapt..."
aapt package -f -m -J "$BUILD_DIR/src" -M "$BUILD_DIR/AndroidManifest.xml" -S "$BUILD_DIR/res" -A "$BUILD_DIR/assets" -I "$ANDROID_JAR"
echo "[*] 2. Compiling Java source files with ecj..."
ecj -d "$BUILD_DIR/obj" -sourcepath "$BUILD_DIR/src" -classpath "$ANDROID_JAR" $(find "$BUILD_DIR/src" -name "*.java")
echo "[*] 3. Converting bytecode to Dalvik dex with dx..."
dx --dex --output="$BUILD_DIR/bin/classes.dex" "$BUILD_DIR/obj"
echo "[*] 4. Packaging unaligned APK..."
aapt package -f -M "$BUILD_DIR/AndroidManifest.xml" -S "$BUILD_DIR/res" -A "$BUILD_DIR/assets" -I "$ANDROID_JAR" -F "$BUILD_DIR/bin/japan.unaligned.apk" "$BUILD_DIR/bin"
echo "[*] 5. Signing APK with debug key..."
KEYSTORE_PATH="/data/data/com.termux/files/home/japan_debug.keystore"
[ ! -f "$KEYSTORE_PATH" ] && keytool -genkey -v -keystore "$KEYSTORE_PATH" -alias debug -keyalg RSA -keysize 2048 -validity 10000 -storepass android -keypass android -dname "CN=AndroidDebug,O=Android,C=US"
apksigner sign --ks "$KEYSTORE_PATH" --ks-pass pass:android --ks-key-alias debug --key-pass pass:android --out "$BUILD_DIR/japan.apk" "$BUILD_DIR/bin/japan.unaligned.apk"
echo "[*] 6. Seeding external settings and installing APK..."
su -c "mkdir -p /sdcard/JapanMastery && [ -s /sdcard/JapanMastery/settings.json ] || cp $BUILD_DIR/assets/anki_settings.json /sdcard/JapanMastery/settings.json 2>/dev/null || true"
su -c "pm install -r -d -g $BUILD_DIR/japan.apk"
echo "[✓] SUCCESS: Japan Mastery Kiosk APK v2.5.5 installed!"
