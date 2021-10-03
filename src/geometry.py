import os

class Geometry(object):

    def __init__(self, name: str, meshpath: os.PathLike):
        self.name = name
        self.path = meshpath
    
    def __str__(self):
        return self.name