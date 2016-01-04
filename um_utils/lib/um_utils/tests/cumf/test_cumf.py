# (C) Crown Copyright 2016, Met Office. All rights reserved.
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

from StringIO import StringIO
from um_utils import cumf


# Disable warnings about the presence of the STASHmaster file
import warnings
warnings.filterwarnings("ignore", r".*unable to load STASHmaster file.*")

# Manually change this flag to "True" if you are trying to add a new test -
# this will trigger the testing to save the output if it doens't already
# exist (for development work which adds a new test file)
_ADD_NEW_TESTS = True

class TestCumf(tests.UMUtilsTest):

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
        ff1 = self._minimal_valid_ff()
        ff1.fields = [self._minimal_valid_field() for _ in range(6)]

        for field in ff1.fields:
            # Make sure the first element is set - or remove_empty_lookups
            # will delete the fields!
            field.raw[1] = 2015

        ff2 = self._minimal_valid_ff()
        ff2.fields = [self._minimal_valid_field() for _ in range(6)]

        for field in ff2.fields:
            # Make sure the first element is set - or remove_empty_lookups
            # will delete the fields!            
            field.raw[1] = 2015

        # Break the headers of field #2 - this field will then fail to be
        # matched in the two files
        ff1.fields[2].lbuser4 = 300
        ff2.fields[2].lbuser4 = 500

        # Field #3 will have different data
        nx, ny = ff1.fields[3].lbnpt, ff1.fields[3].lbrow
        provider = mule.ArrayDataProvider(5.0*np.arange(nx*ny).reshape(nx,ny))
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

if __name__ == "__main__":
    tests.main()
