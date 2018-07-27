# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of Mule.
#
# Mule is free software: you can redistribute it and/or modify it under
# the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# Mule is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with Mule.  If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""
Example code to scan a file and print the key structural information.

The information is printed in the form of a creation template.
cf. `mule.UMFile.from_template`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import numpy as np

from mule import UMFile, Field, Field3, FieldsFile, load_umfile


def template_string_from_mule_file(ffv):
    #
    # This could be an interesting utility function.
    # Maybe it shouldn't print the array values, though ?
    #
    names = [name for name, _ in ffv.COMPONENTS]
    names = ['fixed_length_header'] + names
    result = '\n{'
    for name in names:
        result += '\n "{}":'.format(name)
        comp = getattr(ffv, name, None)
        if not comp:
            result += ' None,\n'
        else:
            dictstr = '\n    {'
            any_done = False
            for name, _ in getattr(comp, 'HEADER_MAPPING', []):
                value = getattr(comp, name)
                if isinstance(value, np.ndarray) or value != comp.MDI:
                    msg = '\n     "{}": {!r},'
                    dictstr += msg.format(name, value)
                    any_done = True
            dictstr += '\n    },\n' if any_done else '},\n'
            result += dictstr
    result += '\n}\n'
    return result


def get_test_template_string():
    from mule.tests import COMMON_N48_TESTDATA_PATH
    ffv = FieldsFile.from_file(COMMON_N48_TESTDATA_PATH)
    template_string = template_string_from_mule_file(ffv)
    return template_string


if __name__ == '__main__':
    template_string = get_test_template_string()
    print(template_string)
