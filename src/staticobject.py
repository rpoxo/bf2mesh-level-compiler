from vec3 import Vec3

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
        self.rotation = Vec3(0 - float(yaw), pitch, roll)
    
    def __str__(self):
        return f'{self.name} ({self.position})'