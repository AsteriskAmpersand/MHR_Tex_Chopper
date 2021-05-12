# -*- coding: utf-8 -*-
"""
Created on Sun Apr  4 19:24:12 2021

@author: AsteriskAmpersand
"""

import construct as C
from pathlib import Path
import sys
import io

from formatEnum import reverseFormatEnum,formatTexelParse,formatParse, swizzableFormats,swizzledFormats
from dds import ddsFromTexData,ddsMHRTypeEnum,getBCBPP
from astc import astcToPureRGBA
from dds import texHeaderFromDDSFile
from streaming import convertStreaming
from tex_math import (ruD,ulog2,bitCount,linearize,dotDivide,hypersize,deswizzle,
                    squareWidth,squareHeight,blockWidth,blockHeight,packetSize,
                    capSuperBlock)
from debugging import DEBUG

mipData = C.Struct(
        "mipOffset" / C.Int64ul,
        "compressedSize" / C.Int32ul,
        "uncompressedSize" / C.Int32ul,
    )

swizzleData = C.Struct(
        "swizzleHeightDepth" / C.Int8ul,
        "swizzleHeight" / C.Computed(C.this.swizzleHeightDepth&0xF),
        "swizzleDepth" / C.Computed(C.this.swizzleHeightDepth&0xF0>>4),
        "swizzleWidth" / C.Int8ul,
        "NULL1" / C.Int16ul,
        "SEVEN" / C.Const(7,C.Int16ul),
        "ONE_1" / C.Const(1,C.Int16ul),
    )

swizzleNull = C.Struct(
        "swizzleHeightDepth" / C.Int8ul,
        "swizzleHeight" / C.Computed(C.this.swizzleHeightDepth&0xF),
        "swizzleDepth" / C.Computed(C.this.swizzleHeightDepth&0xF0>>4),
        "swizzleWidth" / C.Int8ul,
        "NULL1" / C.Int16ul,
        "SEVEN" / C.Const(0,C.Int16ul),
        "ONE_1" / C.Const(0,C.Int16ul),
    )

_TEXHeader = C.Struct(
        "magic" / C.CString("utf-8"),
        "version" / C.Int32ul,
        "width" / C.Int16ul,
        "height" / C.Int16ul,
        "depth" / C.Int16ul,
        "counts" / C.Int16ul,        
        "imageCount" / C.Computed(lambda this: this.counts&0x3FF if this.version in swizzableFormats else this.counts>>8),#C.Int8ul,#12
        "mipCount" / C.Computed(lambda this: (this.counts>>12 if this.version in swizzableFormats else this.counts&0xFF)),#C.Int8ul,#4
        "format" / C.Int32ul,
        "swizzleControl" / C.Int32sl,#C.Const(1,C.Int32ul),
        "cubemapMarker" / C.Int32ul,
        "unkn04" / C.Int8ul[2],
        "NULL0" /  C.Const(0,C.Int16ul),
        "swizzleData" / C.If(lambda ctx: ctx.version in swizzableFormats,C.IfThenElse(lambda ctx: ctx.version in swizzledFormats,swizzleData,swizzleNull)),
        "textureHeaders" / mipData[C.this.mipCount][C.this.imageCount],
        "start" /C.Tell,
        "data" / C.GreedyBytes,
    )
TEXHeader = _TEXHeader#.compile()

def expandBlockData(texhead,swizzle):
    texs = []
    for image in texhead.textureHeaders:
        mips = []
        for mipsTex in image:
            start = mipsTex.mipOffset-texhead.start
            end = start + (mipsTex.compressedSize if swizzle else mipsTex.uncompressedSize)
            padding = (mipsTex.uncompressedSize - mipsTex.compressedSize) if swizzle else 0
            print("Tx2: Input Packet Count: %d | Input Length: %d"%(mipsTex.uncompressedSize/packetSize,mipsTex.uncompressedSize))
            #assert len(data) == end-start
            mips.append(texhead.data[start:end]+b"\x00"*padding)
        texs.append(mips)
    return texs
    
def trim(data,size,texelSize,mTexelSize,superBlockSize):  
    w,h = size
    tw,th = hypersize(size,texelSize,superBlockSize)
    #mbw,mbh = mTexelSize
    bw,bh = texelSize
    linearTexel = linearize(packetSize,data)
    if DEBUG:
        print("Tx2")
        print("Tx2 Image XY : "+ str((w,h)))
        print("Tx2 Hyper XY : "+ str((tw,th)))
        print("Tx2 DataInLen : "+ str(len(data)))
        result = b''
        for ix,texel in enumerate(linearTexel):
            xix = (ix*bw)% tw
            yix = (ix*bw)//tw*bh
            #print(xix,yix,texel)
            if xix < w and yix < h:
                result += texel
    else:
        result = b''.join(texel for ix,texel in (filter(lambda ixtexel: ((((ixtexel[0]))*bw) % tw < w) and ((((ixtexel[0]))*bw) // tw * bh < h) ,enumerate(linearTexel))))
    if DEBUG:
        sX,sY = superBlockSize
        #print(sX,sY)
        
        superblockPixelWidth = sX*2*2*bw
        superblockPixelHeight = sY*4*2*bh
        superblockWCount = ruD(tw,superblockPixelWidth)
        superblockHCount = ruD(th,superblockPixelHeight)    
        
        print("Tx2: "+ str("%d x %d | SuperBlockCoeff: %d x %d | Texel: %d x %d | SquareBlock %d x %d | SuperBlock %d x %d | HyperBlock (%d,%d) %d x %d"%
          (*size,ulog2(sX),ulog2(sY),bw,bh,4*bw,8*bh,sX*4*bw,sY*8*bh,
           sX*4*bw,sY*8*bh,
           sX*4*bw*superblockWCount,sY*8*bh*superblockHCount)))
        print("Tx2 In/Out : %d/%d | %d x %d [%d x %d]"%(len(data),len(result),w,h,bw,bh))
        print("Tx2 Out/Expected: %d/%d"%(len(result), ruD(w,bw) * ruD(h,bh) * packetSize))
    assert len(result) == ruD(w,bw) * ruD(h,bh) * packetSize
        
    #print("_____")  
    return result

def BCtoDDS(filename,texhead,texelSize,mTexelSize,datablocks):
    width,height = texhead.width,texhead.height
    size = width,height
    p = lambda x: (x,x)
    if texhead.swizzleControl == 1:
        superBlockSize = (2**texhead.swizzleData.swizzleWidth,2**texhead.swizzleData.swizzleHeight)
        #if texelSize == (8,4): superBlockSize = dotDivide(superBlockSize,(2,1))
        trimmedBlocks = [trim(data,dotDivide(size,p(2**mip)),
                              texelSize,
                              mTexelSize,
                              capSuperBlock(superBlockSize,mTexelSize,dotDivide(size,p(2**mip)),mip)) 
                         for texture in datablocks for mip,data in enumerate(texture)]
    else:
        trimmedBlocks = [mip for texture in datablocks for mip in texture]
    targetFormat = ddsMHRTypeEnum[reverseFormatEnum[texhead.format].upper()]
    mipCount,imageCount = texhead.mipCount, texhead.imageCount
    cubemap = texhead.cubemapMarker!=0
    #cubemap = 0
    if DEBUG: print("Tx2: "+ str(list(map(len,trimmedBlocks))))
    result = ddsFromTexData(height, width, mipCount, imageCount, targetFormat, cubemap, b''.join(trimmedBlocks))
    output = Path('.'.join(str(filename).split(".")[:2])).with_suffix(".dds")
    with open(output,"wb") as outf:
        outf.write(result)
    return output

def toR8G8B8_UNORM(pixelData):    
    return b''.join(map(lambda row: b''.join(map(bytes,row)),pixelData))

def ASTCtoDDS(filename,texhead,texelSize,mTexelSize,data,f):
    bindata = b""
    for tex in data:
        for mip,image in enumerate(tex):
            size = ruD(texhead.width,2**(mip)),ruD(texhead.height,2**(mip))
            if texhead.swizzleData:
                superBlockSize = (2**max(texhead.swizzleData.swizzleWidth-mip,0),2**max(texhead.swizzleData.swizzleHeight-mip,0))
                tw,th = hypersize(size,texelSize,superBlockSize)
            else:
                superBlockSize = (1,1)
                tw,th = size
            rgba = astcToPureRGBA(image, tw, th, texelSize[0], texelSize[1], "Srgb" in f)
            binImg = toR8G8B8_UNORM([[column for column in row[:size[0]]] for row in rgba[:size[1]]])
            bindata += binImg
    output = Path('.'.join(str(filename).split(".")[:2])).with_suffix(".dds")
    mipCount,imageCount = texhead.mipCount, texhead.imageCount
    cubemap = texhead.cubemapMarker!=0
    result = ddsFromTexData(texhead.height, texhead.width, mipCount, imageCount, "R8G8B8A8UNORM", cubemap,bindata)
    with open(output,"wb") as outf:
        outf.write(result)
    return output

def exportBlocks(filename,texhead,t,f,texelSize,mTexelSize,data):
    rfilename = filename
    if "ASTC" in t:
        f = ASTCtoDDS(rfilename,texhead,texelSize,mTexelSize,data,f)
    elif "BC" in t:
        f = BCtoDDS(rfilename,texhead,texelSize,mTexelSize,data)         
    else:
        f = BCtoDDS(rfilename,texhead,texelSize,mTexelSize,data)
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
        print("Tx2: "+ str("%d x %d x %d | %d/%d"%(header.width,header.height,header.depth,header.mipCount,header.imageCount)))
    filename = str(filename).replace(".19","").replace(".28","")
    formatString = reverseFormatEnum[header.format]
    typing,bx,by,formatting = formatTexelParse(formatString)
    datablocks = expandBlockData(header,header.swizzleControl == 1)
    width,height = header.width, header.height
    size = width,height
    trueSize = size
    texelSize = (bx,by)
    _,mBx,mBy,_ = formatParse(formatString)
    mTexelSize = mBx, mBy
    if header.swizzleControl == 1:
        superBlockSize = (2**header.swizzleData.swizzleWidth,2**header.swizzleData.swizzleHeight)
        plainBlocks = [[deswizzle(block,superBlockSize,texelSize,mTexelSize,trueSize,mip) for mip,block in enumerate(image)] for tix,image in enumerate(datablocks)]
    else:
        plainBlocks = datablocks
    return exportBlocks(filename,header,typing,formatting,texelSize,mTexelSize,plainBlocks)
        
convert = convertFromTex

def convertToTex(filename,outf = None,salt = 0x1c):
    texHeader = texHeaderFromDDSFile(filename,salt)
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
            sx=header.swizzleData.swizzleWidth
            sy=header.swizzleData.swizzleHeight
            #print(2**sx,2**sy)
            #continue
            _,tx,ty,_ = formatParse(reverseFormatEnum[header.format])
            x=ulog2(ruD(header.width,tx))
            y=ulog2(ruD(header.height,ty))
            if (x,y) not in mipsw:mipsw[(x,y)] = {}
            if (sx,sy) not in mipsw[(x,y)]: mipsw[(x,y)][(sx,sy)] = set()
            mipsw[(x,y)][(sx,sy)].add(reverseFormatEnum[header.format])
            if header.swizzleDepth != 0:
                print("RT: "+str("%d x %d (x %d) -> %d x %d (x %d): %s"%
                      (x,y,header.depth,sx,sy,header.swizzleDepth,str(p)) ))
        for x,y in sorted(mipsw):
            print("RT: "+str("%d x %d:"%(x,y)))
            for sx,sy in mipsw[(x,y)]:
                print("RT: "+str("    %d x %d: %s"%(sx,sy,', '.join(mipsw[(x,y)][(sx,sy)]))))
    
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
        print("RT: "+str("%s seconds for %d textures at %s sec/tex" % (elapsed,len(testCases),elapsed/len(testCases))))
        print("RT: "+str("%s seconds for %d non astc textures at %s sec/tex" % (elapsed-sub,len(testCases)-k,
                                                            (elapsed-sub)/(len(testCases)-k))))
        print("RT: "+str("%s seconds for %d astc textures at %s sec/tex" % (sub,k,sub/k)))
    
   
    def runTests():
        testCases = [r"C:\Users\Asterisk\Documents\GitHub\MHR_Tex_Chopper\test\NullMSK1.tex",
                     r"C:\Users\Asterisk\Documents\GitHub\MHR_Tex_Chopper\test\eyelash_ALP.tex"
                     ]
        for p in testCases:
            header = TEXHeader.parse_file(p)
            if header.imageCount == 1 and header.depth == 1:
                formatting = reverseFormatEnum[header.format]
                if "NULL" not in formatting:
                    print("RT: "+str(formatting))
                    print("RT: "+str(p))
                    print()
                    w = convertFromTex(p)
                    print("RT: "+str("Converted From"))
                    print()
                    w = convertToTex(w,str(Path(p.replace(".","_iter.")).with_suffix(".tex")))
                    print("RT: "+str(w))
                    print()
                    convertFromTex(w)
                    print()
                    print("==================================")
    
    def irregularTests():
        REVerse = ['E:/MHR/MHR_Tex_Chopper/tests/T_Pl_Leon_00_Items_ALBM.tex.30']
        DMC5 = ['E:/MHR/MHR_Tex_Chopper/tests/wp00_000_albm.tex.11']
        for file in DMC5:
            print("Forwards")
            w = convertFromTex(file)
            print("Backwards")
            w = convertToTex(w,str(Path(file.replace(".","_iter.")).with_suffix(".tex")),salt = 11)
            print("Forward Again")
            convertFromTex(w)
        for file in REVerse:
            w = convertFromTex(file)
            w = convertToTex(w,str(Path(file.replace(".","_iter.")).with_suffix(".tex")),salt = 30)
            convertFromTex(w)
    from texTest import testCases
    from pathlib import Path
    import traceback
    #convert(r"E:\MHR\GameFiles\RETool\re_chunk_000\natives\NSW\enemy\em001\00\mod\em001_00_ALBD.tex.28")
    #analyzeMipSize()
    #testTiming()
    #irregularTests()
    runTests()
        #try:
        #    convertFromTex(p)
        #except Exception as e:
        #    traceback.print_tb(e.__traceback__)
        #    pass
