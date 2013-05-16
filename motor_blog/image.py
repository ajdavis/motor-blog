import os
from cStringIO import StringIO

from PIL import Image


def is_retina_filename(filename):
    base, extension = os.path.splitext(filename)
    return base.endswith('@2x')


def regular_from_retina(filename):
    base, extension = os.path.splitext(filename)
    return base.rsplit('@2x', 1)[0] + extension


def resized(data, maxwidth):
    """Returns (data, new width, new height).

    :Parameters:
      - data: A string full of image-file data
      - maxwidth: int
    """
    im = Image.open(StringIO(data))
    width, height = im.size
    factor = maxwidth / float(width)
    if factor > 1:
        return data, width, height

    new_width = int(width * factor)
    new_height = int(height * factor)
    im_resized = im.resize((new_width, new_height), Image.ANTIALIAS)

    out = StringIO()
    im_resized.save(out, im.format)
    return out.getvalue(), new_width, new_height
