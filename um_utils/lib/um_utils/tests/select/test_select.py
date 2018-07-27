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
"""Tests for the select utility in the :mod:`um_utils` module."""

import um_utils.tests as tests
from um_utils import select


class TestSelect(tests.UMUtilsEGTest):

    N_FIELDS = 100

    def run_comparison(self, **kwargs):
        """
        Main test function, generates a test file with varied lookup
        parameters, then passes through any keyword arguments to
        :meth:`select.select` and returns the result.

        """
        # Create a very simple test case - minimal FieldsFile with some fields
        nx, ny, nz = 4, 3, 5
        x0, y0, dx, dy = 10.0, -60.0, 0.1, 0.2
        stagger = 6
        ff = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy, stagger)
        for _ in range(self.N_FIELDS):
            self.new_p_field(ff)

        # Create header differences for select to select on
        lbuser4 = 0
        for ifld, field in enumerate(ff.fields):
            # STASH code varies for every field
            lbuser4 += 100
            field.lbuser4 = lbuser4
            # Proc code is 50/50
            field.lbproc = ifld // (self.N_FIELDS//2)

        # Run select on the file to produce the filtered file
        return select.select(ff, **kwargs)

    def test_include_single(self):
        # Test of including only one item
        fields = self.run_comparison(
            include={"lbuser4": [1100, ]})
        # Should match 1 field
        self.assertEqual(len(fields), 1)
        # Should have the STASH code above
        field = fields[0]
        self.assertEqual(field.lbuser4, 1100)

    def test_exclude_single(self):
        # Test of excluding only one item
        fields = self.run_comparison(
            exclude={"lbuser4": [1100, ]})
        # Should match 1 less than all fields
        self.assertEqual(len(fields), self.N_FIELDS - 1)
        # Should NOT have the STASH code above
        for field in fields:
            self.assertNotEqual(field.lbuser4, 1100)

    def test_include_multi(self):
        # Test of including one item matching many fields
        fields = self.run_comparison(
            include={"lbproc": [0, ]})
        # Should match just over half of the fields
        self.assertEqual(len(fields), self.N_FIELDS//2)

        # All fields should have the lbproc above
        for field in fields:
            self.assertEqual(field.lbproc, 0)

    def test_exclude_multi(self):
        # Test of excluding one item matching many fields
        fields = self.run_comparison(
            exclude={"lbproc": [0, ]})
        # Should match just over half of the fields
        self.assertEqual(len(fields), self.N_FIELDS//2)

        # All fields should NOT have the lbproc above
        for field in fields:
            self.assertNotEqual(field.lbproc, 0)

    def test_include_combo(self):
        # Test of including based on multiple parameters, some which
        # may not match
        fields = self.run_comparison(
            include={"lbproc": [0, ],
                     "lbuser4": [1100, 2000, 6000]})
        # Should match 2 fields (not 6000 as it fails lbproc)
        self.assertEqual(len(fields), 2)

        # All fields should have the lbproc above and one of the two STASHes
        for field in fields:
            self.assertEqual(field.lbproc, 0)
            self.assertIn(field.lbuser4, (1100, 2000))
            self.assertNotEqual(field.lbuser4, 6000)

    def test_exclude_combo(self):
        # Test of excluding based on multiple parameters, some which
        # may not match
        fields = self.run_comparison(
            exclude={"lbproc": [0, ],
                     "lbuser4": [1100, 2000, 6000]})
        # Should match 1 less than half the fields
        self.assertEqual(len(fields), self.N_FIELDS/2 - 1)

        # No fields should have the properties of the above
        for field in fields:
            self.assertNotEqual(field.lbproc, 0)
            self.assertNotEqual(field.lbuser4, 1100)
            self.assertNotEqual(field.lbuser4, 2000)
            self.assertNotEqual(field.lbuser4, 6000)

    def test_include_exclude_combo(self):
        # Test of excluding and including together
        fields = self.run_comparison(
            include={"lbproc": [1, ]},
            exclude={"lbuser4": [1000, 6000, 7000, 8000]})
        # Should match 3 less than half the fields
        self.assertEqual(len(fields), self.N_FIELDS/2 - 3)

        # All fields should have lbproc 1 but the 3 excluded
        # fields should not be present
        for field in fields:
            self.assertEqual(field.lbproc, 1)
            self.assertNotEqual(field.lbuser4, 1000)
            self.assertNotEqual(field.lbuser4, 6000)
            self.assertNotEqual(field.lbuser4, 7000)
            self.assertNotEqual(field.lbuser4, 8000)

    def test_include_all_combo(self):
        # Test of matching everything
        fields = self.run_comparison(
            include={"lbproc": [1, 0]})
        # Should match everything
        self.assertEqual(len(fields), self.N_FIELDS)

    def test_exclude_all_combo(self):
        # Test of excluding resulting in no matches
        fields = self.run_comparison(
            include={"lbproc": [1, 0]},
            exclude={"lbproc": [1, 0]})
        # Should match nothing
        self.assertEqual(len(fields), 0)


if __name__ == "__main__":
    tests.main()
