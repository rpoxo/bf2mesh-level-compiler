import os
import re
from typing import Dict

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
