# -*- coding: utf-8 -*-
"""
Created on Mon May 10 17:12:51 2021

@author: Asterisk
"""

import math
from debugging import DEBUG
packetSize = 16


def bitCount(int32):
    return sum(((int32 >> i) & 1 for i in range(32)))

def ulog2(x):
    return math.ceil(math.log2(x))

ruD = lambda x,y: (x+y-1)//y

def dotDivide(vec1,vec2):
    return tuple([ruD(vl,vr) for vl,vr in zip(vec1,vec2)])

def getSwizzleSizes(size,packetTexelSize):
    w,h = size
    tw,th = packetTexelSize
    dx,dy = ulog2(ruD(w,tw)),ulog2(ruD(h,th))
    return max(0,min(4,dx-3)),max(0,min(4,dy-3))

linearize = lambda packetSize,data: (data[i*packetSize:(i+1)*packetSize] for i in range(len(data)//packetSize))

class CoordinateMapping():
    squareWidth = 2
    squareHeight = 2
    blockWidth = 2
    blockHeight = 4

    def __init__(self,size,packetTexelSize,swizzleSize):
        w,h = size
        tw,th = packetTexelSize
        self.wcount, self.hcount = (ruD(w,tw),ruD(h,th))
        self.finalw, self.finalh = size
        self.width, self.height = self.wcount*tw, self.hcount*th
        self.tw, self.th = packetTexelSize
        self.sw, self.sh = swizzleSize
        self._x,self._y = 0,0
        
        self.superblockWidth, self.superblockHeight = 2**self.sw, 2**self.sh
        
        self._CoSqWCum, self._CoSqHCum = self.squareWidth, self.squareHeight
        self._CoSqArea = self._CoSqWCum*self._CoSqHCum
        
        self._CoBWCum, self._CoBHCum = self._CoSqWCum*self.blockWidth, self._CoSqHCum*self.blockHeight
        self._CoBArea = self._CoBWCum*self._CoBHCum
        
        self._CoSuWCum, self._CoSuHCum = self._CoBWCum*self.superblockWidth, self._CoBHCum*self.superblockHeight
        self._CoSuArea = self._CoSuWCum*self._CoSuHCum
        
        self.hyperWCount, self.hyperHCount = ruD(self.wcount,self._CoSuWCum),ruD(self.hcount,self._CoSuHCum)
        self.hyperW, self.hyperH = self.hyperWCount*self._CoSuWCum,self.hyperHCount*self._CoSuHCum
        
        if DEBUG:
            print("TxM2: "+ str("%d x %d | SuperBlockCoeff: %d x %d | Texel: %d x %d | SquareBlock %d x %d | SuperBlock %d x %d | HyperBlock (%d,%d) %d x %d"%
                               (self.finalw,self.finalh,self.sw,self.sh,self.tw,self.th,
                               self.tw*self._CoBWCum,self.th*self._CoBHCum,
                               self.tw*self._CoSuWCum,self.th*self._CoSuHCum,
                               self._CoSuWCum*self.tw,self._CoSuHCum*self.th,
                               self.hyperW*self.tw,self.hyperH*self.th)))
        
    def mapToOffset(self,x,y,error = False):
        #superblocks stack on x, for the length of the image hyperdimensions
        #blocks stack on y, for the length of the superblock
        #squares stack on y, for the length of the block
        #texel stack on y, for the length of the square
        superblockX, superblockY = x // self._CoSuWCum, y  // self._CoSuHCum
        
        sbX, sbY = x % self._CoSuWCum, y  % self._CoSuHCum
        blockX, blockY = sbX // self._CoBWCum, sbY // self._CoBHCum
        
        bX, bY = sbX % self._CoBWCum, sbY % self._CoBHCum
        squareX, squareY = bX // self._CoSqWCum, bY // self._CoSqHCum
        
        lX,lY = bX % self._CoSqWCum, bY % self._CoSqHCum
        
        offset = superblockY*self._CoSuArea*self.hyperWCount + superblockX*self._CoSuArea +\
                blockX*self._CoBArea*self.superblockHeight + blockY*self._CoBArea +\
                squareX*self._CoSqArea*self.blockHeight +  squareY*self._CoSqArea +\
                lX*self.squareHeight + lY
        if error:
            print((lX,bX,sbX,superblockX),(lY,bY,sbY,superblockY))
        return offset
    
    def nextToOffset(self,deswizzle = True):
        if self._y >= self.hcount: return -1
        value = self.mapToOffset(self._x,self._y)
        if DEBUG:
            self._px = self._x
            self._py = self._y
        self._x, self._y = (self._x+1)%self.wcount, self._y + ((self._x+1)>=self.wcount)
        return value
    
    def swizzlingPatternGenerator(self):
        self._x,self._y = 0,0
        offset = self.nextToOffset()
        while(offset != -1):            
            yield offset
            offset = self.nextToOffset()
    
    def deswizzle(self,imageData):
        data = list(linearize(packetSize,imageData))
        generator = self.swizzlingPatternGenerator()
        if DEBUG: print([data[next(generator)] for g in range(1)])
        generator = self.swizzlingPatternGenerator()
        self.image = b''.join((data[offset] for offset in generator))
        if DEBUG: print("TxM2: Image Byte Len %X"%len(self.image))
        return self.image

    def swizzle(self,imageData):
        output = [b'\x00'*packetSize for _ in range(self.hyperW*self.hyperH)]
        if DEBUG:
            print("TxM2: Input Packet Count: %d Output Packet Count: %d Output Length: %d"%(len(imageData)/packetSize,len(output),len(output)*packetSize))
        data = linearize(packetSize,imageData)
        generator = self.swizzlingPatternGenerator()
        for datum,offset in zip(data,generator):
            try:
                output[offset] = datum
            except:
                if DEBUG:
                    print (self._px,self._py)
                    print(offset)
                    self.mapToOffset(self._px,self._py,error = True)
                raise
        self.image = b''.join(output)
        return self.image
                
    def dimensions(self):
        """returns Intended Dimensions, True Dimensions, Hyper Dimensions"""
        return (self.finalw,self.finalh), (self.width,self.height), (self.hyperW,self.hyperH)

def deswizzle(imageData,size,packetTexelSize,swizzleSize,mip):
    if mip:
        size = dotDivide(size,(2**mip,2**mip))
        sx,sy = getSwizzleSizes(size,packetTexelSize)
        swizzleSize = min(sx,swizzleSize[0]),min(sy,swizzleSize[1])
    cm = CoordinateMapping(size,packetTexelSize,swizzleSize)
    image = cm.deswizzle(imageData)
    intendedSize,trueSize,_ = cm.dimensions()
    #if DEBUG: return intendedSize,trueSize,imageData,packetTexelSize
    return intendedSize,trueSize,image,packetTexelSize
    
if __name__ in "__main__":
    x,y = 13,11 #In sq,bl,sb,hb coordinates (1,0,1,1) (1,1,1,0) 
    off = 3*2*2*16 + 4*8 + 7
    cm = CoordinateMapping((16,16),(1,1),(1,1))
    assert cm.mapToOffset(x, y) == off
        
    