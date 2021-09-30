import os

class Level(object):

    def __init__(self, name):
        self.name = name
    
    def loadLevel(self, mod):
        configpath = os.path.join(mod.game.root, mod.path, 'levels', self.name)
        with open(configpath, 'r') as config:
            mod.game.parse()
