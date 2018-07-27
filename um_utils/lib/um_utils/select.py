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

"""
SELECT is a utility to extract a selection of fields of an UM file.

It is primarily intended to be a command-line tool, since filtering of
fields is straightforward enough to do directly when already within a
Python script.  That being said, should you wish to call it from another
script the usage is as follows:

 * Selecting a set of fields:

   >>> fields = select.select(umfile_object, include=include, exclude=exclude)

Where include and exclude are each dictionaries; the keys are the names of
lookup entries as they appear in Mule, the values are lists of the lookup
values to be matched (or excluded).

The return value is a list of fields which match the criteria.  When used
via the command line an "or" operation can be specified; this is equivalent
to running each "or"d request through the above function separately and then
combining the results.

..Note ::
    As an "and" type operation, a selection which both tags a field for
    inclusion and for exclusion will result in the field being excluded.

"""

import os
import sys
import mule
import mule.pp
import argparse
import textwrap
from um_utils.pumf import _banner
from um_utils.version import report_modules


def select(umf, include=None, exclude=None):
    """
    Given a UM file object and some filtering dictionaries, return a list of
    qualifying fields.

    Args:
        * umf:
            A :class:`mule.UMFile` object.

    Kwargs:
        * include:
            A dictionary defining lookup header combinations which should be
            included in the output; keys are the lookup names as defined by
            Mule, values are lists of the values to match.
        * exclude:
            A dictionary defining lookup header combinations which should be
            excluded from the output; keys are the lookup names as defined by
            Mule, values are lists of the values to exclude.

    """
    fields_out = [f for f in umf.fields]
    if include is not None:
        for field in list(fields_out):
            # Process includes first... the field has to meet all of the
            # criteria not to be removed, so as soon as it fails one criteria
            # remove it
            for header, vals in include.items():
                if getattr(field, header, None) not in vals:
                    fields_out.remove(field)
                    break

    if exclude is not None:
        for field in list(fields_out):
            # After processing includes, process excludes on the result,
            # since the two are to be "and"ed together anyway.  This time
            # however a field must fail to satisfy all of the conditions
            check = []
            for header, vals in exclude.items():
                if getattr(field, header, None) in vals:
                    check.append(True)
            if len(check) > 0 and all(check):
                fields_out.remove(field)

    return fields_out


def _main():
    """
    Main function; accepts command line arguments and implements or logic by
    calling the select function multiple times.
    """

    help_prolog = """    usage:
      %(prog)s input_filename [input_filename2 [input_filename3]] \
                                            output_filename [filter arguments]

    This script will select or exclude fields from one or more UM file based
    on the values set in the lookup headers of each field.
    """
    title = _banner(
        "SELECT - Field filtering tool for UM files "
        "(using the Mule API)", banner_char="=")

    help_epilog = """
    examples:
      Select U and V wind components (lbfc 56 57) at model level 1
      mule-select ifile ofile --include lbfc=56,57 lblev=1

      Select U and V wind components (lbfc 56 57) at model level 1 from
      two input files
      mule-select ifile1 ifile2 ofile --include lbfc=56,57 lblev=1

      Select pressure (lbfc  8) but not at surface (lblev 9999)
      mule-select ifile ofile --include lbfc=8 --exclude blev=9999

      Select all fields which match U wind at model level 2 or
      fields which are at model level 1
      mule-select ifile ofile --include lblev=2 lbfc=56 --or --include lblev=1

    often used codes:
      lbfc    field code
      lbft    forecast period in hours
      lblev   fieldsfile level code
      lbuser4 stash section and item number (section x 1000 + item)
      lbproc  processing code
      lbpack  packing method
      lbvc    vertical co-ordinate type
      lbyr    year (validity time / start of processing period)
      lbmon   month (validity time / start of processing period)
      lbdat   day (validity time / start of processing period)
      lbhr    hour (validity time / start of processing period)
      lbmin   minute (validity time / start of processing period)
      lbsec   second (validity time / start of processing period)

    for other codes please see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf
    """

    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent(help_epilog))

    pg = parser.add_argument_group('filter arguments')

    pg.add_argument(
        "--include", nargs="+",
        metavar="name=val1[,val2]",
        help="specify lookup headers to include, the names should \n"
        "correspond to lookup entry names and the values to the \n"
        "desired values which must match \n ")
    pg.add_argument(
        "--exclude", nargs="+",
        metavar="name=val1[,val2]",
        help="specify lookup headers to exclude, the names should \n"
        "correspond to lookup entry names and the values to the \n"
        "desired values which must not match \n ")
    pg.add_argument(
        "--or", metavar="",
        help="specify the separation of two criteria sections that \n"
        "should be \"or\"d together; this is a positional argument")

    # There should be at least 4 arguments (i.e. the two filename plus one
    # include/exclude flag and a value for it)
    if len(sys.argv) < 4:
        parser.print_help()
        parser.exit(1)

    # Print version information
    print(_banner("(SELECT) Module Information")),
    report_modules()
    print("")

    # The files must be the first arguments, with the output file being
    # the last one  Note that we don't include these in the parser
    # explicitly, because the way we wish to call the parser below is a
    # little odd (once per --or to separate the cases) and including
    # the files would interfere with this

    input_files = []
    while len(sys.argv) > 3:
        # Once the argument 2 positions ahead is a flag, exit
        if sys.argv[2].startswith("--"):
            break
        # Otherwise gather the input files up
        input_files.append(sys.argv.pop(1))

    output_file = sys.argv.pop(1)

    for input_file in input_files:
        if not os.path.isfile(input_file):
            msg = "File not found: " + input_file
            raise ValueError(msg)

    # Pickup the "--or" argument, splitting the arguments up and then pass them
    # through to the parser as if they were separate arguments
    cases = " ".join(sys.argv[1:]).split("--or")
    arglist = [parser.parse_args(case.split()) for case in cases]

    # Make a list of possible keys; use the combination of options from both
    # release types, to cover all bases
    valid_keys = [name for name, _ in mule._LOOKUP_HEADER_3]
    valid_keys += [name for name, _ in mule._LOOKUP_HEADER_2
                   if name not in valid_keys]

    # Now split the result into a list of nested dictionaries - these consist
    # of two top-level keys - include/exclude - and within these the keys
    # correspond to lookup names and values
    case_dicts = []
    for args in arglist:
        entry = {}
        for inc_exc in ["include", "exclude"]:
            attribute = getattr(args, inc_exc, None)
            if attribute is None:
                continue
            entry[inc_exc] = dict([vals.split("=") for vals in attribute])
            for key in entry[inc_exc].keys():
                if key not in valid_keys:
                    msg = "Encountered unrecognised lookup name: {0}"
                    raise ValueError(msg.format(key))
                new_vals = []
                for val in entry[inc_exc][key].split(","):
                    if key.startswith("lb"):
                        new_vals.append(int(val))
                    else:
                        new_vals.append(float(val))
                entry[inc_exc][key] = new_vals
        if entry:
            case_dicts.append(entry)

    # Load the input files
    selected_fields = []
    pp_mode = False
    for ifile, input_file in enumerate(input_files):
        # Check if this is a pp file
        if mule.pp.file_is_pp_file(input_file):
            pp_mode = True
            umf = mule.FieldsFile()
            umf.fields = mule.pp.fields_from_pp_file(input_file)
            umf._source_path = input_file
        elif not pp_mode:
            umf = mule.load_umfile(input_file)
        else:
            msg = "Cannot mix and match UM files and pp files"
            raise ValueError(msg)

        # Iterate through the cases - each returns a list of matching fields
        for case in case_dicts:
            selected_fields += (
                select(umf,
                       include=case.get("include", None),
                       exclude=case.get("exclude", None)))

        # Copy first file to use for writing output
        if ifile == 0 and not pp_mode:
            umf_out = umf.copy()

    # Prune out duplicates while preserving their order
    dupes = set()
    unique_fields = [
        x for x in selected_fields if not (x in dupes or dupes.add(x))]

    # Attach the new set of fields to the first original file object
    # and write it back out, or write out a pp file
    if pp_mode:
        mule.pp.fields_to_pp_file(output_file, unique_fields)
    else:
        umf_out.fields = unique_fields
        umf_out.to_file(output_file)


if __name__ == "__main__":
    _main()
