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


def get_groups(staticobjects: List[Staticobject]):
    return [
        list(group) for _,
        group in groupby(
            sorted(
                staticobjects,
                key=attrgetter('group')),
            attrgetter('group'))]


def generate_template_visible_only(src, dst, name, new_name):
    patterns_collision = [
        r'^CollisionManager.*',
        r'^ObjectTemplate\.collisionMesh.*',
        r'^ObjectTemplate\.mapMaterial.*',
        r'^ObjectTemplate\.hasCollisionPhysics.*',
        r'^ObjectTemplate\.physicsType.*',
    ]

    logging.info(f'cloning {src} to {dst}, replacing {name} -> {new_name}')
    with open(dst, 'w') as newconfig:
        with open(src, 'r') as oldconfig:
            contents = oldconfig.read()
            contents = contents.replace(name, new_name)
            for line in contents.splitlines():
                if any([re.findall(pattern, line, re.IGNORECASE)
                        for pattern in patterns_collision]):
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

                generate_template_visible_only(
                    old_path, new_path, name, new_name)
                logging.info(f'removing {old_path}')
                os.remove(old_path)


def copy_as_custom_template(template_name, new_template_name, templates, dst):
    src = os.path.dirname(templates[template_name])
    dst = os.path.join(dst, new_template_name)
    logging.info(f'copy {src} to {dst}')
    # cleanup first
    logging.info(f'removing {dst}, ignore_errors')
    shutil.rmtree(dst, ignore_errors=True)

    logging.info(f'copy {src} to {dst}')
    shutil.copytree(src, dst, dirs_exist_ok=True)

    logging.info(f'removing {dst}/meshes')
    shutil.rmtree(os.path.join(dst, 'meshes'))

    rename_template(dst, template_name, new_template_name)


def merge_cluster(
        staticobjects: List[Staticobject],
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, Geometry],
        dst: os.PathLike,
        ):
    base = staticobjects[0]
    with VisibleMesh(base.geometry.path) as basemesh:
        logging.info(f'rotating base {base.name} for {base.rotation}')
        basemesh.rotate(base.rotation)
        logging.info(f'translating base {base.name} for {base.position}')
        basemesh.translate(base.position)
        for other in staticobjects[1:]:
            with VisibleMesh(other.geometry.path) as secondmesh:
                secondmesh.rotate([*other.rotation])
                offset = base.position - other.position
                secondmesh.translate(other.position)
                basemesh.merge(secondmesh)
        logging.info(f'translating base {base.name} for {-base.position}')
        basemesh.translate(-base.position)
        logging.info(f'rotating base {base.name} for {-base.rotation}')
        basemesh.rotate(-base.rotation)
        export_name = f'{base.name}_merged={"=".join([str(round(axis)) for axis in base.position])}'
        # NOTE: for some reason bf2 culls meshes if they not centered to bounding box
        # Need to test if need to adjust whole mesh, or bounding box enough
        raise NotImplementedError(f'add CenterToObject')
        export_fname = os.path.join(
            dst,
            export_name,
            'meshes',
            export_name +
            '.staticmesh')
        copy_as_custom_template(base.name, export_name, templates, dst)
        logging.info(f'exporting in {export_fname}')
        basemesh.export(export_fname)

    return os.path.join(export_name, export_name + '.con')

def get_clusters(
        group: List[Staticobject],
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, Geometry],
        ):
    logging.info(f'Testing merges in group {group[0].group}')
    logging.info([staticobject.name for staticobject in group])

    clusters: List[Tuple[Staticobject, ...]] = []
    tests: Dict[Tuple[Tuple, Tuple], bool] = {}
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
                        f'can skip merge test [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, adding [{id2}]{other.geometry} into cluster')
                    cluster.append(other)
            else:
                with VisibleMesh(staticobject.geometry.path) as basemesh:
                    with VisibleMesh(other.geometry.path) as othermesh:
                        if basemesh.canMerge(othermesh):
                            logging.info(
                                f'can merge [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, adding [{id2}]{other.geometry} into cluster')
                            cluster.append(other)
                            tests[test] = True
                        else:
                            logging.info(
                                f'can not merge [{id1}]{staticobject.geometry} and [{id2}]{other.geometry}, skipping[{id2}]{other.geometry}')
                            tests[test] = False
        cluster = tuple(cluster)
        if cluster not in clusters:
            clusters.append(cluster)
            logging.info(f'added cluster {[_.name for _ in cluster]}')

    return [cluster for cluster in clusters if len(cluster) > 1]


def merge_group(
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

    for group in groups:
        clusters = get_clusters(group, templates, geometries)
        configs_group: List[str] = []
        for cluster in clusters:
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

    geometries = get_mod_geometries(modroot)
    configs = get_mod_templates(modroot)

    merge_group(modroot, args.level, args.fname, configs, geometries)

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
        logger = logging.getLogger(__name__)
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
        format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s',
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
