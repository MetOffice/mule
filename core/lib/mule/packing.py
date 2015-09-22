#!/usr/bin/env python
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
This is a light wrapper to the Mule packing library; which handles the
selection between the UM library (obtainable via UM licence) or the
(free) LIBMO packing library

"""
import os
import sys

# This routine is currently a placeholder - the full integration of the
# different packing routines will be added in a future commit.  In the
# meantime it simply ensures a suitable interface is available.

def wgdos_unpack_field(data_bytes, mdi, rows, cols):
    raise NotImplementedError("No WGDOS packing library available")

def wgdos_pack_field(data, mdi, acc):
    raise NotImplementedError("No WGDOS packing library available")    

