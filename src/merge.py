import logging
import argparse
import re
import os
import sys
import shutil
from typing import List, Dict, Tuple
from math import cos, radians, sin
from itertools import groupby, chain
from operator import attrgetter

import bf2mesh
from bf2mesh.visiblemesh import VisibleMesh
from geometry import Geometry

from mod import get_mod_templates, get_mod_geometries
from objectTemplate import ObjectTemplate, load_geometries
from staticobject import Staticobject, parse_config_staticobjects
from vec3 import Vec3


def get_groups(staticobjects: List[Staticobject]) -> List[List[Staticobject]]:
    return [
        list(group) for _,
        group in groupby(
            sorted(
                staticobjects,
                key=attrgetter('group')),
            attrgetter('group'))]

def get_unique_collision_staticobjects(clusters: List[List[Staticobject]]) -> List[Staticobject]:
    seen = set()
    # props to: https://stackoverflow.com/questions/10024646/how-to-get-list-of-objects-with-unique-attribute
    return [seen.add(staticobject.name) or staticobject for staticobject in chain(*clusters) if staticobject.name not in seen]

def generate_renamed_config(
        src: os.PathLike,
        dst: os.PathLike,
        name_old: str,
        name_new: str,
        remove_col: bool = False,
        remove_visible: bool = False,
        ):
    patterns_collision = [
        r'^CollisionManager.*',
        r'^ObjectTemplate\.collisionMesh.*',
        r'^ObjectTemplate\.setCollisionMesh.*',
        r'^ObjectTemplate\.mapMaterial.*',
        r'^ObjectTemplate\.hasCollisionPhysics.*',
        r'^ObjectTemplate\.physicsType.*',
    ]
    patterns_collision_set = [
        r'^ObjectTemplate\.collisionMesh.*',
        r'^ObjectTemplate\.setCollisionMesh.*',
    ]
    patterns_visible = [
        r'^GeometryTemplate.*',
        r'^ObjectTemplate\.geometry.*',
        r'^ObjectTemplate\.cullRadiusScale.*',
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
                if remove_visible:
                    if any([re.findall(pattern, line, re.IGNORECASE)
                            for pattern in patterns_visible]):
                        line = 'rem ' + line
                    # preserve col name
                    if any([re.findall(pattern, line, re.IGNORECASE)
                            for pattern in patterns_collision_set]):
                        line = line.replace(name_new, name_old)
                newconfig.write(line + '\n')

def rename_template(
        path_object: os.PathLike,
        old_name: str,
        new_name: str,
        remove_col: bool = False,
        remove_visible: bool = False,
        ):
    for dirname, dirnames, filenames in os.walk(path_object):
        for filename in filenames:
            root, ext = os.path.splitext(filename)
            if ext in ['.con', '.tweak']:
                old_path = os.path.join(dirname, filename)
                new_filename = filename.replace(old_name, new_name)
                new_path = os.path.join(dirname, new_filename)

                generate_renamed_config(
                    old_path, new_path,
                    old_name, new_name,
                    remove_col, remove_visible
                    )
                logging.info(f'removing {old_path}')
                os.remove(old_path)

def generate_cluster_visiblemesh(
        base: Staticobject,
        staticobjects: List[Staticobject]
        ) -> VisibleMesh:
    logging.info(f'merging meshes {[staticobject.name for staticobject in staticobjects]} into {str(base)}')
    with VisibleMesh(base.geometry.path) as basemesh:
        logging.info(f'rotating base {base.name} for {base.rotation}')
        basemesh.rotate(base.rotation)
        logging.info(f'translating base {base.name} for {base.position}')
        basemesh.translate(base.position)
        for other in staticobjects:
            with VisibleMesh(other.geometry.path) as secondmesh:
                logging.info(f'rotating other {other.name} for {other.rotation}')
                secondmesh.rotate([*other.rotation])

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

def get_merged_name(staticobject: Staticobject):
    return f'{staticobject.name}_merged={"=".join([str(round(axis)) for axis in staticobject.position])}'

def rotate_world_position(position: Vec3, rotation: Vec3) -> Vec3:
    def Rpitch(position: Vec3, angle):
        newX = position.x
        newY = position.y * cos(angle) - position.z * sin(angle)
        newZ = position.y * sin(angle) + position.z * cos(angle)

        return Vec3(newX, newY, newZ)

    def Ryaw(position: Vec3, angle):
        newX = position.x * cos(angle) + position.z * sin(angle)
        newY = position.y
        newZ = position.z * cos(angle) - position.x * sin(angle)

        return Vec3(newX, newY, newZ)

    def Rroll(position: Vec3, angle):
        newX = position.x * cos(angle) - position.y * sin(angle)
        newY = position.x * sin(angle) + position.y * cos(angle)
        newZ = position.z

        return Vec3(newX, newY, newZ)

    logging.debug(f'rotating at {position} by {rotation}')
    yaw, pitch, roll = [radians(axis) for axis in rotation]

    return Ryaw(Rpitch(Rroll(position, roll), pitch), yaw)

def generate_custom_cluster_object(
        cluster: List[Staticobject],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike, 
        ) -> Staticobject:
    base = cluster[0]
    mesh_cluster = generate_cluster_visiblemesh(base, cluster[1:])
    
    # needed due to mesh culling when looking away
    offset = Vec3(*mesh_cluster.get_lod_center_offset(geomId=0, lodId=0))
    logging.info(f'translating mesh centerToObject by {str(offset)}')
    mesh_cluster.translate(-offset)

    cluster_staticobject = Staticobject(base.name)
    # rotate object world to object space, apply offset, rorate back
    new_position = rotate_world_position(base.position, -base.rotation)
    new_position += offset
    new_position = rotate_world_position(new_position, base.rotation)
    logging.info(f'new position {base.position} -> {new_position}')
    cluster_staticobject.setPosition(*new_position)
    cluster_staticobject.setRotation(*base.rotation)
    cluster_staticobject.group = base.group
    name_cluster = get_merged_name(cluster_staticobject)
    cluster_staticobject.name = name_cluster
    cluster_staticobject._template = ObjectTemplate(name_cluster)
    cluster_staticobject._template.config = f'objects/{name_cluster}/{name_cluster}.con'

    src = os.path.dirname(templates[base.name])
    dst = os.path.join(levelroot, 'objects', name_cluster)
    copy_object_to_level(src, dst)
    remove_meshes(dst)

    export_path = os.path.join(dst, 'meshes', name_cluster+'.staticmesh')
    logging.info(f'exporting cluster into {export_path}')
    mesh_cluster.export(export_path)

    rename_template(dst, base.name, name_cluster, remove_col=True)
    return cluster_staticobject

def generate_visible(
        clusters: List[List[Staticobject]],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike,
        ) -> List[Staticobject]:
    logging.info(f'generating merged visiblemeshes')
    merged_cluster: List[Staticobject] = []
    for cluster in clusters:
        logging.info(f'generating merged visiblemesh for {[str(staticobject) for staticobject in cluster]}')
        merged = generate_custom_cluster_object(cluster, templates, levelroot)
        merged_cluster.append(merged)
    
    return merged_cluster

def get_col_name(staticobject: Staticobject):
    return f'{staticobject.name}_col'

def generate_custom_collision_object(
        staticobject: Staticobject,
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike,
        ):
    src = os.path.dirname(templates[staticobject.name])
    name_col = get_col_name(staticobject)
    dst = os.path.join(levelroot, 'objects', name_col)
    copy_object_to_level(src, dst)
    remove_meshes(dst)

    rename_template(dst, staticobject.name, name_col, remove_visible=True)

def generate_custom_collision_objects(
        clusters: List[List[Staticobject]],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike,
        ):
    unique_collisions_staticobjects = get_unique_collision_staticobjects(clusters)
    logging.info(f'unique collisions: {[_.name for _ in unique_collisions_staticobjects]}')
    for staticobject in unique_collisions_staticobjects:
        generate_custom_collision_object(staticobject, templates, levelroot)

def generate_collisions(
        clusters: List[List[Staticobject]],
        templates: Dict[str, os.PathLike],
        levelroot: os.PathLike,
        ) -> List[Staticobject]:
    logging.info(f'generating invinsible collisions')
    generate_custom_collision_objects(clusters, templates, levelroot)

def generate_includes_for_bf2editor(cluster: List[Staticobject]) -> List[str]:
    lines: List[str] = []
    lines.append('if v_arg1 == BF2Editor\n')
    lines.append('console.allowMultipleFileLoad 0\n')
    for staticobject in cluster:
        if staticobject.template and staticobject.template.config:
            logging.info(f'run[{staticobject.name}] {staticobject.template.config}')
            lines.append(f'run {staticobject.template.config}\n')
    lines.append('console.allowMultipleFileLoad 1\n')
    lines.append('endIf\n')

    return lines

def generate_config(
        cluster_visible: List[Staticobject],
        cluster_collisions: List[List[Staticobject]],
        cluster_singleobjects: List[Staticobject],
        levelroot: os.PathLike,
        config_fname: os.PathLike,
        ):
    logging.info(f'generating configs from {[cluster for cluster in zip(cluster_visible, cluster_collisions)]}')

    config_name, ext = os.path.splitext(config_fname)
    configpath = os.path.join(levelroot, f'{config_name}_merged{ext}')
    logging.info(f'writing config to {configpath}')
    with open(configpath, 'w') as clusterconfig:
        #logging.info(f'writing config to {configpath}')
        generated_cluster: List[Staticobject] = []

        for visible, collisions in zip(cluster_visible, cluster_collisions):
            # create merged visible object
            visible_object = Staticobject(visible.name)
            visible_object.setPosition(*visible.position)
            visible_object.setRotation(*visible.rotation)
            visible_object.group = visible.group
            visible_object._template = ObjectTemplate(visible.name)
            visible_object._template.config = f'objects/{visible.name}/{visible.name}.con'
            generated_cluster.append(visible_object)

            # create _col objects
            for staticobject in collisions:
                staticobject.name = get_col_name(staticobject)
                staticobject._template = ObjectTemplate(staticobject.name)
                staticobject._template.config = f'objects/{staticobject.name}/{staticobject.name}.con'
                generated_cluster.append(staticobject)
        
        # add old objects
        for staticobject in cluster_singleobjects:
            generated_cluster.append(staticobject)
        
        clusterconfig.writelines(generate_includes_for_bf2editor(generated_cluster))
        
        for staticobject in generated_cluster:
            clusterconfig.write(staticobject.generateCreateCommands())

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
        config_fname: os.PathLike,
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, Geometry],
        ):
    levelroot = os.path.join(modroot, 'levels', levelname)
    config_group = os.path.join(levelroot, config_fname)

    staticobjects = parse_config_staticobjects(config_group)

    #load_templates(staticobjects, templates)
    load_geometries(staticobjects, templates, geometries)

    dst = os.path.join(levelroot, 'objects')
    groups = get_groups(staticobjects)
    clusters = get_clusters(groups, templates, geometries)
    single_objects = [staticobject for staticobject in staticobjects if staticobject not in chain(*clusters)]

    visible = generate_visible(clusters, templates, levelroot)
    generate_collisions(clusters, templates, levelroot)
    generate_config(visible, clusters, single_objects, levelroot, config_fname)

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
