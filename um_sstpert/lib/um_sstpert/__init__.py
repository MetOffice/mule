# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the UM sstpert library extension module for Mule.
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
SSTPERT is a utility for producing SST perturbation files.

Usage:

 * Produce an SST perturbation field from 12 climatology fields, an alpha
   factor, date and ensemble member:

    >>> pert_field = mule_sstpert.gen_pert_field(
                                        clim_fields, alpha, ens_member, date)

 * As above, but start from a file object containing the climatology and
   return a file object containing the perturbed field:

    >>> pert_fil = mule_sstpert.gen_pert_file(
                                         clim_file, alpha, ens_member, date)

"""
import os
import sys
import argparse
import textwrap
import numpy as np

from datetime import datetime

import mule
from .um_sstpert import sstpert, sstpertseed
from um_utils.version import report_modules
from um_utils.pumf import _banner

__version__ = "2020.01.1"


def gen_pert_field(clim_fields, alpha, ens_member, date):
    """
    Generate an SST perturbation field from a set of climatological
    fields and some values to setup a random number generator.

    Args:
        * clim_fields:
            Array of 12 field objects giving the SST (lbuser4=24)
            for each month of the year.
        * alpha:
            Factor used by algorithm (higher values lead to more extreme
            perturbations).
        * ens_member:
            Ensemble member number - used in random generator.
        * date:
            Datetime object giving the desired date for the perturbed field.

    Returns:
        * pert_field:
            A new field object based on the first climatology field but with
            its data replaced by the new perturbed SST field.

    """
    # Climatology should be a list of 12 field object giving the SSTs
    if len(clim_fields) != 12:
        msg = (
            "Incorrect number of climatology fields; expected 12, found {0}")
        raise ValueError(msg.format(len(clim_fields)))

    # Check that the fields are appropriate releases and are SSTs
    for ifld, field in enumerate(clim_fields):
        if field.lbrel not in (2, 3):
            msg = "Climatology field {0} has invalid header release number"
            raise ValueError(msg.format(ifld+1))
        if field.lbuser4 != 24:
            msg = "Climatology field {0} is not an SST field"
            raise ValueError(msg.format(ifld+1))

    # Sort them into month order if they aren't already
    def month_sort(field):
        return field.lbmon
    clim_fields = sorted(clim_fields, key=month_sort)

    # The SST pert library requires the data from the fields as a big array,
    # so create it here:
    clim_array = np.empty((clim_fields[0].lbrow,
                           clim_fields[0].lbnpt,
                           12))
    for ifield, field in enumerate(clim_fields):
        clim_array[:, :, ifield] = field.get_data()

    # The library also requires some of the other arguments be packed into an
    # array similar to the UM's "dt" array:
    dt = np.array([date.year,
                   date.month,
                   date.day,
                   0,              # This element is a UTC offset and always 0
                   date.hour + 1,  # Add 1 here because fieldcalc did it
                   date.minute,
                   ens_member,
                   ens_member + 100],
                   dtype=np.int64)

    # Call the library
    pert_data = sstpert(alpha, dt, clim_array)

    # Create a copy of the first field to store the new output
    pert_field = clim_fields[0].copy()
    pert_field.set_data_provider(mule.ArrayDataProvider(pert_data))

    # Set the field headers from the given date
    pert_field.lbyr = pert_field.lbyrd = date.year
    pert_field.lbmon = pert_field.lbmond = date.month
    pert_field.lbdat = pert_field.lbdatd = date.day
    pert_field.lbhr = pert_field.lbhrd = date.hour
    pert_field.lbmin = pert_field.lbmind = date.minute
    pert_field.raw[6] = pert_field.raw[12] = 0

    pert_field.lbft = 0
    pert_field.lbpack = 0

    return pert_field


def gen_seed(ens_member, date):
    """
    Generate a seed

    Args:
        * date:
            Datetime object giving the desired date for the perturbed field.

    Returns:
        * seed:
            A seed value.

    """

    # The library also requires some of the other arguments be packed into an
    # array similar to the UM's "dt" array:
    dt = np.array([date.year,
                   date.month,
                   date.day,
                   0,              # This element is a UTC offset and always 0
                   date.hour + 1,  # Add 1 here because fieldcalc did it
                   date.minute,
                   ens_member,
                   ens_member + 100],
                   dtype=np.int64)

    # Call the library
    seed = sstpertseed(dt)
    return seed


def gen_pert_file(umf_clim, alpha, ens_member, date):
    """
    Generate an SST perturbation file from an input file containing a
    set of climatological fields and some values to setup a random
    number generator.

    Args:
        * umf_clim:
            A :class:`mule.UMFile` object containing the 12 field objects
            giving the SST (lbuser4=24) for each month of the year.
        * alpha:
            Factor used by algorithm (higher values lead to more extreme
            perturbations).
        * ens_member:
            Ensemble member number - used in random generator.
        * date:
            Datetime object giving the desired date for the perturbed field.

    Returns:
        * umf_pert:
            A :class:`mule.FieldsFile` object containing the perturbed
            SST field.

    """

    # Generate the perturbations; assume that the first 12 fields
    # in the file are the SST fields
    pert_field = gen_pert_field(
        umf_clim.fields[:12], alpha, ens_member, date)

    # Create a FieldsFile object for the output file
    ff = mule.FieldsFile()

    # Copy the fixed length header from the input, changing the type
    # to match a FieldsFile
    ff.fixed_length_header = umf_clim.fixed_length_header
    ff.fixed_length_header.dataset_type = 3

    # Populate the time entries from the date given
    now = datetime.now()
    ff.fixed_length_header.t1_year = date.year
    ff.fixed_length_header.t2_year = date.year
    ff.fixed_length_header.t3_year = now.year
    ff.fixed_length_header.t1_month = date.month
    ff.fixed_length_header.t2_month = date.month
    ff.fixed_length_header.t3_month = now.month
    ff.fixed_length_header.t1_day = date.day
    ff.fixed_length_header.t2_day = date.day
    ff.fixed_length_header.t3_day = now.day
    ff.fixed_length_header.t1_hour = date.hour
    ff.fixed_length_header.t2_hour = date.hour
    ff.fixed_length_header.t3_hour = now.hour
    ff.fixed_length_header.t1_minute = date.minute
    ff.fixed_length_header.t2_minute = date.minute
    ff.fixed_length_header.t3_minute = now.minute
    ff.fixed_length_header.t1_second = date.second
    ff.fixed_length_header.t2_second = date.second
    ff.fixed_length_header.t3_second = now.second

    # Copy the integer headers that are populated
    ff.integer_constants = mule.ff.FF_IntegerConstants.empty()
    ff.integer_constants.raw[:len(umf_clim.integer_constants.raw)] = (
        umf_clim.integer_constants.raw)

    # Copy the real headers that are populated
    ff.real_constants = mule.ff.FF_RealConstants.empty()
    ff.real_constants.raw[:len(umf_clim.real_constants.raw)] = (
        umf_clim.real_constants.raw)

    # We can't be sure that the input file's grid was setup sensibly, so
    # assume that the copied field header is right and setup the file
    # headers from that
    ff.fixed_length_header.grid_staggering = 6
    ff.real_constants.start_lat = pert_field.bzy + 0.5*pert_field.bdy
    ff.real_constants.start_lon = pert_field.bzx + 0.5*pert_field.bdx

    # The ancil is likely missing the level dependent constants, so
    # put some in which are the minimum size for a FieldsFile
    if umf_clim.level_dependent_constants is None:
        ff.integer_constants.num_p_levels = 1
        ff.level_dependent_constants = (
            mule.ff.FF_LevelDependentConstants.empty(2))

    # Copy the row/column headers if they were set
    if (umf_clim.row_dependent_constants is not None and
            umf_clim.column_dependent_constants is not None):
        ff.row_dependent_constants = umf_clim.row_dependent_constants
        ff.column_dependent_constants = umf_clim.column_dependent_constants

    # Add the perturbation field and output
    ff.fields = [pert_field]

    return ff


def _main():
    """
    Main function; accepts command line arguments and calls routines

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [--date-fmt DATE_FMT]
                    input_file alpha date ens_member output_file

    This script will use 12 months of climatology data, plus a target date
    for the perturbed field and  produce the perturbation in a new file.
    """
    title = _banner(
        "SSTPERT - Produce SST Perturbations (using the Mule API)",
        banner_char="=")

    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    # No need to output help text for the input file (it's obvious)
    parser.add_argument("input_file",
                        help="path to input file containing climatology")
    parser.add_argument("alpha",
                        help="intensity factor for perturbations")
    parser.add_argument("date",
                        help="desired date for perturbations")
    parser.add_argument("--date-fmt",
                        help="format string for date to be passed to "
                        "datetime.strptime - \nsyntax the same as Unix date "
                        "(default is %%Y%%m%%d%%H%%M)",
                        default="%Y%m%d%H%M")
    parser.add_argument("ens_member",
                        help="ensemble member number, used in generation "
                        "of random seed")
    parser.add_argument("output_file",
                        help="path to output file for perturbation")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) < 5:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(SSTPERT) Module Information")),
    report_modules()
    print("")

    # Get the date information using the format if provided
    date = datetime.strptime(args.date, args.date_fmt)

    # Check for valid alpha
    try:
        alpha = float(args.alpha)
    except ValueError:
        msg = "Value for alpha factor not a valid float"
        raise ValueError(msg)

    if args.ens_member.isdigit():
        ens_member = int(args.ens_member)
    else:
        msg = "Value for ensemble member is not a valid integer"
        raise ValueError(msg)

    # Get the filename and load it using Mule
    filename = args.input_file
    if os.path.exists(filename):
        # Load the file (should be an ancil)
        um_file = mule.AncilFile.from_file(filename)
        # Generate the new file
        ff = gen_pert_file(um_file, alpha, ens_member, date)
        # Write it out
        ff.to_file(args.output_file)
    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)

if __name__ == "__main__":
    _main()
