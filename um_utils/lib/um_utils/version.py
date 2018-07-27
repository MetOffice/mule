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
VERSION - Check which version of the various modules are in use.

Usage:

 * Print the version information to stdout:

   >>> version.report_modules()

 * The version information can also be returned to any writeable object

   >>> with open("version_file", "w") as fobj:
   ...     version.report_modules(fobj)

"""
import sys
import argparse
import textwrap
import mule
import um_utils


def _print_module_source(module):
    """
    Given a module object print a formatted message indicating the file
    which contains it.

    """
    report = "{0:10s} : {1} (version {2})"
    return report.format(module.__name__, module.__file__, module.__version__)


def report_modules(stdout=None):
    """
    Print version information for the mule and um_utils modules, and then
    whatever packing library module is currently available to mule.

    Kwargs:
        * stdout:
            If provided, an alternative writeable object to send the
            output text to (default is to use sys.stdout)

    """
    if stdout is None:
        stdout = sys.stdout

    # Report the location of mule and the utilities module
    stdout.write(_print_module_source(mule) + "\n")
    stdout.write(_print_module_source(um_utils) + "\n")

    # The packing module is more variable, so report on whatever
    # the copy of mule above has ended up importing
    if hasattr(mule.packing, "um_packing"):
        stdout.write(_print_module_source(mule.packing.um_packing))
        stdout.write(" (packing lib from SHUMlib: {0})\n".format(
            mule.packing.um_packing.get_shumlib_version()))
    elif hasattr(mule.packing, "mo_pack"):
        stdout.write(_print_module_source(mule.packing.mo_pack))
    else:
        stdout.write("No Packing Library Available")
    stdout.write("\n")


def _main():
    """
    Main function; provides help text for consistency (has no options though)

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h]
    """
    title = """
====================================================================
* VERSION - Check which version of mule related modules are in use *
====================================================================
"""
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )
    args = parser.parse_args()
    report_modules()


if __name__ == "__main__":
    _main()
