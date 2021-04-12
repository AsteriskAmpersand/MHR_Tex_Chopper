# -*- coding: utf-8 -*-
"""
Created on Sun Apr 11 00:15:01 2021

@author: AsteriskAmpersand
"""

import sys
from pathlib import Path
from tex2 import convertFromTex, convertToTex

VERSION = 0x1C

def main():
    for path in sys.argv[1:]:
        if ".tex" in path:
            convertFromTex(path)
        elif ".dds" in path:
            convertToTex(path,salt=VERSION)
        else:
            if Path(path).is_dir():
                for spath in Path(path).rglob("*.tex*"):
                    convertFromTex(spath)
                for spath in Path(path).rglob("*.dds"):
                    convertToTex(spath,salt=VERSION)
                    
if __name__ in "__main__":
    main()