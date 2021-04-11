# -*- coding: utf-8 -*-
"""
Created on Thu Apr  1 18:55:55 2021

@author: AsteriskAmpersand
"""

import construct as C
import astc_decomp

astc = C.Struct(
    "magic" / C.Const(0x5CA1AB13,C.Int32ul),
    "blockdim" / C.Int8ul[3],
    "width" / C.Int24ul,   
    "height" / C.Int24ul,    
    "depth" / C.Int24ul,
    )

def astcFromTexData(h,w,bx,by,data):
    header = {
                "magic" : 0x5CA1AB13,
                "blockdim": [bx,by,1],
                "width": w,
                "height": h,
                "depth": 1,
                }
    return astc.build(header)+data



def bytesToRGBA(data,w,h,bw,bh):
    #rgba = [(int(r),int(g),int(b),int(a)) for r,g,b,a in zip(data[0::4],data[1::4],data[2::4],data[3::4])]
    def accessData(x,y):
        return tuple(map(int,data[(x+y*w)*4:(x+y*w)*4+4]))
    return [accessData(i+si*bw,j+sj*bh) for sj in range(h//bh) for si in range(w//bw) for j in range(bh) for i in range(bw) ]

def astcToRGBA(data,w,h,bw,bh,srgb):
    image = astc_decomp.decompress_astc(data,w,h,bw,bh,srgb)
    return bytesToRGBA(image,w,h,bw,bh)
 
def astcToPureRGBA(data,w,h,bw,bh,srgb):
    image = astc_decomp.decompress_astc(data,w,h,bw,bh,srgb)
    rgba = iter(((int(r),int(g),int(b),int(a)) for r,g,b,a in zip(image[0::4],image[1::4],image[2::4],image[3::4])))
    return [[next(rgba) for r in range(w)] for c in range(h)]
