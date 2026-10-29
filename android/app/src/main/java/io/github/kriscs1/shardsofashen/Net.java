package io.github.kriscs1.shardsofashen;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** The phone on its networks: its own addresses (for others to join a game it hosts), and the games answering on
 *  them (server/lan.py: PROBE to UDP 8485, broadcast; each game answers with what it is). */
final class Net {
    static final int LAN_PORT = 8485;
    static final byte[] PROBE = "SHARDSOFASHEN?".getBytes(StandardCharsets.US_ASCII);

    private Net() { }

    /** The phone's IPv4 addresses on its local networks (Wi-Fi, its own hotspot). */
    static JSONArray addresses() {
        JSONArray out = new JSONArray();
        for (InterfaceAddress a : local()) out.put(a.getAddress().getHostAddress());
        return out;
    }

    private static List<InterfaceAddress> local() {
        List<InterfaceAddress> out = new ArrayList<>();
        try {
            for (NetworkInterface n : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!n.isUp() || n.isLoopback()) continue;
                for (InterfaceAddress a : n.getInterfaceAddresses()) {
                    InetAddress ip = a.getAddress();
                    if (ip instanceof Inet4Address && ip.isSiteLocalAddress()) out.add(a);
                }
            }
        } catch (Exception ignored) { }
        return out;
    }

    /** The games on the phone's networks: [{address, name, port, online, max, version, here}], each once. */
    static JSONArray find(int ms) {
        JSONArray found = new JSONArray();
        Set<String> seen = new HashSet<>(), mine = new HashSet<>();
        for (InterfaceAddress a : local()) mine.add(a.getAddress().getHostAddress());
        try (DatagramSocket sock = new DatagramSocket()) {
            sock.setBroadcast(true);
            List<InetAddress> to = new ArrayList<>();
            to.add(InetAddress.getByName("255.255.255.255"));
            to.add(InetAddress.getByName("127.0.0.1"));             // (a game this phone hosts)
            for (InterfaceAddress a : local()) if (a.getBroadcast() != null) to.add(a.getBroadcast());
            for (InetAddress t : to) {
                try { sock.send(new DatagramPacket(PROBE, PROBE.length, t, LAN_PORT)); } catch (Exception ignored) { }
            }
            long until = System.currentTimeMillis() + ms;
            byte[] buf = new byte[4096];
            while (System.currentTimeMillis() < until) {
                sock.setSoTimeout((int) Math.max(1, until - System.currentTimeMillis()));
                DatagramPacket p = new DatagramPacket(buf, buf.length);
                try { sock.receive(p); } catch (SocketTimeoutException e) { break; }
                try {
                    JSONObject a = new JSONObject(new String(p.getData(), 0, p.getLength(), StandardCharsets.UTF_8));
                    if (!"shardsofashen".equals(a.optString("game"))) continue;
                    String ip = p.getAddress().getHostAddress();
                    boolean here = ip.equals("127.0.0.1") || mine.contains(ip);
                    String key = (here ? "here" : ip) + ":" + a.optInt("port");
                    if (!seen.add(key)) continue;
                    a.put("address", here ? "127.0.0.1" : ip);
                    a.put("here", here);
                    found.put(a);
                } catch (Exception ignored) { }
            }
        } catch (Exception ignored) { }
        return found;
    }
}
