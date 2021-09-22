import os
import sys
import argparse
import logging
import shutil
import itertools
import operator

import bf2py.game
import bf2py.level

def set_logging(args):
    if args.verbose is not None:
        logger = logging.getLogger()
        levels = {
            0 : logging.ERROR,
            1 : logging.INFO,
            2 : logging.DEBUG,
        }
        try:
            level = levels[args.verbose]
        except KeyError:
            level = logging.DEBUG
        logger.setLevel(level)
        if level > 0:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
        logging.info('Setting logging level to %s', logging.getLevelName(logging.getLogger().getEffectiveLevel()))

def get_groups(level):
    groups = {}
    for staticobject in level.getStaticObjects():
        if staticobject.group is not None:
            if staticobject.group not in groups.keys(): groups[staticobject.group] = []
            groups[staticobject.group].append(staticobject)
    return groups

def copy_as_custom(staticobject, level, suffix=None):
    logging.debug('cloning %s as custom to %s' % (staticobject.name, level.name))
    src = os.path.join(level._game.root, level._game.modPath, 'objects', level._game.getTemplateDir(staticobject.name))
    dst = os.path.join(level._game.root, level._game.modPath, 'levels', level.name, 'objects', '_nonvis', staticobject.name)
    logging.debug('shutil.copytree(%s, %s)' % (src, dst))
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    if suffix is not None:
        level._game.rename_template(dst, suffix)

def create_custom_nonvis_cols(level, group):
    cloned = []
    cols = []
    for staticobject in group:
        if staticobject not in cloned:
            copy_as_custom(staticobject, level, suffix='_col')
            cloned.append(staticobject)
        cols.append(staticobject) # TODO: create script

class Staticobject(object):
    def __init__(self, name):
        self.name = name
        self.position = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.group = 0
    
    def setPosition(self, x, y, z):
        self.position = (x, y, z)
    
    def setRotation(self, yaw, pitch, roll):
        self.rotation = (yaw, pitch, roll)

def main(args):
    game = bf2py.game.Game(args.root, args.modPath)
    game.loadLevel(args.level)

    keyfunction = operator.attrgetter('group')
    groups = {groupid: group for groupid, group in itertools.groupby(game.staticobjects, keyfunction)}
    for staticobject in game.staticobjects:
        pass

    #groups = get_groups(level)
    #logging.debug('len(groups) = %d', len(groups))
    #for group in groups:
        #create_custom_nonvis_cols(level, groups[group])
        #create_custom_visible_merged(level, group)
    #

if __name__ == "__main__":
    logging.basicConfig(
                        filename='compiler.log',
                        filemode='w',
                        format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s',
                        datefmt='%X',
                        level=logging.ERROR,
                        )
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Set verbosity level', action='count')
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument('-r', '--root', help='Path to game root forlder', required=True)
    requiredNamed.add_argument('-m', '--modPath', help='Mod to use as source', required=True)
    requiredNamed.add_argument('-l', '--level', help='Level to compile', required=True)
    args = parser.parse_args()
    set_logging(args)
    main(args)