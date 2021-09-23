import os
import re
import logging
from typing import Dict

def get_mod_geometries(modroot):
    pattern_geometry_create = r'GeometryTemplate.create StaticMesh (?P<filename>\S+)'
    meshes: Dict[str, str] = {}
    scanpath = os.path.join(modroot, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                confile = os.path.join(scanpath, dirname, filename)
                with open(confile, 'r') as config:
                    staticmeshes = re.findall(pattern_geometry_create, config.read())
                    if staticmeshes:
                        for staticmesh in staticmeshes:
                            meshpath = os.path.join(scanpath, dirname, 'meshes', staticmesh+'.staticmesh')
                            if not os.path.exists(meshpath):
                                message = f'Missing mesh {meshpath}'
                                #raise FileNotFoundError(message)
                                logging.warning(message)
                                continue
                            meshes[staticmesh] = meshpath
    return meshes

def get_mod_templates(modroot):
    pattern_template_create = r'ObjectTemplate.create (?P<ObjectType>\S+) (?P<filename>\S+)'
    templates: Dict[str, str] = {}
    scanpath = os.path.join(modroot, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                confile = os.path.join(scanpath, dirname, filename)
                with open(confile, 'r') as config:
                    templates = re.findall(pattern_template_create, config.read())
                    if templates:
                        for template in templates:
                            templates[template] = confile
    return templates