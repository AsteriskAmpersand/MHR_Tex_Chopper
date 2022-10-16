# -*- coding: utf-8 -*-
"""
Created on Thu Mar 25 21:09:41 2021

@author: AsteriskAmpersand
"""
import re

AstcRegex = re.compile("(ASTC)([0-9]+)X([0-9]+)(.*)")
BCRegex = re.compile("(BC[0-9]+H?)(.*)")
RGBRegex = re.compile("([RGBAX][0-9]+)?"*5+"(.*)")
RGBChannel = re.compile("([RGBAX])([0-9]+)")

def getBCBPP(BC):
    BC = BC.upper()
    #print("FE: "+BC)
    if "BC1" in BC: return 8
    if "BC2" in BC: return 16
    if "BC3" in BC: return 16
    if "BC4" in BC: return 8
    if "BC5" in BC: return 16
    if "BC6H" in BC: return 16
    if "BC7" in BC: return 16

def formatParse(formatString):
    astc = AstcRegex.match(formatString)
    if astc:
        ASTC,bx,by,f = astc.groups()
        return (ASTC,int(bx),int(by),f)
    bc = BCRegex.match(formatString)
    if bc:
        BC,f = bc.groups()
        return (BC,4,4,f)
    rgb = RGBRegex.match(formatString)
    if rgb:
        channels = []
        bitlen = 0
        for g in rgb.groups()[:-1]:
            if g:
                c,s = RGBChannel.match(str(g)).groups()            
                channels.append((c,int(s)))
                bitlen += int(s)
        bytelen = (bitlen + 7)//8
        xpacketlen = 16//bytelen
        ypacketlen = 1
        return (channels,1,ypacketlen,rgb.groups()[-1])
    raise ValueError("Unparseable Format Error")

def formatTexelParse(formatString):
    astc = AstcRegex.match(formatString)
    if astc:
        ASTC,bx,by,f = astc.groups()
        return (ASTC,int(bx),int(by),f)
    bc = BCRegex.match(formatString)
    if bc:
        BC,f = bc.groups()
        hcount = 16//getBCBPP(BC)
        return (BC,4*hcount,4,f)
    rgb = RGBRegex.match(formatString)
    if rgb:
        channels = []
        bitlen = 0
        for g in rgb.groups()[:-1]:
            if g:
                c,s = RGBChannel.match(str(g)).groups()            
                channels.append((c,int(s)))
                bitlen += int(s)
        bytelen = (bitlen + 7)//8
        xpacketlen = 16//bytelen
        ypacketlen = 1
        return (channels,xpacketlen,ypacketlen,rgb.groups()[-1])
    raise ValueError("Unparseable Format Error")
    
packetTexelparse = formatTexelParse

#RE Engine Swizzable formats
swizzableFormats = [28,30]#MHRise, ResidentEvilReVerse
swizzledFormats = []

formatEnum = {
    "A8Unorm":0x41,
    "Astc10x10Typeless":0x422,
    "Astc10x10Unorm":0x423,
    "Astc10x10UnormSrgb":0x424,
    "Astc10x5Typeless":0x419,
    "Astc10x5Unorm":0x41a,
    "Astc10x5UnormSrgb":0x41b,
    "Astc10x6Typeless":0x41c,
    "Astc10x6Unorm":0x41d,
    "Astc10x6UnormSrgb":0x41e,
    "Astc10x8Typeless":0x41f,
    "Astc10x8Unorm":0x420,
    "Astc10x8UnormSrgb":0x421,
    "Astc12x10Typeless":0x425,
    "Astc12x10Unorm":0x426,
    "Astc12x10UnormSrgb":0x427,
    "Astc12x12Typeless":0x428,
    "Astc12x12Unorm":0x429,
    "Astc12x12UnormSrgb":0x42a,
    "Astc4x4Typeless":0x401,
    "Astc4x4Unorm":0x402,
    "Astc4x4UnormSrgb":0x403,
    "Astc5x4Typeless":0x404,
    "Astc5x4Unorm":0x405,
    "Astc5x4UnormSrgb":0x406,
    "Astc5x5Typeless":0x407,
    "Astc5x5Unorm":0x408,
    "Astc5x5UnormSrgb":0x409,
    "Astc6x5Typeless":0x40a,
    "Astc6x5Unorm":0x40b,
    "Astc6x5UnormSrgb":0x40c,
    "Astc6x6Typeless":0x40d,
    "Astc6x6Unorm":0x40e,
    "Astc6x6UnormSrgb":0x40f,
    "Astc8x5Typeless":0x410,
    "Astc8x5Unorm":0x411,
    "Astc8x5UnormSrgb":0x412,
    "Astc8x6Typeless":0x413,
    "Astc8x6Unorm":0x414,
    "Astc8x6UnormSrgb":0x415,
    "Astc8x8Typeless":0x416,
    "Astc8x8Unorm":0x417,
    "Astc8x8UnormSrgb":0x418,
    "B5G5R5A1Unorm":0x56,
    "B5G6R5Unorm":0x55,
    "B8G8R8A8Typeless":0x5a,
    "B8G8R8A8Unorm":0x57,
    "B8G8R8A8UnormSrgb":0x5b,
    "B8G8R8X8Typeless":0x5c,
    "B8G8R8X8Unorm":0x58,
    "B8G8R8X8UnormSrgb":0x5d,
    "Bc1Typeless":0x46,
    "Bc1Unorm":0x47,
    "Bc1UnormSrgb":0x48,
    "Bc2Typeless":0x49,
    "Bc2Unorm":0x4a,
    "Bc2UnormSrgb":0x4b,
    "Bc3Typeless":0x4c,
    "Bc3Unorm":0x4d,
    "Bc3UnormSrgb":0x4e,
    "Bc4Snorm":0x51,
    "Bc4Typeless":0x4f,
    "Bc4Unorm":0x50,
    "Bc5Snorm":0x54,
    "Bc5Typeless":0x52,
    "Bc5Unorm":0x53,
    "Bc6hSF16":0x60,
    "Bc6hTypeless":0x5e,
    "Bc6hUF16":0x5f,
    "Bc7Typeless":0x61,
    "Bc7Unorm":0x62,
    "Bc7UnormSrgb":0x63,
    "D16Unorm":0x37,
    "D24UnormS8Uint":0x2d,
    "D32Float":0x28,
    "D32FloatS8X24Uint":0x14,
    "ForceUint":0x7fffffff,
    "G8R8G8B8Unorm":0x45,
    "R10G10B10A2Typeless":0x17,
    "R10G10B10A2Uint":0x19,
    "R10G10B10A2Unorm":0x18,
    "R10G10B10xrBiasA2Unorm":0x59,
    "R11G11B10Float":0x1a,
    "R16Float":0x36,
    "R16G16B16A16Float":0xa,
    "R16G16B16A16Sint":0xe,
    "R16G16B16A16Snorm":0xd,
    "R16G16B16A16Typeless":0x9,
    "R16G16B16A16Uint":0xc,
    "R16G16B16A16Unorm":0xb,
    "R16G16Float":0x22,
    "R16G16Sint":0x26,
    "R16G16Snorm":0x25,
    "R16G16Typeless":0x21,
    "R16G16Uint":0x24,
    "R16G16Unorm":0x23,
    "R16Sint":0x3b,
    "R16Snorm":0x3a,
    "R16Typeless":0x35,
    "R16Uint":0x39,
    "R16Unorm":0x38,
    "R1Unorm":0x42,
    "R24G8Typeless":0x2c,
    "R24UnormX8Typeless":0x2e,
    "R32Float":0x29,
    "R32FloatX8X24Typeless":0x15,
    "R32G32B32A32Float":0x2,
    "R32G32B32A32Sint":0x4,
    "R32G32B32A32Typeless":0x1,
    "R32G32B32A32Uint":0x3,
    "R32G32B32Float":0x6,
    "R32G32B32Sint":0x8,
    "R32G32B32Typeless":0x5,
    "R32G32B32Uint":0x7,
    "R32G32Float":0x10,
    "R32G32Sint":0x12,
    "R32G32Typeless":0xf,
    "R32G32Uint":0x11,
    "R32G8X24Typeless":0x13,
    "R32Sint":0x2b,
    "R32Typeless":0x27,
    "R32Uint":0x2a,
    "R8G8B8A8Sint":0x20,
    "R8G8B8A8Snorm":0x1f,
    "R8G8B8A8Typeless":0x1b,
    "R8G8B8A8Uint":0x1e,
    "R8G8B8A8Unorm":0x1c,
    "R8G8B8A8UnormSrgb":0x1d,
    "R8G8B8G8Unorm":0x44,
    "R8G8Sint":0x34,
    "R8G8Snorm":0x33,
    "R8G8Typeless":0x30,
    "R8G8Uint":0x32,
    "R8G8Unorm":0x31,
    "R8Sint":0x40,
    "R8Snorm":0x3f,
    "R8Typeless":0x3c,
    "R8Uint":0x3e,
    "R8Unorm":0x3d,
    "R9G9B9E5Sharedexp":0x43,
    "ViaExtension":0x400,
    "X24TypelessG8Uint":0x2f,
    "X32TypelessG8X24Uint":0x16,
}
formatEnum={key.upper():val for key,val in formatEnum.items()}
reverseFormatEnum = {val:key for key,val in formatEnum.items()}

def packetSize(formatName):
    if formatName is not str:
        formatName = formatEnum[formatName]
    return formatParse(formatName)[1:3]
    