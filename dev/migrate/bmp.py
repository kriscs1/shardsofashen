import struct, zlib
def read_bmp(p):
    b=open(p,'rb').read()
    off=struct.unpack('<I',b[10:14])[0]; w,h=struct.unpack('<ii',b[18:26]); bpp=struct.unpack('<H',b[28:30])[0]
    pal=None
    if bpp==8:
        n=struct.unpack('<I',b[46:50])[0] or 256
        hs=struct.unpack('<I',b[14:18])[0]
        pal=[tuple(b[14+hs+i*4:14+hs+i*4+3][::-1]) for i in range(n)]
    rowsz=((w*bpp//8)+3)//4*4
    px=[]
    for y in range(abs(h)):
        ry = (abs(h)-1-y) if h>0 else y
        r=b[off+ry*rowsz:off+ry*rowsz+rowsz]
        row=[]
        for x in range(w):
            if bpp==24: row.append((r[x*3+2],r[x*3+1],r[x*3]))
            elif bpp==32: row.append((r[x*4+2],r[x*4+1],r[x*4]))
            elif bpp==8: row.append(pal[r[x]])
        px.append(row)
    return w,abs(h),px
def write_bmp(p,w,h,px):
    rowsz=(w*3+3)//4*4; data=b''
    for y in range(h-1,-1,-1):
        r=b''.join(bytes((c[2],c[1],c[0])) for c in px[y]); data+=r+b'\0'*(rowsz-len(r))
    hdr=b'BM'+struct.pack('<IHHI',54+len(data),0,0,54)+struct.pack('<IiiHHIIiiII',40,w,h,1,24,0,len(data),2835,2835,0,0)
    open(p,'wb').write(hdr+data)
def write_png(p,w,h,px,scale=1):
    raw=b''
    for y in range(h*scale):
        raw+=b'\0'+b''.join(bytes(px[y//scale][x//scale]) for x in range(w*scale))
    def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(p,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w*scale,h*scale,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
