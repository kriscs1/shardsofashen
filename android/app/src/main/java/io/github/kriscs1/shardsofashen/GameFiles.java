package io.github.kriscs1.shardsofashen;

import android.content.Context;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** The game's folder on the phone (its data, maps, pictures, the server and the web page): game.zip, packed into the
 *  app by the build, unpacked into the app's files the first time it hosts and again whenever the app is updated. The
 *  world itself (world.db) is beside it, and stays. */
final class GameFiles {
    private GameFiles() { }

    static File unpack(Context c) throws IOException {
        String stamp = read(c.getAssets().open("game.stamp"));
        File dir = new File(c.getFilesDir(), "game");
        File mark = new File(dir, ".stamp");
        if (mark.exists() && stamp.equals(read(new FileInputStream(mark)))) return dir;
        delete(dir);
        byte[] buf = new byte[65536];
        try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(c.getAssets().open("game.zip")))) {
            for (ZipEntry e; (e = zip.getNextEntry()) != null; ) {
                File f = new File(dir, e.getName());
                if (!f.getCanonicalPath().startsWith(dir.getCanonicalPath() + File.separator))
                    throw new IOException("Bad path in game.zip: " + e.getName());
                if (e.isDirectory()) { f.mkdirs(); continue; }
                f.getParentFile().mkdirs();
                try (OutputStream out = new FileOutputStream(f)) {
                    for (int n; (n = zip.read(buf)) > 0; ) out.write(buf, 0, n);
                }
            }
        }
        try (OutputStream out = new FileOutputStream(mark)) {
            out.write(stamp.getBytes(StandardCharsets.UTF_8));
        }
        return dir;
    }

    private static String read(InputStream in) throws IOException {
        try (InputStream i = in) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[256];
            for (int n; (n = i.read(buf)) > 0; ) out.write(buf, 0, n);
            return new String(out.toByteArray(), StandardCharsets.UTF_8).trim();
        }
    }

    private static void delete(File f) {
        File[] inside = f.listFiles();
        if (inside != null) for (File g : inside) delete(g);
        f.delete();
    }
}
