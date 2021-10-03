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
from geometry import Geometry

from mod import get_mod_templates, get_mod_geometries
from objectTemplate import load_templates, load_geometries
from staticobject import Staticobject, parse_config_staticobjects
from vec3 import Vec3


def get_groups(staticobjects: List[Staticobject]):
    return [
        list(group) for _,
        group in groupby(
            sorted(
                staticobjects,
                key=attrgetter('group')),
            attrgetter('group'))]


def replace_template_contents(src, dst, name, new_name, remove_col=False, remove_visible=False):
    patterns_visible = [
        r'^GeometryTemplate.*',
        r'^ObjectTemplate\.geometry.*',
        r'^ObjectTemplate\.cullRadiusScale.*',
    ]

    logging.info(f'moving {src} to {dst}, replacing {name} -> {new_name}')
    with open(dst, 'w') as newconfig:
        with open(src, 'r') as oldconfig:
            contents = oldconfig.read()
            contents = contents.replace(name, new_name)
            for line in contents.splitlines():
                if remove_col:
                    if any([re.findall(pattern, line, re.IGNORECASE)
                            for pattern in patterns_collision]):
                        line = 'rem ' + line
                if remove_visible:
                    if any([re.findall(pattern, line, re.IGNORECASE)
                            for pattern in patterns_visible]):
                        line = 'rem ' + line
                newconfig.write(line + '\n')

def generate_renamed_config(
        src: os.PathLike, dst: os.PathLike,
        name_old: str, name_new: str,
        remove_col=False,
        ):
    patterns_collision = [
        r'^CollisionManager.*',
        r'^ObjectTemplate\.collisionMesh.*',
        r'^ObjectTemplate\.setCollisionMesh.*',
        r'^ObjectTemplate\.mapMaterial.*',
        r'^ObjectTemplate\.hasCollisionPhysics.*',
        r'^ObjectTemplate\.physicsType.*',
    ]

    logging.info(f"generating {dst} with replaced '{name_old}'->'{name_new}' from {dst}")
    with open(dst, 'w') as newconfig:
        with open(src, 'r') as oldconfig:
            contents = oldconfig.read()
            contents = contents.replace(name_old, name_new)
            for line in contents.splitlines():
                if remove_col:
                    if any([re.findall(pattern, line, re.IGNORECASE)
                            for pattern in patterns_collision]):
                        line = 'rem ' + line
                newconfig.write(line + '\n')

def rename_template(
        path_object: os.PathLike,
        old_name: str, new_name: str,
        remove_col: bool,
        ):
    for dirname, dirnames, filenames in os.walk(path_object):
        for filename in filenames:
            root, ext = os.path.splitext(filename)
            if ext in ['.con', '.tweak']:
                old_path = os.path.join(dirname, filename)
                new_filename = filename.replace(old_name, new_name)
                new_path = os.path.join(dirname, new_filename)

                generate_renamed_config(old_path, new_path, old_name, new_name, remove_col)
                logging.info(f'removing {old_path}')
                os.remove(old_path)


def copy_as_custom_template(template_name, new_template_name, templates, dst):
    src = os.path.dirname(templates[template_name])
    dst = os.path.join(dst, new_template_name)

    # cleanup first
    logging.info(f'removing {dst}, ignore_errors')
    shutil.rmtree(dst, ignore_errors=True)

    logging.info(f'copy {src} to {dst}')
    shutil.copytree(src, dst, dirs_exist_ok=True)

    logging.info(f'removing {dst}/meshes')
    shutil.rmtree(os.path.join(dst, 'meshes'))

    return dst

def generate_col(
        staticobject: Staticobject,
        templates: Dict[str, os.PathLike],
        dst: os.PathLike,
        ):
    export_name = f'{staticobject.name}_col'
    if export_name not in os.listdir(dst):
        logging.info(f'copy template {staticobject.name} as {export_name} to {dst}')
        copy_as_custom_template(staticobject.name, export_name, templates, dst)
        rename_template(dst, staticobject.name, export_name, remove_visible=True)
    return os.path.join(export_name, export_name + '.con')

def generate_cluster_visiblemesh(base: Staticobject, staticobjects: List[Staticobject]):
    logging.info(f'merging meshes {[str(staticobject) for staticobject in staticobjects]} into {str(base)}')
    with VisibleMesh(base.geometry.path) as basemesh:
        logging.info(f'rotating base {base.name} for {base.rotation}')
        basemesh.rotate(base.rotation)
        logging.info(f'translating base {base.name} for {base.position}')
        basemesh.translate(base.position)
        for other in staticobjects:
            with VisibleMesh(other.geometry.path) as secondmesh:
                logging.info(f'rotating other {other.name} for {other.rotation}')
                secondmesh.rotate([*other.rotation])
                offset = base.position - other.position
                logging.info(f'translating other {other.name} for {other.position}')
                secondmesh.translate(other.position)
                logging.info(f'merging {other.name} into {base.name}')
                basemesh.merge(secondmesh)
        logging.info(f'translating base {base.name} for {-base.position}')
        basemesh.translate(-base.position)
        logging.info(f'rotating base {base.name} for {-base.rotation}')
        basemesh.rotate(-base.rotation)
    
    return basemesh

def copy_object_to_level(src, dst):
    # cleanup first
    logging.info(f'removing {dst}, ignore_errors')
    shutil.rmtree(dst, ignore_errors=True)

    logging.info(f'copy {src} to {dst}')
    shutil.copytree(src, dst, dirs_exist_ok=True)

def remove_meshes(path_object: os.PathLike):
    path_meshes = os.path.join(path_object, 'meshes')
    logging.info(f'removing {path_meshes}')
    shutil.rmtree(path_meshes, ignore_errors=True)

def get_merged_name(base: Staticobject):
    return f'{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}'

def generate_custom_cluster_object(
        cluster: List[Staticobject],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike, 
        ):
    base = cluster[0]
    src = os.path.dirname(templates[base.name])
    mesh_cluster = generate_cluster_visiblemesh(base, cluster[1:])
    name_cluster = get_merged_name(base)
    dst = os.path.join(levelroot, 'objects', name_cluster)
    copy_object_to_level(src, dst)
    remove_meshes(dst)

    export_path = os.path.join(dst, 'meshes', name_cluster+'.staticmesh')
    logging.info(f'exporting cluster into {export_path}')
    mesh_cluster.export(export_path)

    rename_template(dst, base.name, name_cluster, remove_col=True)

def generate_visible(
        clusters: List[List[Staticobject]],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike,
        ):
    logging.info(f'generating merged visiblemeshes')
    for cluster in clusters:
        logging.info(f'generating merged visiblemesh for {[str(staticobject) for staticobject in cluster]}')
        generate_custom_cluster_object(cluster, templates, levelroot)

def get_clusters(
        groups: List[List[Staticobject]],
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, Geometry],
        ):
    logging.info(f'Testing merges in {[[staticobject.name for staticobject in group] for group in groups]}')

    clusters: List[List[Staticobject]] = []
    tests: Dict[Tuple[Tuple, Tuple], bool] = {}
    for group in groups:
        for id1, staticobject in enumerate(group):
            cluster: List[Staticobject] = []
            for id2, other in enumerate(group):
                test = (
                    (staticobject.geometry, other.geometry),
                    (other.geometry, staticobject.geometry),
                )
                if test in tests.keys():
                    if tests[test]:
                        logging.info(
                            f'skipping merge test [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, adding [{id2}]{other} into cluster')
                        cluster.append(other)
                else:
                    with VisibleMesh(staticobject.geometry.path) as basemesh:
                        with VisibleMesh(other.geometry.path) as othermesh:
                            if basemesh.canMerge(othermesh):
                                logging.info(
                                    f'can merge [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, adding [{id2}]{other} into cluster')
                                cluster.append(other)
                                tests[test] = True
                            else:
                                logging.info(
                                    f'cannot merge [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, skipping [{id2}]{other.geometry}')
                                tests[test] = False
            if cluster not in clusters:
                clusters.append(cluster)
                logging.info(f'added cluster {[_.name for _ in cluster]}')

    return [cluster for cluster in clusters if len(cluster) > 1]

def generate_merged(
        modroot: os.PathLike,
        levelname: str,
        config: os.PathLike,
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, Geometry],
        ):
    levelroot = os.path.join(modroot, 'levels', levelname)
    config_group = os.path.join(levelroot, config)

    staticobjects = parse_config_staticobjects(config_group)

    #load_templates(staticobjects, templates)
    load_geometries(staticobjects, templates, geometries)

    dst = os.path.join(levelroot, 'objects')
    groups = get_groups(staticobjects)
    clusters = get_clusters(groups, templates, geometries)

    generate_visible(clusters, templates, levelroot)
    generate_collisions(clusters)
    raise NotImplementedError('add cols')
    generate_configs(clusters, levelroot)

    raise NotImplementedError('redo all, need cols')
    for group in groups:
        clusters = None
        configs_group: List[str] = []
        for cluster in clusters:
            # copy templates as cols
            #   copy templates directories
            #       rename files
            #       rename contents except collisions
            #       remove visible
            # copy templates as visible
            #   copy base template directory
            #       rename files
            #       rename contents all
            #       remove cols
            config_cluster = merge_cluster(cluster, templates, geometries, dst)
            config_cluster = os.path.join(
                'objects', config_cluster).replace(
                '\\', '/')
            configs_group.append(config_cluster)
        generate_group_config(
            modroot,
            levelroot,
            config_group,
            clusters,
            configs_group)

def generate_group_config(modroot,
                          levelroot,
                          config,
                          clusters: List[List[Staticobject]],
                          configs_cluster: List[str]):
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
            # always assuming first object is merged one
            base = cluster[0]
            cluster_name = f'{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}'
            base.name = cluster_name
            groupconfig.write(base.generateCreateCommands())


def main(args):
    args.root = os.path.join('E:/', 'Games', 'Project Reality')
    args.modPath = os.path.join('mods', 'pr_repo')
    args.level = 'fallujah_west'
    args.fname = 'staticobjects_2.con'

    modroot = os.path.join(args.root, args.modPath)

    logging.info(f'Merging meshes from {modroot}/levels/{args.level}/{args.fname}')
    try:
        geometries = get_mod_geometries(modroot)
        configs = get_mod_templates(modroot)

        generate_merged(modroot, args.level, args.fname, configs, geometries)
    except Exception as err:
        logging.critical(f'Failed to generate merge from {args.fname}', exc_info=err)

    # group objects in editor by mapper
    # generate merge plan:
    #   1. generate json with clusters
    #   2. preflight checks:
    #       merge sizes(indices are 32k)
    #       LM merged size <=2k
    #   3. generate colmeshes without visible geometry
    #   4. merge meshes
    # ...


def set_logging(args):
    if args.verbose is not None:
        # TODO: logging only self module
        logger = logging.getLogger()
        levels = {
            0: logging.ERROR,
            1: logging.INFO,
            2: logging.DEBUG,
        }
        try:
            level = levels[args.verbose]
        except KeyError:
            level = logging.DEBUG
        logger.setLevel(level)
        if level > 0:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        logging.info(
            'Setting logging level to %s',
            logging.getLevelName(
                logging.getLogger().getEffectiveLevel()))


if __name__ == "__main__":
    logging.basicConfig(
        filename=f'{os.path.basename(__file__)}.log',
        filemode='w',
        format='[%(asctime)s] %(levelname)s:%(name)s:%(funcName)s:%(message)s',
        datefmt='%X',
        level=logging.ERROR,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v',
        '--verbose',
        help='Set verbosity level',
        action='count')
    parser.add_argument('--noop', help="Do not perform any actions", type=bool)
    parser.add_argument('--modPath', help="Path to mod relative to game root")
    parser.add_argument('--root', help="Path to game directory")
    parser.add_argument('--in', help="Path to staticobjects.con with groups")
    args = parser.parse_args()
    set_logging(args)

    main(args)
