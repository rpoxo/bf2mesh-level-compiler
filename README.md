# bf2mesh-level-compiler - script for merging Battlefield 2 meshes on levels into clusters

Script used for compiling staticmeshes on map into single meshes for saving drawcalls.  
Selection based on editor groups

Dependencies:
``bf2mesh`` - library for parsing and writing Battlefield 2 mesh files 

## TODO:
argsparse arguments, currently path to game root, level, filenames are hardcoded

## Usage:
1. in bfeditor, assign groups to staticobjects, merge will be selecting cluster depending on that
2. ``python src/generate_group_configs.py`` - will generate grouped staticobjects config, ``staticobjects_<groupid>.con``
3. ``python src/merge.py`` - will generate merged visible meshes, non-visible objects, merged config ``staticobjects_<groupid>_merged.con``
