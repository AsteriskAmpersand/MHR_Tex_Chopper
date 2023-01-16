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
#from astc import astcToPureRGBA
from dds import texHeaderFromDDSFile
from streaming import convertStreaming
#from tex_math import (ruD,ulog2,bitCount,linearize,dotDivide,hypersize,#deswizzle,
#                    squareWidth,squareHeight,blockWidth,blockHeight,packetSize,
#                    capSuperBlock)
from tex_math import deswizzle,ruD,packetSize,ulog2
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
            if DEBUG:
                pass
                #print("Tx2: Input Packet Count: %d | Input Length: %d"%(mipsTex.uncompressedSize/packetSize,mipsTex.uncompressedSize))
            #assert len(data) == end-start
            mips.append(texhead.data[start:end]+b"\x00"*padding)
            if DEBUG: print("Tx2: %X %X"%(start,end))
        texs.append(mips)
    return texs

def trim(data,blockSize):
    bx,by = blockSize
    targetSize,currentSize,texture,packetTexelSize = data
    tx,ty = packetTexelSize

    finalx,finaly = targetSize
    currentx,currenty = currentSize
    if currentx == finalx and currenty == finaly:
        if DEBUG: print("Tx2: %X"%len(texture))
        return texture
    currentBlocksX,currentBlocksY = ruD(currentx,bx),ruD(currenty,by)
    targetBlocksX,targetBlocksY = ruD(finalx,bx),ruD(finaly,by)
    bppX = (bx * packetSize)//tx
    offset = lambda x,y: y * currentBlocksX * bppX + x * bppX
    result = b''.join((texture[offset(0,y):offset(targetBlocksX,y)] for y in range(targetBlocksY)))
    #print("_____")
    return result

def BCtoDDS(filename,texhead,blockSize,datablocks):
    width,height = texhead.width,texhead.height
    if texhead.swizzleControl == 1:
        trimmedBlocks = [trim(miplevel,blockSize) for texture in datablocks for miplevel in texture]
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

def ASTCtoDDS(filename,texhead,blockSize,data,f):
    bindata = b""
    for tex in data:
        for targetSize,currentSize,texture,packetTexelSize in tex:
            raise ValueError("ASTC is not supported, use a better image format like DDS")
            #rgba = astcToPureRGBA(texture, *currentSize, *blockSize, "Srgb" in f)
            rgba = None
            binImg = toR8G8B8_UNORM([[column for column in row[:targetSize[0]]] for row in rgba[:targetSize[1]]])
            bindata += binImg
    output = Path('.'.join(str(filename).split(".")[:2])).with_suffix(".dds")
    mipCount,imageCount = texhead.mipCount, texhead.imageCount
    cubemap = texhead.cubemapMarker!=0
    result = ddsFromTexData(texhead.height, texhead.width, mipCount, imageCount, "R8G8B8A8UNORM", cubemap,bindata)
    with open(output,"wb") as outf:
        outf.write(result)
    return output

def exportBlocks(filename,texhead,blockSize,t,f,data):
    rfilename = filename
    if "ASTC" in t:
        f = ASTCtoDDS(rfilename,texhead,blockSize,data,f)
    elif "BC" in t:
        f = BCtoDDS(rfilename,texhead,blockSize,data)
    else:
        f = BCtoDDS(rfilename,texhead,blockSize,data)
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
    if True:#"streaming" not in str(filename):
        filename = Path(filename)
        if not filename.exists():
            filename = filename.with_suffix(".tex.28")
        header = TEXHeader.parse_file(filename)
    else:
        header = mergeStreaming(str(filename))
    return _convertFromTex(header,filename)

#from tex_math import swizzle
#def testDeswizzle(block,*args):
#    return deswizzle(swizzle(deswizzle(block,*args),*args),*args)

def _convertFromTex(header,filename):
    if DEBUG:
        print("Tx2: "+ str("%d x %d x %d | %d/%d"%(header.width,header.height,header.depth,header.mipCount,header.imageCount)))
    filename = str(filename).replace(".19","").replace(".28","")
    formatString = reverseFormatEnum[header.format]
    _,blockSizeX,blockSizeY,_ = formatParse(formatString)
    typing,bx,by,formatting = formatTexelParse(formatString)
    datablocks = expandBlockData(header,header.swizzleControl == 1)
    width,height = header.width, header.height
    size = width,height
    packetTexelSize = (bx,by)
    if header.swizzleControl == 1:
        swizzleSize = (header.swizzleData.swizzleWidth,header.swizzleData.swizzleHeight)
        plainBlocks = [[deswizzle(block,size,packetTexelSize,swizzleSize,mip) for mip,block in enumerate(image)] for tix,image in enumerate(datablocks)]
    else:
        plainBlocks = datablocks
    return exportBlocks(filename,header,(blockSizeX,blockSizeY),typing,formatting,plainBlocks)

convert = convertFromTex

def convertToTex(filename,outf = None,salt = 0x1c):
    texHeader = texHeaderFromDDSFile(filename,salt)
    if outf is None:
        outf = str(filename).replace(".dds",".tex")
    with open(outf,"wb") as tex:
        binaryFile = TEXHeader.build(texHeader)
        tex.write(binaryFile)
    return outf