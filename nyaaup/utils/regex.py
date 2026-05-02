import re

from nyaaup.utils.collections import first_or_none


def find(pattern, string, group=None, flags=0):
    if group:
        if m := re.search(pattern, string, flags=flags):
            return m.group(group)
    else:
        return first_or_none(re.findall(pattern, string, flags=flags))
