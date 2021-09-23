import logging
import argparse
import re
import os
import sys
from typing import List, Dict
from itertools import groupby
from operator import attrgetter

import bf2mesh
from bf2mesh.visiblemesh import VisibleMesh

from staticobject import Staticobject

def get_mod_meshes(root, modPath):
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

def parse_config_staticobjects(fname):
    # windows using CR LF for ending line
    pattern_create = r'^Object.create (?P<name>.+)\r?\n'
    pattern_create += r'Object.absolutePosition (?P<bf2position>\S+)\r?\n'
    pattern_create += r'Object.rotation (?P<bf2rotation>\S+)\r?\n'
    pattern_create += r'Object.layer (?P<layer>\d+)\r?\n'
    pattern_create += r'Object.group (?P<group>\d+)\r?\n'

    pattern_float3 = r'(-?\d+\.\d+)/(-?\d+\.\d+)/(-?\d+\.\d+)'

    with open(fname, 'r') as staticobjects:
        matches = re.findall(
                            pattern=pattern_create,
                            string=staticobjects.read(),
                            flags=re.IGNORECASE | re.MULTILINE)
    staticobjects: List[Staticobject] = []
    for match in matches:
        name, position, rotation, layer, group = match
        position = re.match(pattern_float3, position)
        rotation = re.match(pattern_float3, rotation)
        if not position:
            logging.warning(match)
        staticobject = Staticobject(name)
        staticobject.setPosition(*position.groups())
        staticobject.setRotation(*rotation.groups())
        staticobject.group = group
        staticobjects.append(staticobject)
    
    return staticobjects

def get_groups(staticobjects):
    return [list(group) for _, group in groupby(sorted(staticobjects, key=attrgetter('group')), attrgetter('group'))]

def merge_cluster(staticobjects: List[Staticobject], geometries):
    base = staticobjects[0]
    with VisibleMesh(geometries[base.name]) as basemesh:
        basemesh.rotate([*base.rotation])
        basemesh.translate(base.position)
        for staticobject in staticobjects[1:]:
            with VisibleMesh(geometries[staticobject.name]) as secondmesh:
                secondmesh.rotate([*staticobject.rotation])
                offset = base.position - staticobject.position
                secondmesh.translate(staticobject.position)
                basemesh.merge(secondmesh)
        basemesh.translate(-base.position)
        export_fname = f'./{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}.staticmesh'
        logging.info(f'exporting in {export_fname}')
        basemesh.export(export_fname)

def get_clusters(group: List[Staticobject], geometries: Dict[str, str]):
    logging.info('getting mergeable clusters from group:')
    logging.info([staticobject.name for staticobject in group])

    clusters: List[tuple[Staticobject]] = []
    tests: Dict[tuple[tuple, tuple], bool] = {}
    for id1, staticobject in enumerate(group):
        cluster: List[Staticobject] = []
        for id2, other in enumerate(group):
            test = (
                (staticobject.name, other.name),
                (other.name, staticobject.name),
            )
            if test in tests.keys():
                if tests[test]:
                    logging.info(f'can skip merge test [{id1}]{staticobject.name} and [{id2}]{other.name}, adding [{id2}]{other.name} into cluster')
                    cluster.append(other)
            else:
                with VisibleMesh(geometries[staticobject.name]) as basemesh:
                    with VisibleMesh(geometries[other.name]) as othermesh:
                        if basemesh.canMerge(othermesh):
                            logging.info(f'can merge [{id1}]{staticobject.name} and [{id2}]{other.name}, adding [{id2}]{other.name} into cluster')
                            cluster.append(other)
                            tests[test] = True
                        else:
                            logging.info(f'can not merge [{id1}]{staticobject.name} and [{id2}]{other.name}, skipping[{id2}]{other.name}')
                            tests[test] = False
        cluster = tuple(cluster)
        if cluster not in clusters:
            clusters.append(cluster)
            logging.info(f'added cluster {[_.name for _ in cluster]}')

    return [cluster for cluster in clusters if len(cluster) > 1]

def merge(groups, geometries):
    for group in groups:
        clusters = get_clusters(group, geometries)
        for cluster in clusters:
            merge_cluster(cluster, geometries)

def main():
    config_staticobjects = 'StaticObjects.con'
    root = os.path.join('E:/', 'Games', 'Project Reality')
    modPath = os.path.join('mods', 'pr_repo')

    staticobjects = parse_config_staticobjects(config_staticobjects)
    geometries = get_mod_meshes(root, modPath)
    groups = get_groups(staticobjects)
    merge(groups, geometries)

    # group objects in editor by mapper
    # generate merge plan:
    #   1. generate json with clusters
    #   2. preflight checks:
    #       merge sizes(indices are 32k)
    #       LM merged size <=2k
    #   3. generate colmeshes without visible geometry
    #   4. merge meshes
    #...


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

    main()