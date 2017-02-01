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

    =============================================================================
    * SUMMARY - Print a summary of the fields in a UM File (using the Mule API) *
    =============================================================================
    usage:
      mule-summary [-h] [options] input_file

    This script will output a summary table of the lookup headers in a UM
    file, with the columns selected by the user.

    optional arguments:
      -h, --help            show this help message and exit
      --column-names --column-names name1[,name2][...]
                            set the names of the lookup header items to print, in the 
                            order the columns should appear as a comma separated list. A 
                            special entry of "stash_name" will put in the field's name 
                            according to the STASHmaster, "index" will give the field's 
                            index number in the file, and "t1" or "t2" will give the first 
                            and second time from the lookup (nicely formatted)

      --heading-frequency N
                            repeat the column heading block every N lines (to avoid 
                            having to scroll too far to identify columns in the output) A 
                            value of 0 means do not repeat the heading block

      --field-index i1[,i2][,i3:i5][...]
                            limit the output to specific fields by index (comma-separated 
                            list of single indices, or ranges of indices separated by a single 
                            colon-character)

      --field-property key1=value1[,key2=value2][...]
                            limit the output to specific fields using a property string 
                            (comma-separated list of key=value pairs where key is the name of 
                            a lookup property and value is what it must be set to)

      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a UM 
                            version number e.g. '10.2'; if given a number summary will look in 
                            the path defined by: 
                              mule.stashmaster.STASHMASTER_PATH_PATTERN 
                            which by default is : 
                              $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A

    possible lookup names for the column-names option:
        lbyr, lbmon, lbdat, lbhr, lbmin, lbsec, lbyrd, lbmond, lbdatd, lbhrd,
        lbmind, lbsecd, lbtim, lbft, lblrec, lbcode, lbhem, lbrow, lbnpt, lbext,
        lbpack, lbrel, lbfc, lbcfc, lbproc, lbvc, lbrvc, lbexp, lbegin, lbnrec,
        lbproj, lbtyp, lblev, lbrsvd1, lbrsvd2, lbrsvd3, lbrsvd4, lbsrce,
        lbuser1, lbuser2, lbuser3, lbuser4, lbuser5, lbuser6, lbuser7, brsvd1,
        brsvd2, brsvd3, brsvd4, bdatum, bacc, blev, brlev, bhlev, bhrlev, bplat,
        bplon, bgor, bzy, bdy, bzx, bdx, bmdi, bmks, lbday, lbdayd

    for details of how these relate to indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf


um_utils.summary API
--------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.summary
   :members:
   :show-inheritance:
