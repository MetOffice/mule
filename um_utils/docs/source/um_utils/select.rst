Select (Copy selected fields)
===================================

This is a utility to extract a selection of fields of an UM file.
 
Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``/mule-select --help``):

.. code-block:: none

    ===================================================================
    * SELECT - Field filtering tool for UM files (using the Mule API) *
    ===================================================================
    usage:
      mule-select input_filename [input_filename2 [input_filename3]] 
                                  output_filename [filter arguments]

    This script will select or exclude fields from one or more UM file based
    on the values set in the lookup headers of each field.

    optional arguments:
      -h, --help            show this help message and exit

    filter arguments:
      --include name=val1[,val2] [name=val1[,val2] ...]
                            specify lookup headers to include, the names should
                            correspond to lookup entry names and the values to the
                            desired values which must match

      --exclude name=val1[,val2] [name=val1[,val2] ...]
                            specify lookup headers to exclude, the names should
                            correspond to lookup entry names and the values to the
                            desired values which must not match

      --or                  specify the separation of two criteria sections that
                            should be "or"d together; this is a positional argument

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


um_utils.summary API
--------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.select
   :members:
   :show-inheritance:
