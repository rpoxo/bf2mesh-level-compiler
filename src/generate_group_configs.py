import os
import sys
import re
import argparse
import logging
from typing import DefaultDict, List
from collections import defaultdict

# couldn't make it work with findall
def generate_groups_configs(fname: os.PathLike):
    logging.info(f'Generating groups configs from {fname}')
    # NOTE: windows using CR LF for ending line, might break pattern
    # NOTE: pattern relies on linebreak between "create" blocks
    # Credits: thanks paradisebeyound for pattern
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
                    # no group = 0
                    groups[0].append(created.group())
    
    for groupid, blocks in groups.items():
        root, ext = os.path.splitext(fname)
        new_fname = root + f'_{groupid}' + ext
        filename = os.path.basename(new_fname)
        print(filename)
        logging.info(f'Writing config for group {groupid} in {new_fname}')
        with open(new_fname, 'w') as newconfig:
            for commands in blocks:
                newconfig.write('\n')
                newconfig.writelines(commands)

def main(args):
    root = os.path.join('E:/', 'Games', 'Project Reality')
    modPath = os.path.join('mods', 'pr_repo')
    levelname = 'fallujah_west'
    fname = 'StaticObjects.con'
    args.path = os.path.join(root, modPath, 'levels', levelname, fname)

    generate_groups_configs(args.path)

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
    parser.add_argument('--split-groups', help='Split groups by individual config files', action='store_true')
    parser.add_argument('-p', '--path', help='Path to staticobjects.con')
    args = parser.parse_args()
    set_logging(args)

    main(args)

