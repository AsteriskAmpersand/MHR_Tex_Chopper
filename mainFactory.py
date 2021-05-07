# -*- coding: utf-8 -*-
"""
Created on Sun Apr 11 17:30:45 2021

@author: AsteriskAmpersand
"""
gameMapping = {
    "ResidentEvil7" : 8,
    "ResidentEvil2" : 10,
    "DevilMayCry5" : 11,
    "ResidentEvil3" : 190820018,
    "MonsterHunterRise" : 28,
    "ResidentEvilReVerse" : 30
    }

specStr = "Asterisk_MHR_Tex_Chopper"
specTarget = "Asterisk_%s_Tex_Chopper"

versionStr = "VERSION = 0x1C"
versionTarget = "VERSION = %d"

mainStr = "main.py"
mainTarget = "_main_%s.py"
specFileTarget = "_main_%s.spec"

with open("main.spec","r",encoding="utf-8") as mainSpec:
    spec = mainSpec.read()
    
with open("mainBase.py","r",encoding="utf-8") as mainCode:
    code = mainCode.read()

batEntry = "PyInstaller %s"
batcode = r"""cd /d C:\Users\Asterisk\Documents\GitHub\MHR_Tex_Chopper
.\Scripts\activate
PyInstaller main.spec
"""
for game,salt in gameMapping.items():        
    specFileName = specFileTarget%game
    mainFileName = mainTarget%game
    newSpec = spec.replace(mainStr,mainFileName).replace(specStr,specTarget%game)
    newCode = code.replace(versionStr,versionTarget%salt)
    with open(mainFileName,"w",encoding="utf-8") as outf:
        outf.write(newCode)
    with open(specFileName,"w",encoding="utf-8") as outf:
        outf.write(newSpec)
    batcode += "PyInstaller %s\n"%specFileName

with open("List_Compiler.bat","w",encoding="utf-8") as outf:
    outf.write(batcode)