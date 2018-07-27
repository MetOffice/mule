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
"""Tests for the cumf utility in the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import os
import numpy as np
import um_utils.tests as tests
import mule

from six import StringIO
from um_utils import cumf


# Manually change this flag to "True" if you are trying to add a new test -
# this will trigger the testing to save the output if it doens't already
# exist (for development work which adds a new test file)
_ADD_NEW_TESTS = False


class TestCumf(tests.UMUtilsNDTest):

    def run_comparison(self, ff1, ff2, testname, **kwargs):
        """
        Main test function, takes the name of a test to provide the
        output file and runs a comparison and report, then compares
        the output to the expected result.

        """
        # Create the comparison object
        comp = cumf.UMFileComparison(ff1, ff2, **kwargs)

        # Run cumf to produce reports, capturing the output
        strbuffer = StringIO()
        cumf.full_report(comp, stdout=strbuffer, **kwargs)

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

    def create_2_different_files(self):
        nx, ny, nz = 4, 3, 5
        x0, y0, dx, dy = 10.0, -60.0, 0.1, 0.2
        stagger = 3
        ff1 = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy, stagger)
        for _ in range(7):
            self.new_p_field(ff1)

        for field in ff1.fields:
            # Make sure the first element is set - or remove_empty_lookups
            # will delete the fields!
            field.raw[1] = 2015

        ff2 = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy, stagger)
        for _ in range(7):
            self.new_p_field(ff2)

        for field in ff2.fields:
            # Make sure the first element is set - or remove_empty_lookups
            # will delete the fields!
            field.raw[1] = 2015

        # Break the headers of fields #0 & #2 - this field will then fail to be
        # matched in the two files
        ff1.fields[0].lbuser4 = 2
        ff2.fields[0].lbuser4 = 3
        ff1.fields[2].lbuser4 = 3227
        ff2.fields[2].lbuser4 = 500

        # Make field #6 match, but use an unknown stash code
        ff1.fields[6].lbuser4 = 700
        ff2.fields[6].lbuser4 = 700

        # add a fake STASHmaster
        ff1.attach_stashmaster_info(ff1.stashmaster)
        ff2.attach_stashmaster_info(ff2.stashmaster)

        # Field #3 will have different data
        nx, ny = ff1.fields[3].lbnpt, ff1.fields[3].lbrow
        provider = mule.ArrayDataProvider(5.0*np.arange(nx*ny).reshape(ny, nx))
        ff2.fields[3].set_data_provider(provider)

        # Field #4 will have positional differences
        ff1.fields[4].lbegin = 12345
        ff2.fields[4].lbegin = 67890

        # Add some component differences
        ff1.fixed_length_header.grid_staggering = 3
        ff1.integer_constants.num_p_levels = 38
        ff2.fixed_length_header.grid_staggering = 6
        ff2.level_dependent_constants.raw[:, 1] = np.arange(
            ff2.integer_constants.num_p_levels + 1)*5.0
        ff2.integer_constants.num_p_levels = 70

        # Add dummy source path
        ff1._source_path = "[Test generated file 1]"
        ff2._source_path = "[Test generated file 2]"

        return ff1, ff2

    def test_default(self):
        # Test of default cumf output
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "default")

    def test_ignore_missing(self):
        # Test of the ignore missing option
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "ignore_missing", ignore_missing=True)

    def test_report_successes(self):
        # Test of the full output option
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "report_successes",
                            only_report_failures=False)

    def test_ignore_template(self):
        # Test of the ignore templates
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "ignore_template",
                            ignore_templates={"fixed_length_header": [9],
                                              "integer_constants": [8],
                                              "lookup": [29]})

    def test_show_missing(self):
        # Test of show-missing
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "show_missing",
                            show_missing=True)

    def test_show_missing_maxone(self):
        # Test of show-missing
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "show_missing_maxone",
                            show_missing=True,
                            show_missing_max=1)

    def test_show_missing_full(self):
        # Test of show-missing with full output
        ff1, ff2 = self.create_2_different_files()
        self.run_comparison(ff1, ff2, "show_missing_full",
                            show_missing=True,
                            only_report_failures=False)

    def test_order_missmatch(self):
        # Test of show-missing with full output
        ff1, _ = self.create_2_different_files()
        ff2 = ff1.copy()
        ff2._source_path = "[Test generated file 2]"
        ff2.fields = list(ff1.fields)
        ff2.fields[2], ff2.fields[3] = ff1.fields[3], ff1.fields[2]
        self.run_comparison(ff1, ff2, "no_difference")

    def test_order_missmatch_full(self):
        # Test of show-missing with full output
        ff1, _ = self.create_2_different_files()
        ff2 = ff1.copy()
        ff2._source_path = "[Test generated file 2]"
        ff2.fields = list(ff1.fields)
        ff2.fields[2], ff2.fields[3] = ff1.fields[3], ff1.fields[2]
        self.run_comparison(ff1, ff2, "order_missmatch_full",
                            show_missing=True,
                            only_report_failures=False)

    def test_show_missing_alldifferent(self):
        # Test of show-missing with all fields different
        ff1, ff2 = self.create_2_different_files()
        for field in ff1.fields:
            field.lbuser4 = 300
        for field in ff2.fields:
            field.lbuser4 = 500
        self.run_comparison(ff1, ff2, "show_missing_alldifferent",
                            show_missing=True)

    def test_no_difference(self):
        # Test with no differences
        ff1, _ = self.create_2_different_files()
        ff2 = ff1.copy()
        ff2._source_path = "[Test generated file 2]"
        ff2.fields = list(ff1.fields)
        self.run_comparison(ff1, ff2, "no_difference")

    def test_no_difference_show_missing(self):
        # Test no differences and show-missing (which should
        # do nothing)
        ff1, _ = self.create_2_different_files()
        ff2 = ff1.copy()
        ff2._source_path = "[Test generated file 2]"
        ff2.fields = list(ff1.fields)
        self.run_comparison(ff1, ff2, "no_difference",
                            show_missing=True)

    def test_no_difference_full(self):
        # Test no differences with full output
        ff1, _ = self.create_2_different_files()
        ff2 = ff1.copy()
        ff2._source_path = "[Test generated file 2]"
        ff2.fields = list(ff1.fields)
        self.run_comparison(ff1, ff2, "no_difference_full",
                            only_report_failures=False)

if __name__ == "__main__":
    tests.main()
