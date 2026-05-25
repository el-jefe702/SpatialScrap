from pathlib import Path
from PIL import Image
import numpy as np
import os
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = Path(WORKSPACE_ROOT) / 'examples' / 'bobs domain.png'
print('exists', path.exists())
with Image.open(path) as im:
    arr = np.array(im)
    print('mode', im.mode, 'shape', arr.shape, 'dtype', arr.dtype)
