Edit-mask (Utility for manual editing of land/sea mask)
=======================================================

This utility is used to enable the manual editing of a land/sea mask from
a UM ancil file.  Rather than designing a full GUI utility the intention is
that the tool allows the land/sea mask data to be exported as an image file
and edited externally using a program of the users choice.  Once edited the
image file may be ingested back into a new UM ancil file.

For the image editing, one has to be careful about how the file is saved to
ensure it is still compatible with the format expected by PIL (Python Imaging
Library).  It has been tested using the free utility GIMP
(GNU Image Manipulation Program).  After loading the file make careful edits
using only "hard edged" tools (i.e. pixel brush drawing tools) so as to ensure
the image remains purely black & white.  Use the save option to "overwrite" the
original file for best results as it will avoid altering the format too much.


Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-editmask --help``):

.. code-block:: none

    ==========================================================================
    * EDIT MASK - Editor for Land Sea Masks in UM Files (using the Mule API) *
    ==========================================================================
    usage:
      mule-editmask [-h] {genimage,genancil} [options]

    Description

    positional arguments:
      {genimage,genancil}
        genimage           generate image file (run "mule-editmask genimage --help"
                           for specific help on this command)

        genancil           generate ancil file (run "mule-editmask genancil --help"
                           for specific help on this command)

    optional arguments:
      -h, --help           show this help message and exit

Note that as shown above the command has two modes of operation - ``genimage``
and ``genancil``, with each requiring different arguments.  Here are the help
texts for these two modes:

(from ``mule-editmask genimage --help``):

.. code-block:: none

    ==========================================================================
    * EDIT MASK - Editor for Land Sea Masks in UM Files (using the Mule API) *
    ==========================================================================
    usage:
      mule-editmask genimage [-h] ancil_file image_file

    This will generate an image file which represents the contents
    of the mask from the input file (ready for editing)

    positional arguments:
      ancil_file  UM Ancillary File containing source mask

      image_file  Filename for output image (.png will be appended)


    optional arguments:
      -h, --help  show this help message and exit


(from ``mule-editmask genancil --help``):

.. code-block:: none

    ==========================================================================
    * EDIT MASK - Editor for Land Sea Masks in UM Files (using the Mule API) *
    ==========================================================================
    usage:
      mule-editmask genancil [-h]
               [--text-file text_file] ancil_file mask_file output_file

    This will create a copy of the original file but with the data
    from the mask image inserted into the mask field

    positional arguments:
      ancil_file            UM Ancillary File containing original mask

      mask_file             Filename of edited mask, either:
                                A png image produced by 'genimage'
                                and edited externally
                             OR
                                A txt file produced by a previous
                                invocation of 'genancil' (see text_file)
      output_file           Filename for Ancillary File with new mask data

    optional arguments:
      -h, --help            show this help message and exit
      --text-file TEXT_FILE
                            Filename for text file which will contain a list
                            of the changed points, and can be used as the
                            'mask_file' argument in future calls if needed

um_utils.editmask API
---------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.editmask
   :members:
   :show-inheritance:
