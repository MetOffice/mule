PUMF (Print UM Files)
=====================

This utility is used to print out the various parts of a UM file in a nicely
formatted way.  Its intended use is to aid in quick inspections of files for
diagnostic purposes.  An install of this module will include an executable 
wrapper script ``mule-pumf`` which provides a command-line interface to most
of PUMF's functionality, but it may also be imported and used directly inside
another Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-pumf --help``):

.. code-block:: none

    ==========================================================================
    * PUMF-II - Pretty Printer for UM Files, version II (using the Mule API) *
    ==========================================================================
    usage:
      mule-pumf [-h] [options] input_filename

    This script will output the contents of the headers from a UM file to
    stdout.  The default output may be customised with a variety of options
    (see below).

    optional arguments:
      -h, --help            show this help message and exit
      --include-missing     include header values which are set to MDI and entries for 
                            components which are not present in the file (by default this will 
                            be hidden)

      --use-indices         list headers by their indices (instead of only listing named 
                            headers)

      --headers-only        only list headers (do not read data and calculate any derived 
                            statistics)
      --components component1[,component2][...]
                            limit the header output to specific components 
                            (comma-separated list of component names, with no spaces)

      --field-index i1[,i2][,i3:i5][...]
                            limit the lookup output to specific fields by index 
                            (comma-separated list of single indices, or ranges of indices 
                            separated by a single colon-character)

      --field-property key1=value1[,key2=value2][...]
                            limit the lookup output to specific field using a property 
                            string (comma-separated list of key=value pairs where the key is 
                            the name of a lookup property and the value is the value it must 
                            take)

      --print-columns N     how many columns should be printed

      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a UM 
                            version number e.g. '10.2'; if given a number pumf will look in 
                            the path defined by: 
                              mule.stashmaster.STASHMASTER_PATH_PATTERN 
                            which by default is : 
                              $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A

    possible component names for the component option:
        fixed_length_header, integer_constants, real_constants,
        level_dependent_constants, row_dependent_constants,
        column_dependent_constants, additional_parameters, extra_constants,
        temp_historyfile, compressed_field_index1, compressed_field_index2,
        compressed_field_index3, lookup

    possible lookup names for the field-property option:
        lbyr, lbmon, lbdat, lbhr, lbmin, lbsec, lbyrd, lbmond, lbdatd, lbhrd,
        lbmind, lbsecd, lbtim, lbft, lblrec, lbcode, lbhem, lbrow, lbnpt, lbext,
        lbpack, lbrel, lbfc, lbcfc, lbproc, lbvc, lbrvc, lbexp, lbegin, lbnrec,
        lbproj, lbtyp, lblev, lbrsvd1, lbrsvd2, lbrsvd3, lbrsvd4, lbsrce,
        lbuser1, lbuser2, lbuser3, lbuser4, lbuser5, lbuser6, lbuser7, brsvd1,
        brsvd2, brsvd3, brsvd4, bdatum, bacc, blev, brlev, bhlev, bhrlev, bplat,
        bplon, bgor, bzy, bdy, bzx, bdx, bmdi, bmks, lbday, lbdayd

    for details of how these relate to indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf


um_utils.pumf API
-----------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.pumf
   :members:
   :show-inheritance:
