"""To support mobile clients we add the CSS rule:

img { max-width: 100%; }

This lets mobile browsers resize images to their containers, but they only
preserve aspect-ratio if the image has no "height" attribute. MarsEdit,
understandably, likes to include the "height" attribute, so we remove it.
"""

import re


img_pat = re.compile(r'<img([^>^<]+)>')
width_pat = re.compile(r'width="(\d+)"')
height_pat = re.compile(r'height="(\d+)"')


def remove_image_sizes(html):
    def sub(img_pat_match):
        # img_text will be like '<img width="600" height="600" src="...">'.
        img_text = img_pat_match.group(0)

        # Remove width and height.
        img_text = width_pat.sub(lambda match: '', img_text)
        img_text = height_pat.sub(lambda match: '', img_text)
        return img_text

    return img_pat.sub(sub, html)
