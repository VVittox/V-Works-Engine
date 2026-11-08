




from __future__ import annotations
import math,sys,types
from PIL import Image,ImageDraw,ImageFont

class BoundSignal:
    def __init__(self):self.callbacks=[];self.calls=[]
    def connect(self,callback):self.callbacks.append(callback)
    def emit(self,*args):
        self.calls.append(args)
        for callback in tuple(self.callbacks):callback(*args)

class Signal:
    def __init__(self,*args):pass
    def __set_name__(self,owner,name):self.name='_signal_'+name
    def __get__(self,instance,owner):
        if instance is None:return self
        if self.name not in instance.__dict__:instance.__dict__[self.name]=BoundSignal()
        return instance.__dict__[self.name]

class QPointF:
    def __init__(self,x=0,y=0):self._x=float(x);self._y=float(y)
    def x(self):return self._x
    def y(self):return self._y

class QLineF:
    def __init__(self,a,b):self.a=a;self.b=b

class QRectF:
    def __init__(self,x,y,w,h):self.x=x;self.y=y;self.w=w;self.h=h
    def contains(self,p):return self.x<=p.x()<=self.x+self.w and self.y<=p.y()<=self.y+self.h

class QPolygonF(list):
    def containsPoint(self,point,*_):
        inside=False;j=len(self)-1;x,y=point.x(),point.y()
        for i,a in enumerate(self):
            b=self[j]
            if (a.y()>y)!=(b.y()>y) and x<(b.x()-a.x())*(y-a.y())/(b.y()-a.y())+a.x():inside=not inside
            j=i
        return inside

class QColor:
    def __init__(self,*args):self.rgba=tuple(args)+(255,)*(4-len(args))

class QPen:
    def __init__(self,color,width=1):self.color=color;self.width=width

class Qt:
    StrongFocus=1;MouseFocusReason=2;LeftButton=1;RightButton=2;MiddleButton=4
    ShiftModifier=1;ControlModifier=2;AlignCenter=4;OddEvenFill=0;NoBrush=0
    OpenHandCursor=3;ClosedHandCursor=4
    Key_W=87;Key_E=69;Key_R=82;Key_F=70;Key_P=80;Key_X=88;Key_Y=89;Key_Z=90;Key_L=76;Key_G=71
    Key_Escape=27;Key_Return=13

class QWidget:
    def __init__(self,parent=None):self._width=1280;self._height=720;self.updates=0;self.cursor=None
    def width(self):return self._width
    def height(self):return self._height
    def resize(self,w,h):self._width=w;self._height=h
    def rect(self):return QRectF(0,0,self.width(),self.height())
    def setMouseTracking(self,*_):pass
    def setFocusPolicy(self,*_):pass
    def setFocus(self,*_):pass
    def setMinimumSize(self,*_):pass
    def update(self):self.updates+=1
    def setCursor(self,cursor):self.cursor=cursor
    def unsetCursor(self):self.cursor=None
    def keyPressEvent(self,*_):pass
    def focusOutEvent(self,*_):pass

class Event:
    def __init__(self,x=0,y=0,button=Qt.LeftButton,modifiers=0,key=0,wheel=120):
        self.p=QPointF(x,y);self.b=button;self.m=modifiers;self.k=key;self.wheel=wheel
    def position(self):return self.p
    def button(self):return self.b
    def modifiers(self):return self.m
    def key(self):return self.k
    def angleDelta(self):return QPointF(0,self.wheel)
    def accept(self):pass

class QPainter:
    Antialiasing=1
    def __init__(self,widget):
        widget.image=Image.new('RGBA',(widget.width(),widget.height()),(0,0,0,255));self.widget=widget
        self.pen=QPen(QColor(255,255,255));self.brush=None
        try:self.font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
        except OSError:self.font=ImageFont.load_default()
    def setRenderHint(self,*_):pass
    def setPen(self,pen):self.pen=pen if isinstance(pen,QPen) else QPen(pen)
    def setBrush(self,brush):self.brush=brush if isinstance(brush,QColor) else None
    def _draw(self,fn):
        overlay=Image.new('RGBA',self.widget.image.size);fn(ImageDraw.Draw(overlay));self.widget.image=Image.alpha_composite(self.widget.image,overlay)
    def fillRect(self,rect,color):
        self._draw(lambda d:d.rectangle((rect.x,rect.y,rect.x+rect.w,rect.y+rect.h),fill=color.rgba))
    def drawLine(self,a,b):
        self._draw(lambda d:d.line((a.x(),a.y(),b.x(),b.y()),fill=self.pen.color.rgba,width=max(1,round(self.pen.width))))
    def drawLines(self,lines):
        self._draw(lambda d:[d.line((v.a.x(),v.a.y(),v.b.x(),v.b.y()),fill=self.pen.color.rgba,width=max(1,round(self.pen.width))) for v in lines])
    def drawRect(self,*args):
        rect=args[0] if len(args)==1 else QRectF(*args)
        self._draw(lambda d:d.rectangle((rect.x,rect.y,rect.x+rect.w,rect.y+rect.h),outline=self.pen.color.rgba,
                                       fill=self.brush.rgba if self.brush else None,width=max(1,round(self.pen.width))))
    def drawEllipse(self,p,rx,ry):
        self._draw(lambda d:d.ellipse((p.x()-rx,p.y()-ry,p.x()+rx,p.y()+ry),outline=self.pen.color.rgba,
                                     fill=self.brush.rgba if self.brush else None,width=max(1,round(self.pen.width))))
    def drawPolygon(self,points):
        self._draw(lambda d:d.polygon([(v.x(),v.y()) for v in points],outline=self.pen.color.rgba,fill=self.brush.rgba if self.brush else None,width=max(1,round(self.pen.width))))
    def drawText(self,*args):
        if isinstance(args[0],QRectF):
            r=args[0];x,y=r.x+r.w/2,r.y+r.h/2;text=args[-1];anchor='mm'
        elif isinstance(args[0],QPointF):x,y=args[0].x(),args[0].y()-12;text=args[1];anchor=None
        else:x,y=args[0],args[1]-12;text=args[2];anchor=None
        self._draw(lambda d:d.text((x,y),text,fill=self.pen.color.rgba,font=self.font,anchor=anchor))

def install():
    modules={name:types.ModuleType(name) for name in ('PySide6','PySide6.QtCore','PySide6.QtGui','PySide6.QtWidgets')}
    for name in ('QPointF','QLineF','QRectF','Qt','Signal'):setattr(modules['PySide6.QtCore'],name,globals()[name])
    for name in ('QColor','QPen','QPolygonF','QPainter'):setattr(modules['PySide6.QtGui'],name,globals()[name])
    for name in ('QKeyEvent','QMouseEvent','QWheelEvent'):setattr(modules['PySide6.QtGui'],name,Event)
    modules['PySide6.QtWidgets'].QWidget=QWidget
    sys.modules.update(modules)
