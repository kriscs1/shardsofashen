"""Picture sizes without pygame: the PNG header's IHDR, a BMP's BITMAPINFOHEADER (an old Liberty BASIC BMP sprite is
twice as high as its picture: the top half is the mask)."""
import struct


def image_size(path):
    """(width, height) of the picture in path, or None if it can't be read."""
    try:
        with open(path, "rb") as f:
            head = f.read(32)
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        w, h = struct.unpack(">II", head[16:24])
        return int(w), int(h)
    if head[:2] == b"BM" and len(head) >= 26:
        w, h = struct.unpack("<ii", head[18:26])
        return abs(int(w)), abs(int(h))
    return None


def sprite_size(path):
    """The sprite's picture size: a PNG's whole size, a BMP's lower half (the picture under its mask)."""
    size = image_size(path)
    if size is None:
        return None
    w, h = size
    if path.lower().endswith(".bmp"):
        h //= 2
    return w, h
