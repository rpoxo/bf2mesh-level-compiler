import logging
import argparse
import re
import os
import sys
import shutil
from typing import List, Dict, Tuple
from itertools import groupby
from operator import attrgetter

import bf2mesh
from bf2mesh.visiblemesh import VisibleMesh

from mod import get_mod_templates, get_mod_geometries
from staticobject import Staticobject, parse_config_staticobjects

def get_groups(staticobjects):
    return [list(group) for _, group in groupby(sorted(staticobjects, key=attrgetter('group')), attrgetter('group'))]

def generate_template_visible_only(src, dst, name, new_name):
    patterns_collision = [
        r'^CollisionManager.*',
        r'^ObjectTemplate\.collisionMesh.*',
        r'^ObjectTemplate\.mapMaterial.*',
        r'^ObjectTemplate\.hasCollisionPhysics.*',
        r'^ObjectTemplate\.physicsType.*',
    ]
    
    # replace contents
    with open(dst, 'w') as newconfig:
        with open(src, 'r') as oldconfig:
            contents = oldconfig.read()
            contents = contents.replace(name, new_name)
            for line in contents.splitlines():
                if any([re.findall(pattern, line, re.IGNORECASE) for pattern in patterns_collision]):
                    line = 'rem ' + line
                newconfig.write(line + '\n')

def rename_template(src, name, new_name):
    for dirname, dirnames, filenames in os.walk(src):
        for filename in filenames:
            root, ext = os.path.splitext(filename)
            if ext in ['.con', '.tweak']:
                old_path = os.path.join(dirname, filename)
                new_filename = filename.replace(name, new_name)
                new_path = os.path.join(dirname, new_filename)

                generate_template_visible_only(old_path, new_path, name, new_name)
                logging.info(f'removing {old_path}')
                os.remove(old_path)

def copy_as_custom_template(template_name, new_template_name, templates, dst):
    src = os.path.dirname(templates[template_name])
    dst = os.path.join(dst, new_template_name)
    logging.info(f'copy {src} to {dst}')
    # cleanup first
    shutil.rmtree(dst, ignore_errors=True)
    
    shutil.copytree(src, dst, dirs_exist_ok=True)
    shutil.rmtree(os.path.join(dst, 'meshes'))

    rename_template(dst, template_name, new_template_name)

def merge_cluster(staticobjects: List[Staticobject], templates, geometries, dst):
    base = staticobjects[0]
    with VisibleMesh(geometries[base.name]) as basemesh:
        logging.info(f'rotating base {base.name} for {base.rotation}')
        basemesh.rotate(base.rotation)
        logging.info(f'translating base {base.name} for {base.position}')
        basemesh.translate(base.position)
        for staticobject in staticobjects[1:]:
            meshpath = get_meshpath(geometries, templates, staticobject.name)
            with VisibleMesh(meshpath) as secondmesh:
                secondmesh.rotate([*staticobject.rotation])
                offset = base.position - staticobject.position
                secondmesh.translate(staticobject.position)
                basemesh.merge(secondmesh)
        logging.info(f'translating base {base.name} for {-base.position}')
        basemesh.translate(-base.position)
        logging.info(f'rotating base {base.name} for {-base.rotation}')
        basemesh.rotate(-base.rotation)
        export_name = f'{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}'
        export_fname = os.path.join(dst, export_name, 'meshes', export_name+'.staticmesh')
        copy_as_custom_template(base.name, export_name, templates, dst)
        logging.info(f'exporting in {export_fname}')
        basemesh.export(export_fname)
    
    return os.path.join(export_name, export_name+'.con')

def get_meshpath(geometries, templates, templatename):
    try:
        meshpath = geometries[templatename]
    except KeyError as err:
        logging.warning(f'Could not find mesh path for {templatename}, looking in templates...')
        with open(templates[templatename]) as secondconfig:
            match = re.search(r'ObjectTemplate\.geometry (?P<geometry>\S+)', secondconfig.read(), re.IGNORECASE | re.MULTILINE)
            if match:
                geometryname = match.group('geometry')
                logging.warning(f'Found geometry {geometryname}')
                meshpath = geometries[geometryname]
            else:
                logging.error(f'could not find mesh path for {templatename}')
    return meshpath

def get_clusters(group: List[Staticobject], templates: Dict[str, str], geometries: Dict[str, str]):
    logging.info('getting mergeable clusters from group:')
    logging.info([staticobject.name for staticobject in group])

    clusters: List[Tuple[Staticobject, ...]] = []
    tests: Dict[Tuple[Tuple, Tuple], bool] = {}
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
                meshpath = get_meshpath(geometries, templates, staticobject.name)
                with VisibleMesh(meshpath) as basemesh:
                    meshpath = get_meshpath(geometries, templates, other.name)
                    with VisibleMesh(meshpath) as othermesh:
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

def merge_group(modroot, levelname, config, templates: Dict[str, str], geometries: Dict[str, str]):
    levelroot = os.path.join(modroot, 'levels', levelname)
    config_group = os.path.join(levelroot, config)
    staticobjects = parse_config_staticobjects(config_group)
    
    dst = os.path.join(levelroot, 'objects')
    groups = get_groups(staticobjects)

    for group in groups:
        clusters = get_clusters(group, templates, geometries)
        configs_group: List[str] = []
        for cluster in clusters:
            config_cluster = merge_cluster(cluster, templates, geometries, dst)
            config_cluster = os.path.join('objects', config_cluster).replace('\\', '/')
            configs_group.append(config_cluster)
        generate_group_config(modroot, levelroot, config_group, clusters, configs_group)

def generate_group_config(modroot, levelroot, config, clusters: List[List[Staticobject]], configs_cluster: List[str]):
    config_group = os.path.join(levelroot, config)
    root, ext = os.path.splitext(config_group)
    new_config_group = root + '_vismeshes' + ext
    logging.info(f'writing merged group config to {new_config_group}')
    with open(new_config_group, 'w') as groupconfig:
        groupconfig.write('if v_arg1 == BF2Editor\n')
        groupconfig.write('console.allowMultipleFileLoad 0\n')
        for config_cluster in configs_cluster:
            groupconfig.write(f'run {config_cluster}\n')
        groupconfig.write('console.allowMultipleFileLoad 1\n')
        groupconfig.write('endIf\n')
        for cluster in clusters:
            base = cluster[0]
            cluster_name = f'{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}'
            base.name = cluster_name
            groupconfig.write(base.getCreateCommands())

def main():
    root = os.path.join('E:/', 'Games', 'Project Reality')
    modPath = os.path.join('mods', 'pr_repo')
    modroot = os.path.join(root, modPath)
    levelname = 'burning_sands'
    config_groups = [
        'StaticObjects_1.con',
        'StaticObjects_2.con',
        'StaticObjects_3.con',
    ]

    geometries = get_mod_geometries(modroot)
    templates = get_mod_templates(modroot)
    for config_group in config_groups:
        merge_group(modroot, levelname, config_group, templates, geometries)

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