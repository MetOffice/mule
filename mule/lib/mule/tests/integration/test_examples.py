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
Integration tests for code examples.

This just stops the examples code from going stale.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import os
import os.path
import sys

import mule
import mule.tests as tests


# Make the examples code dir importable.
# Get the mule module source path.
_mule_path = os.path.dirname(mule.__file__)
# Construct a path to the examples dir (not importable).
_examplecode_dir = os.path.join(_mule_path, 'example_code')
# Add to the import path.
sys.path.append(_examplecode_dir)


import print_file_structure_template as pfst


class Test_print_file_structure(tests.MuleTest):
    def test_example_template(self):
        # Run the example code to get a template string.
        template_string = pfst.get_test_template_string()
        # Execute the template string to get a template.
        # To make this work, we also need access to the numpy 'array' method.
        from numpy import array
        tpl = eval(template_string)
        # Make some checks on the result, to ensure it basically functions.
        self.assertEqual(tpl['fixed_length_header']['dataset_type'], 3)
        self.assertEqual(tpl['integer_constants']['num_cols'], 96)
        self.assertEqual(tpl['real_constants']['start_lat'], -90.0)
        self.assertIsNotNone(tpl['level_dependent_constants'])
        self.assertIsNone(tpl['row_dependent_constants'])


if __name__ == '__main__':
    tests.main()
