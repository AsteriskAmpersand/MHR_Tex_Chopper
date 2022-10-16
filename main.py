# -*- coding: utf-8 -*-
"""
Created on Mon Apr  5 11:46:20 2021

@author: AsteriskAmpersand
"""
import sys
from pathlib import Path
from tex import convertFromTex, convertToTex

def main():
    for path in sys.argv[1:]:
        if ".tex" in path:
            convertFromTex(path)
        elif ".dds" in path:
            convertToTex(path)
        else:
            if Path(path).is_dir():
                for spath in Path(path).rglob("*.tex*"):
                    convertFromTex(spath)
                for spath in Path(path).rglob("*.dds"):
                    convertToTex(spath)

if __name__ in "__main__":
    main()