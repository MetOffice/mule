# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the UM utilities module, which use the Mule API.
#
# Mule and these utilities are free software: you can redistribute it and/or
# modify them under the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# These utilities are distributed in the hope that they will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with these utilities.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""Tests for the summary utility in the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import os
import um_utils.tests as tests

from six import StringIO
from um_utils import summary

# Manually change this flag to "True" if you are trying to add a new test -
# this will trigger the testing to save the output if it doens't already
# exist (for development work which adds a new test file)
_ADD_NEW_TESTS = False


class TestSummary(tests.UMUtilsNDTest):

    def run_comparison(self, testname, n_fields=50, **kwargs):
        """
        Main test function, takes the name of a test to provide the
        output file and runs :meth:`summary.field_summary`, then compares
        the output to the expected result.

        """
        # Create a very simple test case - minimal FieldsFile with some fields
        nx, ny, nz = 4, 3, 5
        x0, y0, dx, dy = 10.0, -60.0, 0.1, 0.2
        stagger = 3
        ff = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy, stagger)
        for _ in range(n_fields):
            self.new_p_field(ff)

        # Vary the "stash code" of the fields and add an lbproc code
        lbuser4 = 0
        for field in ff.fields:
            lbuser4 += 100
            field.lbuser4 = lbuser4
            field.lbproc = 0
            field.lbyr = 2001
            field.lbmon = 1
            field.lbdat = 1
            field.lbhr = 12
            field.lbmin = 0
            field.lbsec = 0

        # Run summary on the file, capturing the output to a buffer
        strbuffer = StringIO()
        summary.field_summary(ff, stdout=strbuffer, **kwargs)

        # The expected output is kept in the "output" directory
        expected_output = os.path.join(
            os.path.dirname(__file__),
            "output", "{0}.txt".format(testname))

        if os.path.exists(expected_output):
            # If the expected output file is found, read it in and do an
            # exact comparison of the two files line by line
            with open(expected_output, "r") as fh:
                buffer_lines = strbuffer.getvalue().split("\n")
                expect_lines = fh.read().split("\n")
                for iline, line in enumerate(buffer_lines):
                    self.assertLinesEqual(line, expect_lines[iline])
        else:
            # If the file doesn't exist, either try to create it (if the
            # manual flag is set in this file, otherwise it is an error)
            if _ADD_NEW_TESTS:
                fh = open(expected_output, "w")
                fh.write(strbuffer.getvalue())
            else:
                msg = "Test file not found: {0}"
                raise ValueError(msg.format(expected_output))

    def test_default(self):
        # Test of default summary
        self.run_comparison("default")

    def test_column_names(self):
        # Test of output changing column names
        self.run_comparison("column_names",
                            column_names=["lbuser4", "lbproc"])

    def test_field_index(self):
        # Test of output using the field index
        self.run_comparison("field_index", n_fields=10,
                            field_index=[1, 2, 7])

    def test_field_property(self):
        # Test of output using the field property
        self.run_comparison("field_property", n_fields=10,
                            field_property={"lbuser4": 200, "lbproc": 0})

    def test_heading_freq(self):
        # Testing repetition of headings
        self.run_comparison("heading_freq", heading_frequency=20)


if __name__ == "__main__":
    tests.main()
