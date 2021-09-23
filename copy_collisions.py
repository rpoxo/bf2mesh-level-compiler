from merge_group import parse_config_staticobjects
import os
import sys
import shutil
import logging
import argparse
import re
from typing import List, Dict

def get_mod_geometries(root, modPath):
    pattern_geometry_create = r'GeometryTemplate.create StaticMesh (?P<filename>\S+)'
    meshes: Dict[str, str] = {}
    scanpath = os.path.join(root, modPath, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                confile = os.path.join(scanpath, dirname, filename)
                with open(confile, 'r') as config:
                    # GeometryTemplate.create StaticMesh afghannorth_stairs2patioflat
                    staticmeshes = re.findall(pattern_geometry_create, config.read())
                    if staticmeshes:
                        for staticmesh in staticmeshes:
                            meshpath = os.path.join(scanpath, dirname, 'meshes', staticmesh+'.staticmesh')
                            if not os.path.exists(meshpath):
                                message = f'Missing mesh {meshpath}'
                                #raise FileNotFoundError(message)
                                continue
                            meshes[staticmesh] = meshpath
    return meshes

def main(args):
    args.root = os.path.join('E:/', 'Games', 'Project Reality')
    args.modPath = os.path.join('mods', 'pr_repo')
    args.level = 'kokan'
    args.fname = 'StaticObjects_2.con'

    geometries = get_mod_geometries(root, modPath)
    staticobjects = parse_config_staticobjects(fname)


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