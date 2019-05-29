Convpp
======

This utility is used to convert between UM Files and PP files.  Unlike some
of the other utilities it isn't really anticipated that this should need to
be called from within another script - if you need to write out fields to 
PP file format from within another script the appropriate routines are all
contained within the `mule.pp` module (see :meth:`fields_to_pp_file`).

Note that one of the options to the utility is to have it output in IBM number
format.  This option is available to support a legacy output mode of the 
original convpp Fortran utility, and should not normally be needed.  However
if you do need to use it you will have to ensure that the optional module
`um_ppibm` has been installed.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-convpp --help``):

.. code-block:: none

    =======================================================================
    * CONVPP-II - Convertor to PP format, version II (using the Mule API) *
    =======================================================================
    usage:
      mule-convpp [-h] [options] input_file output_file
    
    This script will convert a FieldsFile to a PP file.
    
    Note: IBM number format options require that the optional
          um_ppibm module has been built
    
    optional arguments:
      -h, --help             show this help message and exit
      --ibm_format, -I       convert data written to IBM number format
      --keep-addressing, -k  Don't modify address elements LBNREC, LBEGIN and LBUSER(2)
                             (might be required for legacy compatability)


um_utils.convpp API
---------------------
Here is the API documentation (auto-generated) for completeness (although as
stated above, there should be no need to call anything from here separately):

.. automodule:: um_utils.convpp
   :members:
   :show-inheritance:


