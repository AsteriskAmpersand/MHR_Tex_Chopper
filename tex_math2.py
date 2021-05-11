# -*- coding: utf-8 -*-
"""
Created on Mon May 10 17:12:51 2021

@author: Asterisk
"""

import math

packetSize = 16

def ulog2(x):
    return math.ceil(math.log2(x))

ruD = lambda x,y: (x+y-1)//y

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
        
        self.CoSqWCum, self.CoSqHCum = self.squareWidth, self.squareHeight
        self.CoSqArea = self.CoSqWCum*self.CoSqHCum
        
        self.CoBWCum, self.CoBHCum = self.CoSqWCum*self.blockWidth, self.CoSqHCum*self.blockHeight
        self.CoBArea = self.CoBWCum*self.CoBHCum
        
        self.CoSuWCum, self.CoSuHCum = self.CoBWCum*self.superblockWidth, self.CoBHCum*self.superblockHeight
        self.CoSuArea = self.CoSuWCum*self.CoSuHCum
        
        self.hyperWCount, self.hyperHCount = ruD(self.w,self.CoSuWCum),ruD(self.h,self.CoSuHCum)
        self.hyperW, self.hyperH = self.hyperWCount*self.CoSuWCum,self.hyperHCount*self.CoSuHCum
        
    def mapToOffset(self,x,y):
        #superblocks stack on x, for the length of the image hyperdimensions
        #blocks stack on y, for the length of the superblock
        #squares stack on y, for the length of the block
        #texel stack on y, for the length of the square
        superblockX, superblockY = x // self.CoSuWCum, y  // self.CoSuHCum
        
        sbX, sbY = x % self.CoSuWCum, y  % self.CoSuHCum
        blockX, blockY = sbX // self.CoBWCum, sbY // self.CoBHCum
        
        bX, bY = sbX % self.CoBWCum, sbY % self.CoBHCum
        squareX, squareY = bX // self.CoSqWCum, bY // self.CoSqHCum
        
        lX,lY = bX % self.CoSqWCum, bY % self.CoSqHCum
        
        offset = superblockY*self.CoSuArea*self.hyperWCount + superblockX*self.CoSuArea +\
                blockX*self.CoBArea*self.superblockHeight + blockY*self.CoBArea +\
                squareX*self.CoSqArea*self.blockHeight +  squareY*self.CoSqArea +\
                lX*self.squareHeight + lY
        return offset
    
    def nextToOffset(self,deswizzle = True):
        if deswizzle:
            if self._y >= self.hcount: return -1
        else:
            if self._y >= self.hyperH: return -1
        value = self.mapToOffset(self._x,self._y)
        if deswizzle:
            self.x, self.y = (self.x+1)%self.wcount, self.y + ((self.x+1)>=self.wcount)
        else:
            self.x, self.y = (self.x+1)%self.hyperW, self.y + ((self.x+1)>=self.hyperW)
        return value
    
    def swizzlingPatternGenerator(self):
        offset = 0
        while(offset != -1):
            offset = self.nextToOffset(deswizzle = True)
            yield offset
    
    def deswizzle(self,imageData):
        data = list(linearize(packetSize,imageData))
        generator = self.swizzlingPatternGenerator()
        self.image = b''.join((data[offset] for offset in generator))
        return self.image

    def swizzle(self,imageData):
        output = [b'/x00'*packetSize for _ in range(self.hyperW*self.hyperH)]
        data = list(linearize(packetSize,imageData))
        generator = self.swizzlingPatternGenerator()
        for datum,offset in zip(data,generator):
            output[offset] = datum
        self.image = b''.join(output)
        return self.image
                
    def dimensions(self):
        """returns Intended Dimensions, True Dimensions, Hyper Dimensions"""
        return (self.finalw,self.finalh), (self.width,self.height), (self.hyperW,self.hyperH)
    
if __name__ in "__main__":
    x,y = 13,11 #In sq,bl,sb,hb coordinates (1,0,1,1) (1,1,1,0) 
    off = 3*2*2*16 + 4*8 + 7
    cm = CoordinateMapping((16,16),(1,1),(1,1))
    assert cm.mapToOffset(x, y) == off
        
    