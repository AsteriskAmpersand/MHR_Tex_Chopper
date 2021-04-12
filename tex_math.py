# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 22:07:22 2021

@author: AsteriskAmpersand
"""
import math

DEBUG = False
if __name__ in "__main__":
    DEBUG = False

def bitCount(int32):
    return sum(((int32 >> i) & 1 for i in range(32)))

def ulog2(x):
    return math.ceil(math.log2(x))

ruD = lambda x,y: (x+y-1)//y

squareWidth = 2
squareHeight = 2
blockWidth = 2
blockHeight = 4

def hypersize(size,texelSize,superBlockSize):
    w,h = size
    sW,sH = superBlockSize
    texelWidth,texelHeight = texelSize
    trueWidth,trueHeight = size#trueSize 
    superblockWCount = ruD(trueWidth,sW*blockWidth*squareWidth*texelWidth)
    superblockHCount = ruD(trueHeight,sH*blockHeight*squareHeight*texelHeight)  
    tw,th = sW*4*texelWidth*superblockWCount,sH*8*texelHeight*superblockHCount
    return tw,th


def dotDivide(vec1,vec2):
    return tuple([ruD(vl,vr) for vl,vr in zip(vec1,vec2)])

X = 0
Y = 1

class Container():
    subclass = None
    width = None
    height = None
    def __init__(self,direction,width=None,height=None,subclass=None):
        self.direction = direction
        if width: self.width = width
        if height: self.height = height
        if subclass: self.subclass = subclass
        elif self.subclass: 
            self.subclass = self.subclass()
        
    def indexize(self):
        result = []
        if self.direction == X:
            for y in range(self.height):
                for x in range(self.width):
                    if self.subclass:
                        childrenBlock = self.subclass.indexize()
                        result += [([x]+xt, [y]+yt)  for xt,yt in childrenBlock]
                    else:
                        result.append(([x],[y]))
        elif self.direction == Y:            
            for x in range(self.width):
                for y in range(self.height):
                    if self.subclass:
                        childrenBlock = self.subclass.indexize()
                        result += [([x]+xt, [y]+yt)  for xt,yt in childrenBlock]
                    else:
                        result.append(([x],[y]))
        return result 

def capSuperBlock(superBlockSize,mTexelSize,trueSize,mip):
    x,y = trueSize
    sX,sY = superBlockSize
    #print(sX,sY) #shrink based on max dimension or min it's one or the other
    sx,sy = ulog2(sX),ulog2(sY)
    tx,ty = mTexelSize
    dx,dy = ulog2(ruD(x,tx)),ulog2(ruD(y,ty))    
    return 2**min(sx,max(dx-3,0)),2**min(sy,max(dy-3,0))

#In multi image contextt, the size of the first image buffer is used as minimum for the following ones data
def generateSwizzlingPatttern(superBlockSize,texelSize,mTexelSize,trueSize,mip=0):
    
    trueSize=dotDivide(trueSize,(2**mip,2**mip))
    trueWidth,trueHeight = trueSize    
    
    #mipF = lambda x: ruD(x,2**mip)
    Square = Container(direction=Y,width=squareWidth,height=squareHeight)
    Block = Container(direction=Y,width=blockWidth,height=blockHeight,
                      subclass=Square)
    
    sX,sY = superBlockSize#dotDivide(superBlockSize,(2**mip,2**mip))
    if mip > 0:
        sX,sY = capSuperBlock(superBlockSize,mTexelSize,trueSize,mip)
    superblockWidth = sX
    superblockHeight = sY
    Superblock = Container(direction=Y,width=superblockWidth,height=superblockHeight,
                      subclass=Block)
    
    texelWidth,texelHeight = texelSize
    superblockPixelWidth = superblockWidth*blockWidth*squareWidth*texelWidth
    superblockPixelHeight = superblockHeight*blockHeight*squareHeight*texelHeight
    superblockWCount = ruD(trueWidth,superblockPixelWidth)
    superblockHCount = ruD(trueHeight,superblockPixelHeight)    
    Texture = Container(direction=X,width = superblockWCount,height=superblockHCount,
                        subclass=Superblock)
    if DEBUG:
        print("%d x %d | Texel: %d x %d | SquareBlock %d x %d | SuperBlock %d x %d | HyperBlock (%d,%d) %d x %d"%
              (*trueSize,texelWidth,texelHeight,4*texelWidth,8*texelHeight,sX*4*texelWidth,sY*8*texelHeight,
               superblockPixelWidth,superblockPixelHeight,
               sX*4*texelWidth*superblockWCount,sY*8*texelHeight*superblockHCount))
    return Texture.indexize()

packetSize = 16
linearize = lambda packetSize,data: (data[i*packetSize:(i+1)*packetSize] for i in range(len(data)//packetSize))
def deswizzle(data,superBlockSize,texelSize,mTexelSize,trueSize,mip=0):    
    linearTexel = linearize(packetSize,data)
    swizzlePattern = generateSwizzlingPatttern(superBlockSize,texelSize,mTexelSize,trueSize,mip)
    
    solvedData = sorted((tuple( ryindex + rxindex),texel) 
               for texel,(rxindex,ryindex) in zip(linearTexel,swizzlePattern))
    if DEBUG:
        print("%d/%d"%(len(data),len(solvedData)*packetSize))
        if len(data) != len(solvedData)*packetSize:
            print()
            print("[EXCEPTION SIZE ILLEGAL]")
            print()
    return b''.join((tex for ix,tex in solvedData))

def swizzle(data,superBlockSize,texelSize,mTexelSize,trueSize,mip=0):      
    linearTexel = linearize(packetSize,data)
    swizzlePattern = generateSwizzlingPatttern(superBlockSize,texelSize,mTexelSize,trueSize,mip)
    swizzledEnum = sorted([(ry+rx,ix) for ix,(rx,ry) in enumerate(swizzlePattern)])
    return b''.join((tex for ix,tex in sorted(((ix,texel) for texel,(yx,ix) in zip(linearTexel,swizzledEnum)))))