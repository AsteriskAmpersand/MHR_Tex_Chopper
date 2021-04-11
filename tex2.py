# -*- coding: utf-8 -*-
"""
Created on Sun Apr  4 19:24:12 2021

@author: AsteriskAmpersand
"""

import construct as C
from pathlib import Path
import sys
import io

from formatEnum import reverseFormatEnum,formatTexelParse,formatParse
from dds import ddsFromTexData,ddsMHRTypeEnum,getBCBPP
from astc import astcToPureRGBA
from dds import texHeaderFromDDSFile
from streaming import convertStreaming
from tex_math import (ruD,ulog2,bitCount,linearize,dotDivide,hypersize,deswizzle,
                    squareWidth,squareHeight,blockWidth,blockHeight,packetSize)

DEBUG = False
if __name__ in "__main__":
    DEBUG = False

mipData = C.Struct(
        "mipOffset" / C.Int64ul,
        "compressedSize" / C.Int32ul,
        "uncompressedSize" / C.Int32ul,
    )

_TEXHeader = C.Struct(
        "magic" / C.CString("utf-8"),
        "version" / C.Int32ul,
        "width" / C.Int16ul,
        "height" / C.Int16ul,
        "depth" / C.Int16ul,
        "counts" / C.Int16ul,
        #C.Probe(),
        "imageCount" / C.Computed(C.this.counts&0x3FF),#C.Int8ul,#12
        "mipCount" / C.Computed((C.this.counts>>12)),#C.Int8ul,#4
        "format" / C.Int32ul,
        "ONE_0" / C.Const(1,C.Int32ul),
        "cubemapMarker" / C.Int32ul,
        "unkn04" / C.Int8ul[2],
        "NULL0" /  C.Const(0,C.Int16ul),
        "swizzleHeightDepth" / C.Int8ul,
        "swizzleHeight" / C.Computed(C.this.swizzleHeightDepth&0xF),
        "swizzleDepth" / C.Computed(C.this.swizzleHeightDepth&0xF0>>4),
        "swizzleWidth" / C.Int8ul,
        "NULL1" / C.Int16ul,
        #[3],
        "SEVEN" / C.Const(7,C.Int16ul),
        "ONE_1" / C.Const(1,C.Int16ul),
        #C.Probe(),
        "textureHeaders" / mipData[C.this.mipCount][C.this.imageCount],
        "start" /C.Tell,
        "data" / C.GreedyBytes,
    )
TEXHeader = _TEXHeader#.compile()

def expandBlockData(texhead):
    texs = []
    for image in texhead.textureHeaders:
        mips = []
        for mipsTex in image:
            start = mipsTex.mipOffset-texhead.start
            end = start + mipsTex.compressedSize
            padding = mipsTex.uncompressedSize - mipsTex.compressedSize
            mips.append(texhead.data[start:end]+b"\x00"*padding)
        texs.append(mips)
    return texs
    
def trim(data,size,texelSize,superBlockSize):    
    w,h = size
    tw,th = hypersize(size,texelSize,superBlockSize)
    bw,bh = texelSize
    linearTexel = linearize(packetSize,data)
    result = b''.join(texel for ix,texel in (filter(lambda ixtexel: ((((ixtexel[0]))*bw) % tw < w) and ((((ixtexel[0]))*bw) // tw < h) ,enumerate(linearTexel))))
    #if DEBUG:
    #    print("%d/%d | %d x %d [%d x %d]"%(len(data),len(result),w,h,bw,bh))
    return result

def BCtoDDS(filename,texhead,texelSize,datablocks):
    width,height = texhead.width,texhead.height
    size = width,height
    p = lambda x: (x,x)
    superBlockSize = (2**texhead.swizzleWidth,2**texhead.swizzleHeight)
    trimmedBlocks = [trim(data,dotDivide(size,p(2**mip)),texelSize,superBlockSize) for texture in datablocks for mip,data in enumerate(texture)]
    targetFormat = ddsMHRTypeEnum[reverseFormatEnum[texhead.format].upper()]
    mipCount,imageCount = texhead.mipCount, texhead.imageCount
    #if DEBUG:mipCount,imageCount = 1,1
    cubemap = texhead.cubemapMarker!=0
    #cubemap = 0
    result = ddsFromTexData(height, width, mipCount, imageCount, targetFormat, cubemap, b''.join(trimmedBlocks))
    output = Path('.'.join(str(filename).split(".")[:2])).with_suffix(".dds")
    with open(output,"wb") as outf:
        outf.write(result)
    return output

def toR8G8B8_UNORM(pixelData):    
    return b''.join(map(lambda row: b''.join(map(bytes,row)),pixelData))

def ASTCtoDDS(filename,texhead,texelSize,data,f):
    bindata = b""
    #data = data[:1]
    for tex in data:
        for mip,image in enumerate(tex):
            size = texhead.width//2**(mip),texhead.height//2**(mip)
            superBlockSize = (2**max(texhead.swizzleWidth-mip,0),2**max(texhead.swizzleHeight-mip,0))
            tw,th = hypersize(size,texelSize,superBlockSize)
            rgba = astcToPureRGBA(image, tw, th, texelSize[0], texelSize[1], "Srgb" in f)
            bindata += toR8G8B8_UNORM([[column for column in row[:size[0]]] for row in rgba[:size[1]]])
    output = Path('.'.join(str(filename).split(".")[:2])).with_suffix(".dds")
    mipCount,imageCount = texhead.mipCount, texhead.imageCount
    #if DEBUG:mipCount,imageCount = 1,1
    cubemap = texhead.cubemapMarker!=0
    #cubemap = 0
    result = ddsFromTexData(texhead.height, texhead.width, mipCount, imageCount, "R8G8B8A8_UNORM", cubemap,bindata)
    with open(output,"wb") as outf:
        outf.write(result)

def exportBlocks(filename,texhead,t,f,texelSize,data):
    #for each image, expand data into a separate file
    #edit the texhead to be 1 image big
    #texhead.imageCount = 1
    #outname = None
    #for ix,texture in enumerate(data):
        #if ix!=0:
        #    rfilename = filename.replace(".tex","_%d.tex"%ix)
        #else: rfilename = filename
    rfilename = filename
    if "ASTC" in t:
        f = ASTCtoDDS(rfilename,texhead,texelSize,data,f)
    elif "BC" in t:
        f = BCtoDDS(rfilename,texhead,texelSize,data)         
    else:
        f = BCtoDDS(rfilename,texhead,texelSize,data)
        #if ix==0:
    outname = f
    return outname

def mergeStreaming(streamingFile):
    baseHeader = streamingFile.replace("\\streaming","").replace("/streaming","")
    if Path(baseHeader).exists():
        with open(baseHeader,"rb") as baseFile:
            with open(streamingFile,"rb") as streamFile:
                data = io.BytesIO(b"")
                convertStreaming(baseFile,streamFile,data)
                data.seek(0)
                data = data.read()
        #raise
        base = TEXHeader.parse(data)
        return base
    else:
        raise ValueError("Cannot decode Streaming texture without headers on chunk.")

def convertFromTex(filename):
    if "streaming" not in str(filename):        
        filename = Path(filename)
        if not filename.exists():
            filename = filename.with_suffix(".tex.28")
        header = TEXHeader.parse_file(filename)
    else:
        header = mergeStreaming(str(filename))
    return _convertFromTex(header,filename)

from tex_math import swizzle
def testDeswizzle(block,*args):
    return deswizzle(swizzle(deswizzle(block,*args),*args),*args)

def _convertFromTex(header,filename):
    if DEBUG:
        print("%d x %d x %d | %d/%d"%(header.width,header.height,header.depth,header.mipCount,header.imageCount))
    #header.mipCount = 1
    #header.imageCount = 1
    filename = str(filename).replace(".19","")
    formatString = reverseFormatEnum[header.format]
    #print(formatString)
    typing,bx,by,formatting = formatTexelParse(formatString)
    datablocks = expandBlockData(header)
    width,height = header.width, header.height
    size = width,height
    trueSize = size#ruD(width,bx),ruD(height,by)
    texelSize = (bx,by)
    _,mBx,mBy,_ = formatParse(formatString)
    mTexelSize = mBx, mBy
    superBlockSize = (2**header.swizzleWidth,2**header.swizzleHeight)
    plainBlocks = [[deswizzle(block,superBlockSize,texelSize,mTexelSize,trueSize,mip) for mip,block in enumerate(image)] for tix,image in enumerate(datablocks)]
    return exportBlocks(filename,header,typing,formatting,texelSize,plainBlocks)
        
convert = convertFromTex

def convertToTex(filename,outf = None):
    texHeader = texHeaderFromDDSFile(filename)
    if outf is None:
        outf = str(filename).replace(".dds",".tex")
    with open(outf,"wb") as tex:
        binaryFile = TEXHeader.build(texHeader)
        tex.write(binaryFile)
    return outf

if __name__ in "__main__":
    def analyzeMipSize():
        mipsw = {}
        testCases = Path(r"E:\MHR\GameFiles\RETool\re_chunk_000").rglob("*.tex")
        for p in testCases:
            header = TEXHeader.parse_file(p)
            sx=header.swizzleWidth
            sy=header.swizzleHeight
            #print(2**sx,2**sy)
            #continue
            _,tx,ty,_ = formatParse(reverseFormatEnum[header.format])
            x=ulog2(ruD(header.width,tx))
            y=ulog2(ruD(header.height,ty))
            if (x,y) not in mipsw:mipsw[(x,y)] = {}
            if (sx,sy) not in mipsw[(x,y)]: mipsw[(x,y)][(sx,sy)] = set()
            mipsw[(x,y)][(sx,sy)].add(reverseFormatEnum[header.format])
            if header.swizzleDepth != 0:
                print("%d x %d (x %d) -> %d x %d (x %d): %s"%
                      (x,y,header.depth,sx,sy,header.swizzleDepth,str(p)) )
        for x,y in sorted(mipsw):
            print("%d x %d:"%(x,y))
            for sx,sy in mipsw[(x,y)]:
                print("    %d x %d: %s"%(sx,sy,', '.join(mipsw[(x,y)][(sx,sy)])))
    
    def testTiming():
        import time
        sub = 0
        k = 0
        start_time = time.time()
        testCases = Path(r"E:\MHR\GameFiles\RETool\re_chunk_000").rglob("*.tex")
        for p in testCases:
            astc_time  = time.time()
            header = TEXHeader.parse_file(p)
            formatting = reverseFormatEnum[header.format]
            #convertFromTex(p)
            elapsed_astc = time.time()-astc_time
            if "ASTC" in formatting:
                sub+=elapsed_astc
                k+=1
        elapsed = time.time() - start_time
        print("%s seconds for %d textures at %s sec/tex" % (elapsed,len(testCases),elapsed/len(testCases)))
        print("%s seconds for %d non astc textures at %s sec/tex" % (elapsed-sub,len(testCases)-k,
                                                            (elapsed-sub)/(len(testCases)-k)))
        print("%s seconds for %d astc textures at %s sec/tex" % (sub,k,sub/k))
    
   
    def runTests():
        #testCases = [r"E:\MHR\MHR_Tex_Chopper\tests\BlueNoise16x16.tex"]
        for p in testCases:
            header = TEXHeader.parse_file(p)
            if header.imageCount == 1:
                formatting = reverseFormatEnum[header.format]
                print(formatting)
                print(p)
                w = convertFromTex(p)
                print("Converted From")
                w = convertToTex(w,str(Path(p.replace(".","_iter.")).with_suffix(".tex")))
                print(w)
                convertFromTex(w)
    
    from texTest import testCases
    from pathlib import Path
    import traceback
    #convert(r"E:\MHR\GameFiles\RETool\re_chunk_000\natives\NSW\enemy\em001\00\mod\em001_00_ALBD.tex.28")
    #analyzeMipSize()
    #testTiming()
    runTests()
    
        #try:
        #    convertFromTex(p)
        #except Exception as e:
        #    traceback.print_tb(e.__traceback__)
        #    pass
