"""
Collect ST3 projects/workspaces into "Constellations"

When you open or close a constellation, it opens or closes all of the included projects.
"""

from .util import input_handlers as collect
from .util.api import API
from .util import constants as c
