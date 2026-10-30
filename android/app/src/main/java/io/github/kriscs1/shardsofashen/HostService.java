package io.github.kriscs1.shardsofashen;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;

/** A game hosted on this phone: the game's server (ds_host.py, in Python), going on while the phone does other
 *  things, with a notification to say so (and to stop it). Players on the same network join it on PORT. */
public class HostService extends Service {
    static final int PORT = 8484;
    static final String STOP = "stop";
    static final String CHANNEL = "hosting";

    static volatile String status = "off";          // off, unpacking, starting, on, stopping, error
    static volatile String error = "";
    static volatile String name = "";
    static volatile boolean solo = false;           // (a game of your own: this phone only, its own world)
    static volatile String mode = "local";          // solo, local (this network) or remote (the central server lists it)
    static volatile String central = "";            // (the central server: accounts, the remote list)

    private PowerManager.WakeLock wake;
    private WifiManager.WifiLock wifi;
    private WifiManager.MulticastLock multicast;

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public int onStartCommand(Intent intent, int flags, int id) {
        if (intent != null && STOP.equals(intent.getAction())) {
            unhost();
            return START_NOT_STICKY;
        }
        if (!status.equals("off") && !status.equals("error")) return START_NOT_STICKY;
        String wanted = intent != null ? intent.getStringExtra("name") : null;
        solo = intent != null && intent.getBooleanExtra("solo", false);
        String m = intent != null ? intent.getStringExtra("mode") : null;
        mode = solo ? "solo" : "remote".equals(m) ? "remote" : "local";
        String c = intent != null ? intent.getStringExtra("central") : null;
        central = c == null ? "" : c.trim();
        name = solo ? "Your own game" : wanted == null || wanted.trim().isEmpty() ? "Shards of Ashen on " + Build.MODEL
            : wanted.trim();
        error = "";
        status = "unpacking";
        foreground("Starting " + name + "...");
        hold();
        new Thread(() -> {
            try {
                File root = GameFiles.unpack(this);
                status = "starting";
                if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                PyObject host = Python.getInstance().getModule("ds_host");
                host.callAttr("start", root.getPath(), new File(getFilesDir(), solo ? "solo.db" : "world.db").getPath(),
                    name, PORT, BuildConfig.VERSION_CODE, solo, mode, central);
                status = "on";
                foreground(solo ? "Your own game is running" : "remote".equals(mode)
                    ? name + ": listed by the central server" : name + ": others on this network can join it");
            } catch (Throwable t) {
                error = String.valueOf(t.getMessage() != null ? t.getMessage() : t);
                status = "error";
                stopSelf();
            }
        }, "host").start();
        return START_NOT_STICKY;
    }

    private void unhost() {
        // (stopped: everyone's saved and the world too, then the service goes)
        if (!status.equals("on")) {
            if (!status.equals("error")) status = "off";
            stopSelf();
            return;
        }
        status = "stopping";
        foreground("Saving " + name + "...");
        new Thread(() -> {
            try {
                Python.getInstance().getModule("ds_host").callAttr("stop");
            } catch (Throwable ignored) { }
            status = "off";
            stopSelf();
        }, "unhost").start();
    }

    @Override
    public void onDestroy() {
        if (status.equals("on")) {                   // (the system took it away: save what can be saved)
            status = "stopping";
            new Thread(() -> {
                try { Python.getInstance().getModule("ds_host").callAttr("stop"); } catch (Throwable ignored) { }
                status = "off";
            }, "unhost").start();
        }
        release();
        super.onDestroy();
    }

    private void hold() {
        // (the phone stays awake and on its Wi-Fi while it hosts, and hears the network's "who's there?")
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wake = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "shardsofashen:host");
        wake.acquire();
        WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
        if (wm != null) {
            wifi = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "shardsofashen:host");
            wifi.acquire();
            multicast = wm.createMulticastLock("shardsofashen:find");
            multicast.acquire();
        }
    }

    private void release() {
        if (wake != null && wake.isHeld()) wake.release();
        if (wifi != null && wifi.isHeld()) wifi.release();
        if (multicast != null && multicast.isHeld()) multicast.release();
    }

    @SuppressWarnings("deprecation")
    private void foreground(String text) {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Hosting a game",
                NotificationManager.IMPORTANCE_LOW));
            b = new Notification.Builder(this, CHANNEL);
        } else b = new Notification.Builder(this);
        int im = PendingIntent.FLAG_IMMUTABLE;
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), im);
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, HostService.class).setAction(STOP), im);
        Notification n = b.setSmallIcon(R.drawable.ic_stat_host)
            .setContentTitle("Hosting Shards of Ashen")
            .setContentText(text)
            .setContentIntent(open)
            .setOngoing(true)
            .addAction(new Notification.Action.Builder(null, "Stop hosting", stop).build())
            .build();
        if (Build.VERSION.SDK_INT >= 34) startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        else startForeground(1, n);
    }
}
