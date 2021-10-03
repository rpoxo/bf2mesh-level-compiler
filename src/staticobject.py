import os
import re
import logging
from typing import Dict, List
from geometry import Geometry

from vec3 import Vec3



def parse_config_staticobjects(fname: os.PathLike):
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

class Staticobject(object):
    def __init__(self, name: str):
        self.name = name
        self.position = Vec3(0.0, 0.0, 0.0)
        self.rotation = Vec3(0.0, 0.0, 0.0)
        self.group = 0
        self._geometry = None
        self._template = None
    
    def setPosition(self, x, y, z):
        self.position = Vec3(x, y, z)
    
    def setRotation(self, yaw, pitch, roll):
        # bf2 world rotated?
        #self.rotation = Vec3(0 - float(yaw), pitch, roll)
        self.rotation = Vec3(yaw, pitch, roll)
    
    def __str__(self):
        return f'{self.name} ({self.position})'
    
    def _bf2float3str(self, float3: List[float]):
        return f'{float3[0]}/{float3[1]}/{float3[2]}'
    
    def generateCreateCommands(self):
        command = f'''
rem *** {self.name} ***
Object.create {self.name}
Object.absolutePosition {self._bf2float3str([*self.position])}
Object.rotation {self._bf2float3str([*self.rotation])}
Object.layer 1
Object.group {self.group}
'''
        return command
    
    @property
    def template(self):
        return self._template
    
    @property
    def geometry(self):
        return self._geometry
    
    # NOTE: quik hax, developer proper loading from template
    def _setGeometry(self,
        configpath: os.PathLike,
        geometries: Dict[str, Geometry],
        ):
        with open(configpath) as config:
            match = re.search(
                r'ObjectTemplate\.geometry (?P<geometry>\S+)',
                config.read(),
                re.IGNORECASE | re.MULTILINE)
            if match:
                geometryname = match.group('geometry')
                logging.info(f'Found geometry {geometryname} for {self.name}')
                self._geometry = geometries[geometryname]
            else:
                #errmsg = f'could not find mesh path for {self._template.name}'
                errmsg = f'could not find mesh path for {self.name}'
                logging.error(errmsg)
                raise FileNotFoundError(errmsg)