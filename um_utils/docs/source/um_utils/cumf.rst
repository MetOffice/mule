CUMF (Compare UM Files)
=======================

This utility is used to compare two UM files and report on any differences
found in either the headers or field data.  Its intended use is to test
results from different UM runs against each other to investigate possible
changes.  An install of this module will include an executable wrapper script
``mule-cumf`` which provides a command-line interface to most of CUMF's
functionality, but it may also be imported and used directly inside another
Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-cumf --help``):

.. code-block:: none

    ===========================================================================
    * CUMF-II - Comparison tool for UM Files, version II (using the Mule API) *
    ===========================================================================
    usage:
      mule-cumf [-h] [options] file_1 file_2

    This script will compare all headers and data from two UM files,
    and write a report describing any differences to stdout.  The
    assumptions made by the comparison may be customised with a
    variety of options (see below).

    optional arguments:
      -h, --help            show this help message and exit
      --ignore component_name=index1[,index2][...]
                            ignore specific indices of a component; provide the name of
                            the component and a comma separated list of indices or ranges
                            (i.e. M:N) to ignore.  This may be specified multiple times to
                            ignore indices from more than one component

      --ignore-missing      if present, positional headers will be ignored (required if
                            missing fields from either file should not be considered a failure
                            to compare)

      --diff-file filename  a filename to write a new UM file to which contains the
                            absolute differences for any fields that differ

      --full                if not using summary output, will increase the verbosity by
                            reporting on all comparisons (default behaviour is to only report
                            on failures)

      --summary             print a much shorter report which summarises the differences
                            between the files without going into much detail

      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a UM
                            version number e.g. '10.2'; if given a number cumf will look in
                            the path defined by:
                              mule.stashmaster.STASHMASTER_PATH_PATTERN
                            which by default is :
                              $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A
      --show-missing [=N]   display missing fields from either file. If given, N is the
                             maximum number of fields to display.

    possible component names for the ignore option:
        fixed_length_header, integer_constants, real_constants,
        level_dependent_constants, row_dependent_constants,
        column_dependent_constants, additional_parameters, extra_constants,
        temp_historyfile, compressed_field_index1, compressed_field_index2,
        compressed_field_index3, lookup

    for details of the indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf


um_utils.cumf API
-----------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.cumf
   :members:
   :special-members: __init__
   :show-inheritance:
