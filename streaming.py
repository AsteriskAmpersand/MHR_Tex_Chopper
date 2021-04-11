# -*- coding: utf-8 -*-
"""
Created on Wed Apr  7 16:08:43 2021

@author: AsteriskAmpersand
"""

from struct import pack, unpack

def convertStreaming(baseFile,streamFile,newFile):
    magic = baseFile.read(4)
    version = baseFile.read(4)#could convert, but its a constant so no need
    width = unpack('H',baseFile.read(2))[0]
    height = unpack('H',baseFile.read(2))[0]
    unkn00 = baseFile.read(2)
    imageCount = baseFile.read(1)
    baseFile.read(1)
    headerEnd = baseFile.read(24)#the rest of this doesn't need to be interpreted, as it should be the same as the main tex
    texture = streamFile.read()
    texSize = len(texture)
    #this should be all of the information needed for the texture
    newFile.write(magic)
    newFile.write(version)
    newFile.write(pack('H',width*2))
    newFile.write(pack('H',height*2))
    newFile.write(unkn00)
    newFile.write(imageCount)
    newFile.write(b'\x10')
    newFile.write(headerEnd)
    newFile.write(pack('Q',newFile.tell()+16))
    newFile.write(pack('I',texSize))
    newFile.write(pack('I',width*height))
    newFile.write(texture)