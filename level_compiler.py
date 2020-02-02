import os
import sys
import argparse
import logging

import bf2py.game
import bf2py.level
import bf2mesh

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

def create_custom_nonvis_cols(level, group):
    cloned = []
    for staticobject in group:
        if staticobject not in cloned:
            copy_as_col(staticobject, level)
            cloned.append(staticobject)

def main(args):
    game = bf2py.game.Game(args.path, args.modPath)
    level = bf2py.level.Level(game, args.level)

    groups = get_groups(level)
    logging.debug('len(groups) = %d', len(groups))
    for group in groups:
        create_custom_nonvis_cols(level, group)
        create_custom_visible_merged(level, group)

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
    requiredNamed.add_argument('-p', '--path', help='Path to game root forlder', required=True)
    requiredNamed.add_argument('-m', '--modPath', help='Mod to use as source', required=True)
    requiredNamed.add_argument('-l', '--level', help='Level to compile', required=True)
    args = parser.parse_args()
    set_logging(args)
    main(args)