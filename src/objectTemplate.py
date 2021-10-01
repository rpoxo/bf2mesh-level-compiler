import os
from typing import List, Dict

from staticobject import Staticobject


def load_templates(staticobjects: List[Staticobject], templates: Dict[str, os.PathLike], geometries: Dict[str, os.PathLike]):
    for staticobject in staticobjects:
        staticobject.loadTemplate(templates)

def load_geometries(
        staticobjects: List[Staticobject],
        templates: Dict[str, os.PathLike],
        geometries: Dict[str, os.PathLike],
        ):
    for staticobject in staticobjects:
        staticobject._setGeometry(templates[staticobject.name], geometries)

class ObjectTemplate(object):

    def __init__(self, name):
        self.name = name
        self.config = None

    @property
    def geometry(self):
        return self.__geometry