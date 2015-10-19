#!/usr/bin/env python
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
import numpy as np
from mule import FieldsFile, DataOperator
from um_utils.stashmaster import STASHmaster

# The STASHmaster is needed by cutout in order to lookup the relevant
# grid information for the fields
STASH = STASHmaster()

class CutoutDataOperator(DataOperator):
    """
    Operator which extracts a new Field representing a sub-region
    of an existing Field
    
    """
    def __init__(self, zx, zy, nx, ny):
        """
        Setup the operator.

        Args:
          * zx - Index of first x point to extract
          * zy - Index of firsy y point to extract
          * nx - Number of x points to extract
          * ny - Number of y points to extract
          
        """
        self.zx = zx
        self.zy = zy
        self.nx = nx
        self.ny = ny

    def new_field(self, field):
        """
        Create the new cutout field.

        Args:
          * field - the Field object containing the source.
        
        """
        new_field = field.copy()

        new_field.bzx = field.bzx + ((self.zx - 1)*field.bdx)
        new_field.bzy = field.bzy + ((self.zy - 1)*field.bdy)
        new_field.lbnpt = self.nx
        new_field.lbrow = self.ny

        new_field.lbhem = 3

        return new_field

    def transform(self, source_field, result_field):
        """
        Retrieve and cut-out the data from the Field.

        """
        # Get the existing data
        data = source_field.get_data()

        # Create a new data array with the desired output sizes
        cut_data = np.empty((self.ny,self.nx), order="C")

        # If the requested number of points extend beyond the edge
        # of the domain assume the domain is wrapping and handle it
        # by extracting a section of the array from either side of
        # the dividing edge
        if self.zx + self.nx > source_field.lbnpt:
            # The left-most part of the target array is filled using
            # values from right-most part of the source array
            cut_data[:, :source_field.lbnpt - self.zx + 1] = (
                data[self.zy-1:self.zy - 1 + self.ny,
                     self.zx - 1:])
            # And the remainder of the target array is filled using
            # values from the left-most part of the source array
            cut_data[:, source_field.lbnpt - self.zx + 1:] = (
                data[self.zy-1:self.zy-1+self.ny,
                     :self.nx + self.zx - source_field.lbnpt - 1])
        else:
            # If the domain is contained entirely within the domain
            # it can be extracted directly
            cut_data[:,:] = data[self.zy-1:self.zy-1+self.ny,
                                self.zx-1:self.zx-1+self.nx]
        return cut_data

def cutout(ffv_src, filename, cutout_params):

    def check_regular_grid(dx, dy, fail_context, mdi=0.0):
        # Raise error if dx or dy values indicate an 'irregular' grid.
        invalid_values = [0.0, mdi]
        if dx in invalid_values or dy in invalid_values:
            msg = "Source grid in {0} is not regular."
            raise ValueError(msg.format(fail_context))

    # Determine the grid staggering
    stagger = {3: "new_dynamics", 6: "endgame"}
    if ffv_src.fixed_length_header.grid_staggering not in stagger:
        msg = "Grid staggering {0} not supported"
        raise ValueError(msg.format(
            ffv_src.fixed_length_header.grid_staggering))
    stagger = stagger[ffv_src.fixed_length_header.grid_staggering]

    # Remove empty fields before processing
    ffv_src.remove_empty_lookups()

    # Grid-spacing in degrees, ensure this is a regular grid
    rmdi = ffv_src.real_constants.real_mdi
    dx = ffv_src.real_constants.col_spacing
    dy = ffv_src.real_constants.row_spacing
    check_regular_grid(dx, dy, fail_context='header', mdi=rmdi)
    
    # Want to extract the co-ords of the first P point in the file
    if stagger == "new_dynamics":
        # For ND grids this is given directly
        zy0 = ffv_src.real_constants.start_lat
        zx0 = ffv_src.real_constants.start_lon
    elif stagger == "endgame":
        # For EG grids the P grid is offset by half a grid spacing
        zy0 = ffv_src.real_constants.start_lat + 0.5*dy
        zx0 = ffv_src.real_constants.start_lon + 0.5*dx

    # Number of points making up the (P) grid
    nx0 = ffv_src.integer_constants.num_cols
    ny0 = ffv_src.integer_constants.num_rows

    # The arguments to the routine/script giving the start index to cutout
    # and the number of points to cutout, in each direction
    x_index, y_index, nx1, ny1 = cutout_params

    # Ensure the above fit within the target domain (it is allowed to exceed
    # the domain in the X direction provided the domain wraps)
    horiz_grid = ffv_src.fixed_length_header.horiz_grid_type    
    msg = ("The given cutout parameters extend outside the dimensions of the "
           "grid contained in the source file.")
    if y_index + ny1 > ny0 or (x_index + nx1 > nx0
                               and horiz_grid % 10 == 3):
        raise ValueError(msg)

    # Create a new fieldsfile to store the cutout fields
    ffv_dest = ffv_src.copy()

    # Calculate new file headers describing the cutout domain
    if stagger == "new_dynamics":
        # For ND grids this is given directly
        ffv_dest.real_constants.start_lat = zy0 + (y_index - 1)*dy
        ffv_dest.real_constants.start_lon = zx0 + (x_index - 1)*dx
    elif stagger == "endgame":
        # For EG grids the header values are offset by half a grid spacing
        ffv_dest.real_constants.start_lat = zy0 + ((y_index - 1.5) * dy)
        ffv_dest.real_constants.start_lon = zx0 + ((x_index - 1.5) * dx)
        
    # The new grid type will be a LAM, and its size is whatever the size of
    # the specified cutout domain is going to be
    ffv_dest.fixed_length_header.horiz_grid_type = 3
    ffv_dest.integer_constants.num_cols = nx1
    ffv_dest.integer_constants.num_rows = ny1

    # Ready to begin processing of each field
    for i_field, field_src in enumerate(ffv_src.fields):

        # Ensure this field is on a regular grid
        check_regular_grid(field_src.bdx, field_src.bdy,
                           fail_context='field#{0:d}'.format(i_field),
                           mdi=field_src.bmdi)

        # In case the field has extra data, abort
        if field_src.lbext != 0:
            msg = ('field#{0} has extra data, which cutout '
                   'does not support')
            raise ValueError(msg.format(i_field))

        # If the grid is not a regular lat-lon grid, abort
        if field_src.lbcode % 10 != 1:
            msg = ('field#{0} is not on a regular lat/lon grid')
            raise ValueError(msg.format(i_field))

        # Retrieve the grid-type for this field from the STASHmaster and
        # use it to adjust the indices to extract for the non-P grids
        grid_type = STASH[field_src.lbuser4].grid
        if grid_type == 19: # V Points
            if stagger == "new_dynamics":
                # One less row than the P grid
                cut_y = ny1 - 1
                cut_x = nx1
            elif stagger == "endgame":
                # One more row than the P grid
                cut_y = ny1 + 1
                cut_x = nx1
        elif grid_type == 18: # U Points
            if stagger == "new_dynamics":
                # Same as the P grid
                cut_y = ny1
                cut_x = nx1
            elif stagger == "endgame":
                # Same as the P grid
                cut_y = ny1
                cut_x = nx1
        elif grid_type == 11: # UV Points
            if stagger == "new_dynamics":
                # One less row than the P grid
                cut_y = ny1 - 1
                cut_x = nx1
            elif stagger == "endgame":
                # One more row than the P grid
                cut_y = ny1 + 1
                cut_x = nx1
        elif grid_type in [1,2,3]: # P Points
            # Are already correct as defined above
            cut_y = ny1
            cut_x = nx1
        else:
            msg = ('field#{0} has unsupported grid type {1}')
            raise ValueError(msg.format(i_field, grid_type))

        # Can now construct the data operator for the cutout operation and
        # assign it to the field
        cutout_operator = CutoutDataOperator(x_index, y_index, cut_x, cut_y)
        field = cutout_operator(field_src)

        ffv_dest.fields.append(field)

    return ffv_dest

if __name__ == "__main__":
    import sys
    in_file, out_file, x_start, y_start, nx, ny = sys.argv[1:]
    ff = FieldsFile.from_file(in_file)
    ff_new = cutout(ff, out_file, [int(x_start),
                                   int(y_start),
                                   int(nx),
                                   int(ny)])
    ff_new.to_file(out_file)
