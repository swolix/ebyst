#!/usr/bin/env python3
import os
import logging

import ebyst

logger = logging.getLogger(__name__)

def get_all_bsdls(root):
    ret = []
    for (root, dirs, files) in os.walk(root):
        for dir in dirs:
            ret += get_all_bsdls(dir)
        for file in files:
            if os.path.splitext(file.lower())[-1] in (".bsm", ".bsd", ".bsdl"):
                ret.append(os.path.join(root, file))
    return ret

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    for fn in get_all_bsdls("bsdl"):
        logger.info(f"Parsing {fn}")
        dev = ebyst.Device.from_bsdl(fn)