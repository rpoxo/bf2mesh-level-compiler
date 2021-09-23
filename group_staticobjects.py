import os
import sys
import re
import argparse
import logging
from typing import DefaultDict, Dict, List
from collections import defaultdict

# couldn't make it work with findall
def generate_groups_configs(fname):
    # NOTE: windows using CR LF for ending line, might break pattern
    # NOTE: pattern relies on linebreak between "create" blocks
    pattern_create = r'^Object\.create.*\n(?:Object(?!\.create).*\n?)*'
    pattern_group = r'^Object\.group (?P<groupid>\d+)'

    groups: DefaultDict[int, List[str]] = defaultdict(list)
    with open(fname, 'r') as config:
        for created in re.finditer(pattern_create, config.read(), re.IGNORECASE | re.MULTILINE):
            if created:
                group = re.search(pattern_group, created.group(), re.IGNORECASE | re.MULTILINE)
                if group:
                    groupid = int(group.group('groupid'))
                    groups[groupid].append(created.group())
                else:
                    groups[0].append(created.group())
    
    for groupid, blocks in groups.items():
        root, ext = os.path.splitext(fname)
        new_fname = root + f'_{groupid}' + ext
        with open(new_fname, 'w') as newconfig:
            for commands in blocks:
                newconfig.write('\n')
                newconfig.writelines(commands)
                

def main():
    args.root = os.path.join('E:/', 'Games', 'Project Reality')
    args.modPath = os.path.join('mods', 'pr_repo')
    args.level = 'kokan'
    config_staticobjects = 'StaticObjects.con'

    fname = os.path.join(args.root, args.modPath, 'levels', args.level, config_staticobjects)
    #fname = config_staticobjects
    generate_groups_configs(fname)

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

if __name__ == "__main__":
    logging.basicConfig(
                        filename=f'{os.path.basename(__file__)}.log',
                        filemode='w',
                        format='[%(asctime)s] %(levelname)s:%(name)s:%(message)s',
                        datefmt='%X',
                        level=logging.ERROR,
                        )
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='Set verbosity level', action='count')
    args = parser.parse_args()
    set_logging(args)

    main()

