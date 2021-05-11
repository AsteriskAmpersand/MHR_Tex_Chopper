# -*- coding: utf-8 -*-
"""
Created on Thu Apr  8 22:07:22 2021

@author: AsteriskAmpersand
"""
import math
from itertools import zip_longest

DEBUG = True

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
    if mip == 0:
        return superBlockSize
    else:
        return _capSuperBlock(superBlockSize,mTexelSize,trueSize,mip)

def _capSuperBlock(superBlockSize,mTexelSize,trueSize,mip):
    x,y = trueSize
    sX,sY = superBlockSize
    #print(sX,sY) #shrink based on max dimension or min it's one or the other
    sx,sy = ulog2(sX),ulog2(sY)
    tx,ty = mTexelSize
    dx,dy = ulog2(ruD(x,tx)),ulog2(ruD(y,ty))    
    if DEBUG:
        print("TxM: (sBS,mTs,s,mip,dxdy) %s"%str((superBlockSize,mTexelSize,trueSize,mip,dx,dy)))
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
        print("TxM: "+ str("%d x %d | SuperBlockCoeff: %d x %d | Texel: %d x %d | SquareBlock %d x %d | SuperBlock %d x %d | HyperBlock (%d,%d) %d x %d"%
              (*trueSize,sX,sY,texelWidth,texelHeight,4*texelWidth,8*texelHeight,sX*4*texelWidth,sY*8*texelHeight,
               superblockPixelWidth,superblockPixelHeight,
               sX*4*texelWidth*superblockWCount,sY*8*texelHeight*superblockHCount)))
    return Texture.indexize()

packetSize = 16
def extendedZip(linearTexel,pattern):
    #return zip(linearTexel,pattern)
    if DEBUG:
        linearTexel = list(linearTexel)
        print("TxM: PreJoinBlock "+ str(len(b''.join(linearTexel))))
        print("TxM: PreJoinBlockTexels "+ str(len(linearTexel)))
        print("TxM: PreJoinPatternTexels "+ str(len(pattern)))
        superTexel = list(zip_longest(linearTexel,pattern,fillvalue = b'\x00'*packetSize))
        flatTexel = b''.join([lt for lt,p in superTexel])
        print("TxM: ExtensionTexels "+ str(len(superTexel)))
        print("TxM: FlatExtetnsionLength "+ str(len(flatTexel)))
        return superTexel
    return zip_longest(linearTexel,pattern,fillvalue = b'\x00'*packetSize)

linearize = lambda packetSize,data: (data[i*packetSize:(i+1)*packetSize] for i in range(len(data)//packetSize))
def deswizzle(data,superBlockSize,texelSize,mTexelSize,trueSize,mip=0):    
    linearTexel = linearize(packetSize,data)
    swizzlePattern = generateSwizzlingPatttern(superBlockSize,texelSize,mTexelSize,trueSize,mip)
    
    solvedData = sorted((tuple( ryindex + rxindex),texel) 
               for texel,(rxindex,ryindex) in extendedZip(linearTexel,swizzlePattern))
    if DEBUG:
        #print("TxM: "+ str("%d/%d"%(len(data),len(solvedData)*packetSize)))
        if len(data) != len(solvedData)*packetSize:
            print("TxM: "+ str())
            print("TxM: "+ str("[EXCEPTION SIZE ILLEGAL]"))
            print("TxM: "+ str())
    return b''.join((tex for ix,tex in solvedData))

def swizzle(data,superBlockSize,texelSize,mTexelSize,trueSize,mip=0):      
    if DEBUG: print("TxM >>: ==================================================")
    linearTexel = linearize(packetSize,data)
    swizzlePattern = generateSwizzlingPatttern(superBlockSize,texelSize,mTexelSize,trueSize,mip)
    #print(swizzlePattern)
    swizzledEnum = sorted([(ry+rx,ix) for ix,(rx,ry) in enumerate(swizzlePattern)])
    if DEBUG:
        linearTexel = list(linearTexel)
        sizzlePattern = list(swizzlePattern)
        llt = len(linearTexel)
        lsp = len(swizzlePattern)
        print("TxM >>: LinearTexel/SwizzleCount "+ str("%d/%d"%(llt,lsp)))
        if llt > lsp:
            pass
            #raise
    if DEBUG: print("TxM >>: ==================================================")
    return b''.join((tex for ix,tex in sorted(((ix,texel) for texel,(yx,ix) in extendedZip(linearTexel,swizzledEnum)))))