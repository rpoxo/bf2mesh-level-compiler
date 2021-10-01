import os
import re
import logging
from typing import Dict

from geometry import Geometry

def get_mod_geometries(modroot: os.PathLike, ignore_missing=True):
    logging.info(f'Searching for geometries in {modroot}')
    pattern_geometry_create = r'GeometryTemplate.create StaticMesh (?P<filename>\S+)'
    meshes: Dict[str, Geometry] = {}
    scanpath = os.path.join(modroot, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                configpath = os.path.join(scanpath, dirname, filename)
                with open(configpath, 'r') as config:
                    staticmeshes = re.findall(pattern_geometry_create, config.read())
                    if staticmeshes:
                        for staticmesh in staticmeshes:
                            meshpath = os.path.join(scanpath, dirname, 'meshes', staticmesh+'.staticmesh')
                            if not os.path.exists(meshpath):
                                message = f"{configpath}: Missing mesh '{staticmesh}'"
                                logging.warning(message)
                                if not ignore_missing:
                                    raise FileNotFoundError(message)
                            else:
                                meshes[staticmesh] = Geometry(staticmesh, meshpath)
                                logging.info(f"Found geometry '{staticmesh}' in {meshpath}")
    return meshes

def get_mod_templates(modroot: os.PathLike):
    pattern_template_create = r'ObjectTemplate.create (?P<ObjectType>\S+) (?P<ObjectName>\S+)'
    templates: Dict[str, os.PathLike] = {}
    scanpath = os.path.join(modroot, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                configpath = os.path.join(scanpath, dirname, filename)
                with open(configpath, 'r') as config:
                    created = re.findall(pattern_template_create, config.read())
                    if created:
                        for create in created:
                            # AttributeError: 'tuple' object has no attribute 'group'
                            #template = create.group('ObjectName')
                            bf2type = create[0]
                            template = create[1]
                            templates[template] = configpath
                            logging.info(f'Loaded {bf2type} {template} from {configpath}')
    return templates
