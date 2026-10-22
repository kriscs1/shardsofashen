import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bmp import *
from common import write_sprite
# Draws the player's walking frames: Player<Dir><Frame>.png, Dir 1=N 2=E 4=S 8=W, Frame a=stand b/c=steps.
# Usage: python -I build_player.py "<Sprites\Entities folder>"
C = {
 'H':(102,55,10), 'h':(72,38,6), 'S':(244,184,221), 's':(214,150,190), 'E':(40,20,30), 'M':(190,90,120),
 'T':(0,0,128), 't':(20,30,175), 'k':(0,0,90), 'P':(64,0,255), 'p':(44,0,185), 'B':(128,128,128), 'b':(88,88,88),
}
W=H=32; CX=16
def blank(): return [[None]*W for _ in range(H)]
def put(g,x,y,c):
    if 0<=x<W and 0<=y<H: g[y][x]=c
def rect(g,x0,y0,x1,y1,c):
    for y in range(y0,y1+1):
        for x in range(x0,x1+1): put(g,x,y,c)

def legs_front(g, frame):
    # left leg x CX-4..CX-2, right leg CX+1..CX+3 ; frame b lifts left, c lifts right
    for side,(x0,x1) in enumerate([(CX-4,CX-2),(CX+1,CX+3)]):
        lift = 2 if (frame=='b' and side==0) or (frame=='c' and side==1) else 0
        rect(g,x0,21,x1,27-lift,'P'); rect(g,x0,21,x0,27-lift,'p')
        rect(g,x0-(1 if side==0 else 0),28-lift,x1+(1 if side==1 else 0),29-lift,'B')
        rect(g,x0-(1 if side==0 else 0),29-lift,x1+(1 if side==1 else 0),29-lift,'b')

def legs_side(g, frame, face):  # face = +1 east
    if frame=='a':
        rect(g,CX-2,21,CX+1,27,'P'); rect(g,CX-2,21,CX-2,27,'p')
        rect(g,CX-2,28,CX+2,29,'B'); rect(g,CX-2,29,CX+2,29,'b')
        return
    # stride: back leg and front leg
    for leg,off in (('back',-1),('front',1)):
        d = off if frame=='b' else -off
        col = 'p' if leg=='back' else 'P'
        for y in range(21,28):
            t=(y-21)/6
            x = CX-1 + int(round(d*face*3*t))
            rect(g,x-1,y,x+1,y,col)
        fx = CX-1 + d*face*3
        rect(g,fx-1,28,fx+1,29,'B'); put(g,fx+2*face,29,'B'); rect(g,fx-1,29,fx+1,29,'b')

def torso_front(g, back=False):
    rect(g,CX-5,12,CX+4,21,'T'); rect(g,CX-5,12,CX-5,21,'k'); rect(g,CX+4,12,CX+4,21,'k')
    if not back: rect(g,CX-1,12,CX,13,'S')            # neck/collar
    rect(g,CX-4,20,CX+3,21,'k')          # belt shadow

def arms_front(g, frame, back=False):
    for side,(x0,x1) in enumerate([(CX-7,CX-6),(CX+5,CX+6)]):
        swing = 0
        if frame=='b': swing = 1 if side==1 else -1
        if frame=='c': swing = 1 if side==0 else -1
        rect(g,x0,13+max(0,swing),x1,18+swing,'t')
        rect(g,x0,19+swing,x1,20+swing,'S')

def torso_side(g, face):
    rect(g,CX-4,12,CX+3,21,'T'); rect(g,CX-4,20,CX+3,21,'k')
    if face>0: rect(g,CX-4,12,CX-4,21,'k')
    else: rect(g,CX+3,12,CX+3,21,'k')
    rect(g,CX-1,12,CX,12,'S')

def arm_side(g, frame, face):
    # visible arm hangs from shoulder at CX-1..CX ; swings forward/back
    sw = {'a':0,'b':1,'c':-1}[frame]
    for y in range(13,20):
        t=(y-13)/6
        x = CX-1 + int(round(sw*face*3*t))
        rect(g,x,y,x+1,y,'t')
    hx = CX-1 + sw*face*3
    rect(g,hx,20,hx+1,21,'S')

def head_front(g):
    rect(g,CX-4,3,CX+3,11,'S'); rect(g,CX-5,4,CX+4,9,'S')
    rect(g,CX-4,2,CX+3,4,'H'); rect(g,CX-5,3,CX+4,5,'H'); put(g,CX-5,6,'H'); put(g,CX+4,6,'H')
    rect(g,CX-3,2,CX+2,2,'h')
    put(g,CX-3,7,'E'); put(g,CX+2,7,'E')
    rect(g,CX-1,9,CX,9,'M')
    rect(g,CX-4,11,CX+3,11,'s')

def head_back(g):
    rect(g,CX-4,3,CX+3,11,'H'); rect(g,CX-5,4,CX+4,9,'H')
    rect(g,CX-4,2,CX+3,2,'h'); rect(g,CX-5,9,CX+4,9,'h')
    rect(g,CX-3,10,CX+2,11,'S'); rect(g,CX-3,11,CX+2,11,'s')
    put(g,CX-5,7,'S'); put(g,CX+4,7,'S')   # ears

def head_side(g, face):
    # east-facing then mirrored by caller for west
    rect(g,CX-4,3,CX+3,11,'S'); rect(g,CX-5,4,CX+4,9,'S'); put(g,CX+5,8,'S')   # nose
    rect(g,CX-4,2,CX+3,4,'H'); rect(g,CX-5,3,CX+2,5,'H'); rect(g,CX-5,5,CX-2,9,'H')
    rect(g,CX-4,2,CX+2,2,'h'); rect(g,CX-5,8,CX-3,9,'h')
    put(g,CX-1,7,'s')                      # ear
    put(g,CX+2,7,'E')
    put(g,CX+3,10,'M')
    rect(g,CX-3,11,CX+2,11,'s')

def mirror(g): return [row[::-1] for row in g]

def draw(direction, frame):
    g=blank()
    if direction in ('1','4'):
        legs_front(g,frame); torso_front(g, direction=='1'); arms_front(g,frame)
        if direction=='4': head_front(g)
        else: head_back(g)
    else:
        legs_side(g,frame,1); torso_side(g,1); head_side(g,1); arm_side(g,frame,1)
        if direction=='8': g=mirror(g)
    return g

def to_sprite(g):
    px=[[(255,255,255)]*W for _ in range(H)]+[[(0,0,0)]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if g[y][x]:
                px[y][x]=(0,0,0); px[H+y][x]=C[g[y][x]]
    return px

if __name__=='__main__':
    out = sys.argv[1] if len(sys.argv)>1 else None
    sheet=[]; frames=[]
    for d in '1248':
        for f in 'abc':
            px=to_sprite(draw(d,f)); frames.append((d+f,px))
            if out: write_sprite(out+'/Player%s%s.png'%(d,f),px)
    if out: write_sprite(out+'/Player.png',to_sprite(draw('4','a')))
    # preview: image halves on a grey background
    SW=len(frames)*(W+4)
    canvas=[[(60,60,60)]*SW for _ in range(H)]
    for i,(n,px) in enumerate(frames):
        for y in range(H):
            for x in range(W):
                if px[y][x]==(0,0,0): canvas[y][i*(W+4)+x]=px[H+y][x]
    write_png(os.path.join(os.path.dirname(os.path.abspath(__file__)),'player_preview.png'),SW,H,canvas,5)
