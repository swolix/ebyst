#!/usr/bin/env python3
import os
import logging

from ebyst.stapl import StaplFile

logger = logging.getLogger(__name__)

def get_all_stapls(root):
    ret = []
    for (root, dirs, files) in os.walk(root):
        for dir in dirs:
            ret += get_all_stapls(dir)
        for file in files:
            if os.path.splitext(file.lower())[-1] in (".stapl"):
                ret.append(os.path.join(root, file))
    return ret

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    for fn in get_all_stapls("stapl"):
        logger.info(f"Parsing {fn}")
        with open(fn, "r") as f:
            dev = StaplFile.parse(f)