"""Northport is shut till its Parliament has spoken: the two roads out (the river bridge east of the city, 8,6,0, and the
forest road south of it, 2,10,0) each have oak gates across them and a gate guard who says why. The gates open (a Lock on
each gate tile, drawn open by Tiles.ini Unlocked.Tile) once The Temporary Capital is done (ParliamentQuest>=2: the Speaker
has given her letter). Only the way out is shut: nothing inside the city changes. Run it again: it writes the same again.

  python -I "dev\migrate\build_northport_blockade.py"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world_edit as W  # noqa: E402
import story_kit as K  # noqa: E402

MAKER = "build_northport_blockade.py"
XT, YT, TW = W.XT, W.YT, W.TW
OPEN = "$Attr.ParliamentQuest>=2"
SHUT_MSG = "The gates are shut."

# way: (map x, y), the gate's tiles (1-based, on that map), the guard's tile and way he faces
WAYS = {
    "Bridge": ((8, 6), [(18, 2), (18, 3)], (17, 3), "E", "Sergeant_Wick"),
    "Forest": ((2, 10), [(19, 15), (20, 15), (21, 15)], (20, 14), "S", "Sergeant_Hale"),
}


def main():
    w = W.World(0)
    for way, ((mx, my), gate, guard, face, name) in WAYS.items():
        gid = "Northport_%s_Gate_Guard" % way
        m = w.maps[(mx, my)]
        for (x, y) in gate:
            w.put(mx * XT + x - 1, my * YT + y - 1, "City_Gate001")
            ln = "Lock\t%d\t%d\t%s\t%s" % (x, y, OPEN, SHUT_MSG)
            m.ents = [e for e in m.ents if e.split("\t")[:3] != ln.split("\t")[:3]]
            m.ents.append(ln)
        m.ents = [e for e in m.ents if "Id=" + gid not in e]
        gx, gy = guard
        m.ents.append("NPC\tPort_Guard\t%d\t%d\tAttitude=Good Stand=1 Face=%s Id=%s Name=%s"
                      % ((gx - 1) * TW, (gy - 1) * TW, face, gid, name))
        w.changed.add(m.name)
        K.write_script("Talk to " + gid, [
            ("Get.Value", "ATTRIBUTE", "ParliamentQuest", "Variable.1$"),
            (">Conditional", "$Variable.1<2", "@open"),
            ("Display.Conversation", "Port_Guard",
             "Halt. The gates are shut by order of the Parliament: raiders have been seen on the roads, and nobody leaves "
             "Northport till it says so.\Go and see the Speaker in the City Hall; the Parliament's word is the only thing "
             "that opens these gates.", "Understood.", "@end"),
            ("End",),
            ("@open",),
            ("Display.Conversation", "Port_Guard",
             "The Parliament's word came down: the gates are open to you. Keep your sword close out there.",
             "Thank you.", "@end"),
            ("@end",),
            ("End",),
        ], MAKER)
    print("changed", w.save(), "maps")


if __name__ == "__main__":
    main()
