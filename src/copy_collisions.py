import os
import sys
import shutil
import logging
import argparse
import re
from typing import List, Dict

from mod import get_mod_geometries
from staticobject import parse_config_staticobjects

def copy_objects():
    pass

def main(args):
    args.root = os.path.join('E:/', 'Games', 'Project Reality')
    args.modPath = os.path.join('mods', 'pr_repo')
    modroot = os.path.join(args.root, args.modPath)
    args.level = 'burning_sands'
    # will be called in func
    args.fname = 'StaticObjects_2.con' 

    geometries = get_mod_geometries(modroot)

    src_objects = os.path.join(modroot, 'objects')
    dst_objects = os.path.join(modroot, 'levels', args.level, 'objects')

    config_fname = os.path.join(modroot, 'levels', args.level, args.fname)
    staticobjects = parse_config_staticobjects(config_fname)

def set_logging(args):
    if args.verbose is not None:
        logger = logging.getLogger()
        levels = {
            0 : logging.ERROR,
            1 : logging.INFO,
            2 : logging.DEBUG,
        }
        try:
            level = levels[args.verbose]
        except KeyError:
            level = logging.DEBUG
        logger.setLevel(level)
        if level > 0:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        logging.info('Setting logging level to %s', logging.getLevelName(logging.getLogger().getEffectiveLevel()))

if __name__ == "__main__":
    logging.basicConfig(
                        filename=f'{os.path.basename(__file__)}.log',
                        filemode='w',
                        format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s',
                        datefmt='%X',
                        level=logging.ERROR,
                        )
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Set verbosity level', action='count')
    args = parser.parse_args()
    set_logging(args)

    main(args)