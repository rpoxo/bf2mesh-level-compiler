import re
import logging
from vec3 import Vec3

from typing import List

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

class Staticobject(object):
    def __init__(self, name):
        self.name = name
        self.position = Vec3(0.0, 0.0, 0.0)
        self.rotation = Vec3(0.0, 0.0, 0.0)
        self.group = 0
    
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
    
    def getCreateCommands(self):
        command = f'''
rem *** {self.name} ***
Object.create {self.name}
Object.absolutePosition {self._bf2float3str([*self.position])}
Object.rotation {self._bf2float3str([*self.rotation])}
Object.layer 1
Object.group {self.group}
'''
        return command