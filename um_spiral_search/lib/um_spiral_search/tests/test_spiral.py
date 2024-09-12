# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the SHUMlib spiral search library module.
#
# It is free software: you can redistribute it and/or modify it under
# the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# Mule is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with this SHUMlib spiral search module.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""
Unit tests for :mod:`um_spiral_search` module.

"""

from __future__ import (absolute_import, division, print_function)

import warnings
import numpy as np
import um_spiral_search.tests as tests
from um_spiral_search import spiral_search


class Test_spiral_search(tests.UMSpiralTest):
    # A few constants - we're not going to mess with the planet radius or
    # constraint parameters, so set them up here
    PLANET_RADIUS = 6371229.0
    CONSTRAINED_MAX_DIST = 200000.0
    DIST_STEP = 3

    def test_spiral_search_basic_land_test(self):
        # Our upscaled original mask contains a resolved strip of land along
        # the bottom edge (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  F  F  F  F  F  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[20:] = False

        # Our high-resolution mask contains a couple of small islands which
        # weren't resolved by the lower resolution mask (note that "T" now
        # means land, confusingly the opposite effect of the above!)
        #  .  .  .  .  .  .  .
        #  .  F  F  F  F  F  .
        #  .  F *T* F  F  F  .
        #  .  F  F  F *T* F  .
        #  .  F  F  F  F  F  .
        #  .  T  T  T  T  T  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(False, 25)
        lsm[20:] = True
        lsm[6] = lsm[13] = True

        # It is the indices of these two points which we wish to resolve
        index_unres = np.array([6, 13])
        # Simple lon/lat co-ords - it's not too important but
        # pick something vaguely equatorial to ensure the distances
        # are intuitive
        lats = np.linspace(3, 4, num=5)
        lons = np.linspace(3, 4, num=5)

        # Not wrapping, it's a land field we're calculating and
        # don't worry about constraining it this time
        cyclic = False
        is_land_field = True
        constrained = False

        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point on the
        # bottom shoreline (which in this simple case will be the points
        # directly to the south of each island)
        #  .  .  .  .  .  .  .
        #  .                 .
        #  .     T           .
        #  .     |     T     .
        #  .     |     |     .
        #  .  T  *  T  *  T  .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([21, 23])

        self.assertArrayEqual(indices, expected_indices)

    def test_spiral_search_basic_sea_test(self):
        # Our upscaled original mask contains a resolved block of sea along
        # the top 2 rows (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  F  F  F  F  F  .
        #  .  F  F  F  F  F  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[:10] = False

        # Our high-resolution mask contains and extra bay which wasn't
        # resolved by the lower resolution mask (note that "F" means sea)
        #  .  .  .  .  .  .  .
        #  .  F  F  F  F  F  .
        #  .  F  F  F  F  F  .
        #  .  T *F**F**F* T  .
        #  .  T  T *F**F* T  .
        #  .  T  T  T *F* T  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(True, 25)
        lsm[:10] = False
        lsm[11:14] = False
        lsm[17:19] = False
        lsm[23] = False

        # It is the indices of the points in this bay which we wish to resolve
        index_unres = np.array([11, 12, 13,
                                17, 18,
                                23])
        # Simple lon/lat co-ords - it's not too important but
        # pick something vaguely equatorial to ensure the distances
        # are intuitive
        lats = np.linspace(3, 4, num=5)
        lons = np.linspace(3, 4, num=5)

        # Not wrapping, it's a sea field we're calculating and
        # don't worry about constraining it this time
        cyclic = False
        is_land_field = False
        constrained = False

        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point on the
        # upper open water (which in this simple case will be the points
        # directly to the north of each point (the starred points))
        #  .  .  .  .  .  .  .
        #  .  F  F  F  F  F  .
        #  .  F  *  *  *  F  .
        #  .     F  F  F     .
        #  .        F  F     .
        #  .           F     .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([6, 7, 8,
                                     7, 8,
                                     8])

        self.assertArrayEqual(indices, expected_indices)

    def test_spiral_search_basic_land_cyclic_test(self):
        # Our upscaled original mask contains a block of land on the
        # western most 3 columns (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[0:3] = False
        unres_mask[5:8] = False
        unres_mask[10:13] = False
        unres_mask[15:18] = False
        unres_mask[20:23] = False

        # Our high-resolution mask contains a couple of small islands which
        # weren't resolved by the lower resolution mask (note that "T" now
        # means land, confusingly the opposite effect of the above!)
        #  .  .  .  .  .  .  .
        #  .  T  T  T  F  F  .
        #  .  T  T  T  F *T* .
        #  .  T  T  T  F  F  .
        #  .  T  T  T  F *T* .
        #  .  T  T  T  F  F  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(False, 25)
        lsm[0:3] = True
        lsm[5:8] = True
        lsm[10:13] = True
        lsm[15:18] = True
        lsm[20:23] = True
        lsm[9] = lsm[19] = True

        # It is the indices of these two points which we wish to resolve
        index_unres = np.array([9, 19])
        # For this test pick a short latitude range for simplicity, but
        # the longitudes we want to set it up to test the wrapping. So we
        # want the right-most column to be closer to the left-most column
        # than it is to the central column when wrapping is enabled.
        lats = np.linspace(3, 4, num=5)
        lons = np.array([1.0, 2.0, 357.0, 358.0, 359.0])

        # It's a land field we're calculating and
        # don't worry about constraining it this time
        is_land_field = True
        constrained = False

        # Call the search once with the domain non-wrapping
        cyclic = False
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point on the
        # landmass to the west
        #  .  .  .  .  .  .  .
        #  .  T  T  T        .
        #  .  T  T  * --- T  .
        #  .  T  T  T        .
        #  .  T  T  * --- T  .
        #  .  T  T  T        .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([7, 17])

        self.assertArrayEqual(indices, expected_indices)

        # Now call it again but this time wrap the domain
        cyclic = True
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point which is
        # now the landmass to the *east* since we are wrapping
        #  .  .  .  .  .  .  .
        #  .  T  T  T        .
        #  .--*  T  T     T--.
        #  .  T  T  T        .
        #  .--*  T  T     T--.
        #  .  T  T  T        .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([5, 15])

        self.assertArrayEqual(indices, expected_indices)

    def test_spiral_search_basic_sea_cyclic_test(self):
        # Our upscaled original mask contains a block of sea on the
        # western most 3 columns (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T  T  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[0:3] = False
        unres_mask[5:8] = False
        unres_mask[10:13] = False
        unres_mask[15:18] = False
        unres_mask[20:23] = False

        # Our high-resolution mask contains a couple of small bays which
        # weren't resolved by the lower resolution mask
        #  .  .  .  .  .  .  .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T *F* .
        #  .  F  F  F  T  T  .
        #  .  F  F  F  T *F* .
        #  .  F  F  F  T  T  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(True, 25)
        lsm[0:3] = False
        lsm[5:8] = False
        lsm[10:13] = False
        lsm[15:18] = False
        lsm[20:23] = False
        lsm[9] = lsm[19] = False

        # It is the indices of these two points which we wish to resolve
        index_unres = np.array([9, 19])
        # For this test pick a short latitude range for simplicity, but
        # the longitudes we want to set it up to test the wrapping. So we
        # want the right-most column to be closer to the left-most column
        # than it is to the central column when wrapping is enabled.
        lats = np.linspace(3, 4, num=5)
        lons = np.array([1.0, 2.0, 357.0, 358.0, 359.0])

        # It's a sea field we're calculating and
        # don't worry about constraining it this time
        is_land_field = False
        constrained = False

        # Call the search once with the domain non-wrapping
        cyclic = False
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point on the
        # landmass to the west
        #  .  .  .  .  .  .  .
        #  .  F  F  F        .
        #  .  F  F  * --- F  .
        #  .  F  F  F        .
        #  .  F  F  * --- F  .
        #  .  F  F  F        .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([7, 17])

        self.assertArrayEqual(indices, expected_indices)

        # Now call it again but this time wrap the domain
        cyclic = True
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the points to have resolved to the closest point which is
        # now the landmass to the *east* since we are wrapping
        #  .  .  .  .  .  .  .
        #  .  F  F  F        .
        #  .--*  F  F     F--.
        #  .  F  F  F        .
        #  .--*  F  F     F--.
        #  .  F  F  F        .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([5, 15])

        self.assertArrayEqual(indices, expected_indices)

    def test_spiral_search_constrained_land_test(self):
        # Our upscaled original mask contains a resolved strip of land along
        # the bottom edge (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  F  F  F  F  F  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[20:] = False

        # Our high-resolution mask contains a single island at the top which
        # wasn't resolved by the lower resolution mask (note that "T" now
        # means land, confusingly the opposite effect of the above!)
        #  .  .  .  .  .  .  .
        #  .  F  F *T* F  F  .
        #  .  F  F  F  F  F  .
        #  .  F  F  F  F  F  .
        #  .  F  F  F  F  F  .
        #  .  T  T  T  T  T  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(False, 25)
        lsm[20:] = True
        lsm[2] = True

        # It is the index of this point which we wish to resolve
        index_unres = np.array([2])
        # This time for the coords keep the longitudes simple and closely
        # packed, but make the latitude range large enough that the point
        # will be too far away depending on the constraint
        lats = np.array([3.0, 4.0, 5.0, 6.0, 89.0])
        lons = np.linspace(3, 4, num=5)

        # Not wrapping and a land field
        cyclic = False
        is_land_field = True

        # Start by testing with the constraint turned off
        constrained = False
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the point to have resolved to the closest point on the
        # bottom shoreline
        #  .  .  .  .  .  .  .
        #  .        T        .
        #  .        |        .
        #  .        |        .
        #  .        |        .
        #  .  T  T  *  T  T  .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([22])

        self.assertArrayEqual(indices, expected_indices)

        # Now turn on the constraint - this should cause a warning to be
        # issued that it was unable to find a point within the limit
        constrained = True
        with warnings.catch_warnings(record=True) as warning_msgs:
            warnings.simplefilter("always")
            indices_constrained = None
            indices_constrained = spiral_search(lsm,
                                                index_unres,
                                                unres_mask,
                                                lats,
                                                lons,
                                                self.PLANET_RADIUS,
                                                cyclic,
                                                is_land_field,
                                                constrained,
                                                self.CONSTRAINED_MAX_DIST,
                                                self.DIST_STEP)
            # Check that the warning was raised, and that the call still
            # returned the value
            self.assertEqual(len(warning_msgs), 1)
            self.assertRegex(
                warning_msgs[0].message.args[0],
                "Despite being constrained there were no resolved points "
                "of any type within the limit")
            self.assertIsNotNone(indices_constrained)

        # This was just a warning, so we still expect the point to have
        # resolved to the same point as before
        #  .  .  .  .  .  .  .
        #  .        T        .
        #  .        |        .
        #  .        |        .
        #  .        |        .
        #  .  T  T  *  T  T  .
        #  .  .  .  .  .  .  .
        self.assertArrayEqual(indices_constrained, expected_indices)

    def test_spiral_search_constrained_sea_test(self):
        # Our upscaled original mask contains a resolved strip of sea along
        # the bottom edge (note that "T" means unresolved)
        #  .  .  .  .  .  .  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  F  F  F  F  F  .
        #  .  .  .  .  .  .  .
        unres_mask = np.repeat(True, 25)
        unres_mask[20:] = False

        # Our high-resolution mask contains a single lake at the top which
        # wasn't resolved by the lower resolution mask (note that "T" now
        # means land, confusingly the opposite effect of the above!)
        #  .  .  .  .  .  .  .
        #  .  T  T *F* T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  T  T  T  T  T  .
        #  .  F  F  F  F  F  .
        #  .  .  .  .  .  .  .
        lsm = np.repeat(True, 25)
        lsm[20:] = False
        lsm[2] = False

        # It is the index of this point which we wish to resolve
        index_unres = np.array([2])
        # This time for the coords keep the longitudes simple and closely
        # packed, but make the latitude range large enough that the point
        # will be too far away depending on the constraint
        lats = np.array([3.0, 4.0, 5.0, 6.0, 89.0])
        lons = np.linspace(3, 4, num=5)

        # Not wrapping and a sea field
        cyclic = False
        is_land_field = False

        # Start by testing with the constraint turned off
        constrained = False
        indices = spiral_search(lsm,
                                index_unres,
                                unres_mask,
                                lats,
                                lons,
                                self.PLANET_RADIUS,
                                cyclic,
                                is_land_field,
                                constrained,
                                self.CONSTRAINED_MAX_DIST,
                                self.DIST_STEP)

        # We expect the point to have resolved to the closest point on the
        # bottom shoreline
        #  .  .  .  .  .  .  .
        #  .        F        .
        #  .        |        .
        #  .        |        .
        #  .        |        .
        #  .  F  F  *  F  F  .
        #  .  .  .  .  .  .  .
        expected_indices = np.array([22])

        self.assertArrayEqual(indices, expected_indices)

        # Now turn on the constraint - this should cause a warning to be
        # issued that it was unable to find a point within the limit
        constrained = True
        with warnings.catch_warnings(record=True) as warning_msgs:
            warnings.simplefilter("always")
            indices_constrained = None
            indices_constrained = spiral_search(lsm,
                                                index_unres,
                                                unres_mask,
                                                lats,
                                                lons,
                                                self.PLANET_RADIUS,
                                                cyclic,
                                                is_land_field,
                                                constrained,
                                                self.CONSTRAINED_MAX_DIST,
                                                self.DIST_STEP)
            # Check that the warning was raised, and that the call still
            # returned the value
            self.assertEqual(len(warning_msgs), 1)
            self.assertRegex(
                warning_msgs[0].message.args[0],
                "Despite being constrained there were no resolved points "
                "of any type within the limit")
            self.assertIsNotNone(indices_constrained)

        # This was just a warning, so we still expect the point to have
        # resolved to the same point as before
        #  .  .  .  .  .  .  .
        #  .        F        .
        #  .        |        .
        #  .        |        .
        #  .        |        .
        #  .  F  F  *  F  F  .
        #  .  .  .  .  .  .  .
        self.assertArrayEqual(indices_constrained, expected_indices)


if __name__ == "__main__":
    tests.main()
