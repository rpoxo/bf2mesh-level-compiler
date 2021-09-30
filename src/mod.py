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
    pattern_template_create = r'ObjectTemplate.create (?P<ObjectType>\S+) (?P<ObjectName>\S+)'
    templates: Dict[str, str] = {}
    scanpath = os.path.join(modroot, 'objects')
    for dirname, dirnames, filenames in os.walk(scanpath):
        for filename in filenames:
            if filename.endswith('.con'):
                confile = os.path.join(scanpath, dirname, filename)
                with open(confile, 'r') as config:
                    created = re.findall(pattern_template_create, config.read())
                    if created:
                        for create in created:
                            # AttributeError: 'tuple' object has no attribute 'group'
                            #template = create.group('ObjectName')
                            template = create[1]
                            templates[template] = confile
    return templates

class Mod(object):

    def __init__(self, name, modPath):
        self.name = name
        self.path = modPath

    def loadTemplate(self, name):
        pass