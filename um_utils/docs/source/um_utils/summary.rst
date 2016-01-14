Summary (List field lookup headers)
===================================

This utility is used to print out a summary of the lookup headers which describe
the fields from a UM file.  Its intended use is to aid in quick inspections of 
files for diagnostic purposes.  An install of this module will include an
executable wrapper script ``mule-summary`` which provides a command-line
interface to most of Summary's functionality, but it may also be imported and 
used directly inside another Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running 
``mule-summary --help``):

.. code-block:: none

    usage: mule-summary [options] input_file

    SUMMARY - Print a summary of the fields in a UM File (using the Mule API).
    This script will output a summary table of the lookup headers in a UM file,
    with the columns selected by the user.

    optional arguments:
      -h, --help            show this help message and exit

      --column-names --column-names name1[,name2][...]
                            set the names of the lookup header items to print, in
                            the order the columns should appear as a comma
                            separated list. A special entry of "stash_name" will
                            put in the field's name according to the STASHmaster,
                            "index" will give the fields index number, and "t1" or
                            "t2" will give the first and second time from the
                            lookup

      --heading-frequency N
                            repeat the column heading block every N lines (to
                            avoid having to scroll too far to identify columns in
                            the output) A value of 0 means do not repeat the
                            heading block

      --field-index i1[,i2][,i3:i5][...]
                            limit the output to specific fields by index (comma-
                            separated list of single indices, or ranges of indices
                            separated by a single colon-character)

      --field-property key1=value1[,key2=value2][...]
                            limit the output to specific fields using a property
                            string (comma-separated list of key=value pairs where
                            key is the name of a lookup property and value is what
                            it must be set to)

      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a
                            UM version number e.g. '10.2'; if given a number
                            summary will look in the following path:
                            $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A


um_utils.summary API
--------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.summary
   :members:
   :show-inheritance:
