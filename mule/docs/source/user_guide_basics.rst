The Basics
==========
This part of the tutorial focuses on the key elements you will be working with
when using the API; to prepare for the later examples.

Opening files
-------------
First of all we will need a file to work with - to make this easier you 
can borrow one of the testing files that comes with the API.  To locate 
these files run the following code snippet:

.. code-block:: python

    >>> import os
    >>> import mule.tests
    >>> import glob
    >>> testdata_path = mule.tests.TESTDATA_DIRPATH
    >>> test_pattern = os.path.join(testdata_path, "*")
    >>> test_files = sorted(glob.glob(test_pattern))
    >>> print("\n".join([os.path.basename(f) for f in test_files]))
    
.. Note::
    
    This is just returning and printing all of the example file paths as a 
    python list you can then access specific full paths from the list by 
    passing one of the filenames printed above to the 
    :meth:`mule.tests.testdata_filepath` method.

Mule supports different UM file types using a series of classes; when 
writing scripts you should generally select a class that corresponds to
the specific type of file you aim to support.  Currently there are four 
available classes:

  * :class:`mule.FieldsFile`
  * :class:`mule.DumpFile`
  * :class:`mule.LBCFile`
  * :class:`mule.AncilFile`

Pick one of the classes and a file which it should correspond to (the test
files have either ".ff", ".dump", ".lbc" or ".anc" extensions that should 
indicate this).  You can then create a new class instance based on the file 
like so:

.. code-block:: python

    >>> import mule
    >>> test_ff_path = mule.tests.testdata_filepath("n48_eg_regular_sample.ff")
    >>> ff = mule.FieldsFile.from_file(test_ff_path)

This will load a file from the list of test files (a fields-file) using
the :class:`mule.FieldsFile` class.  You should find you can load a Dump using
the :class:`mule.DumpFile` class, an LBC file using the :class:`mule.LBCFile` 
class, or an Ancillary file using the :class:`mule.AncilFile` class in the 
same way (the filetypes are indicated by the extension of the test filenames).

.. Note::
    
    You might also notice that if you try to load a fields-file with any of 
    the classes other than the :class:`mule.FieldsFile` class (or similarly 
    for the other classes) it will not work; the classes can detect if the file 
    they are given appears to be the correct type - based on information from 
    the  headers (more on this later).  You will also find you *cannot* load
    a "pp" file with any of the classes (again more on this later).

Alternatively, there is a convenience method which will allow you to attempt
to load a file when you aren't sure of the type (or more likely - where you
are writing a script which can accept *any* type of UM file).  The method
will return whichever type appears to be correct:

.. code-block:: python

    >>> test_file = mule.tests.testdata_filepath("eg_boundary_sample.lbc")
    >>> umf = mule.load_umfile(test_file)
    >>> type(umf)
    <class 'mule.lbc.LBCFile'>
    >>> test_file = mule.tests.testdata_filepath("n48_eg_dump_special.dump")
    >>> umf = mule.load_umfile(test_file)
    >>> type(umf)
    <class 'mule.dump.DumpFile'>

.. Warning::

    It is *not* considered good practice to use this method when your code 
    is actually designed to target a specific file type. Since the specific
    sub-classes are **not identical**, you have to be very careful about 
    what properties you make use of.
    

Header Components
-----------------
You should now be able to create a file object from a UM file, so now let's 
examine the structure of these objects.  

.. Note::

    At this point it might be very useful (depending on how familiar
    you are with UM file formats) to ensure you have a copy of the 
    UM Documentation Paper F03 to hand.

The objects are designed to represent the layout of the files themselves 
very closely.  Load the "ff" object from the example above again and take
a look at your first *header component* - the "fixed length header" (which
is common to all UM files):

.. code-block:: python

    >>> ff.fixed_length_header
    <mule.FixedLengthHeader object at 0x22f7d50>

Many of the parts of the file header are represented in similar classes to
this one, and they provide two different methods to access the data in the 
header.  Many properties can be accessed as named attributes - typically 
these will be those where UMDP F03 provides an obvious name and use for the 
property.  For example the fixed length header contains entries which 
describe the type of file, and the grid staggering:

.. code-block:: python

    >>> ff.fixed_length_header.dataset_type
    3
    >>> ff.fixed_length_header.grid_staggering
    9

All of the header properties can also be accessed directly via their indices, 
which provides a method to access "unknown" properties.  For example to access
the same two properties by index:

.. code-block:: python

    >>> ff.fixed_length_header.raw[5]
    3
    >>> ff.fixed_length_header.raw[9]
    9

.. Note::

    The "raw" method of accessing the header directly applies a hidden offset
    to the indices so that they correspond exactly to the (1-based) indices
    in UMDP F03.  This is to avoid confusion when referring to the document.
    If you inspect the zero-th element you will see it is set to "None" and
    will always be ignored.

Each header component behaves in a similar way; you can refer to UMDP F03 for 
details of all possible components, but here are a few examples:

.. code-block:: python

    >>> ff.integer_constants.num_rows, ff.integer_constants.num_cols
    (72, 96)
    >>> ff.real_constants.real_mdi
    -1073741824.0
    >>> ff.level_dependent_constants.eta_at_theta
    array([0.0, 0.00025, 0.0006667, 0.00125, 0.002, 0.0029167, 0.004, 0.00525,
           ...
           0.6707432, 0.73825, 0.8148403, 0.9016668, 1.0], dtype=object)
    >>> ff.column_dependent_constants
    

Notice that some components may be 2-dimensional (with a named attribute
returning a slice - as in the level dependent constants), and that sometimes
a component can be missing (here the row and column dependent constants are
both missing and set to "None").  To obtain a listing of the possible 
components in the file object, you may inspect the "COMPONENTS" attribute:

.. code-block:: python

    >>> for name, _ in ff.COMPONENTS: print(name)
    ... 
    integer_constants
    real_constants
    level_dependent_constants
    row_dependent_constants
    column_dependent_constants
    fields_of_constants
    extra_constants
    temp_historyfile
    compressed_field_index1
    compressed_field_index2
    compressed_field_index3

Spend some time examining these components in the file object to see what
is available.  You should find that named attributes exist for everything
mentioned in UMDP F03.

Field Objects
-------------
Moving on to the fields which are stored in the file; a UM field consists 
of a lookup-header entry which provides metadata for the field as well as a 
description of where to find the data and how to extract it.  This is all
encapsulated in a series of :class:`mule.Field` objects - one for each field,
and these can be found in the "fields" attribute of the file object:

.. code-block:: python

    >>> ff.fields
    [<mule.Field3 object at 0x2d53050>, <mule.Field3 object at 0x2d3bfd0>, <mule.Field3 object at 0x2d53110>, <mule.Field3 object at 0x2d531d0>, <mule.Field3 object at 0x2d53290>, <mule.Field3 object at 0x2d53350>, <mule.Field3 object at 0x2d53410>, <mule.Field3 object at 0x2d534d0>, <mule.Field3 object at 0x2d53590>, <mule.Field3 object at 0x2d53650>]

Firstly, the lookup header - this behaves fairly similarly to the other
header components, and it contains both the integer and real properties in a
single object.  Accessing these works in the same way as the other header
components - let's take the first field in the file as an example (note that
unlike the raw header arrays the field list starts from **zero** as per 
Python's normal rules):

.. code-block:: python

    >>> field = ff.fields[0]
    >>> field.lbuser4, field.lbft, field.lblev, field.bdy, field.bdx
    (30, 0, 9999, 3.75, 2.5)
    >>> field.raw[42], field.raw[14] ,field.raw[33], field.raw[60], field.raw[62]
    (30, 0, 9999, 3.75, 2.5)

Bonus points if you know what this field is without looking up its STASH code!

.. Note::

    When accessing the "raw" values in the lookup array by index, notice
    that the indices do not "reset" at the point where the real values
    begin; this means the indices are *exactly* what UMDP F03 says for all
    components in the lookup header.

The other part of a UM field is the data itself, but you won't be able to find
a property which contains it.  Unlike the components the API does *not* read in
any of the data when you load the file.  Instead, it uses the information in the 
lookup headers to generate a method for each field that will allow it to access 
that field's data.  Let's tell this field to go and get its data:

.. code-block:: python

    >>> data = field.get_data()
    >>> data
    array([[1, 1, 1, ..., 1, 1, 1],
           [1, 1, 1, ..., 1, 1, 1],
           [1, 1, 1, ..., 1, 1, 1],
           ..., 
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]])

As you can see the data has been returned as a 2-d numpy array.  If you want
(and have matplotlib installed) you can visualise the data quickly like this:

.. code-block:: python

    >>> import matplotlib.pyplot as plt
    >>> plt.pcolormesh(data)
    <matplotlib.collections.QuadMesh object at 0x2e8f0d0>
    >>> plt.axis("tight")
    (0.0, 96.0, 0.0, 72.0)
    >>> plt.colorbar()
    >>> plt.show()

Take some time now to explore the field objects from the file, and the file
as a whole - you have now seen all of the key elements that will allow you 
to examine the contents of a file and its fields.

Manipulation and Writing Out
----------------------------
To conclude this section we'll perform a few basic manipulations of the file
object and write it out to a new file.  Let's assume we only want to output 
the first field (which we examined above); we can do this by replacing the
list of fields with a list containing only the first field:

.. code-block:: python

    >>> ff.fields = [ff.fields[0]]

If we want to adjust any headers we can just set the attributes, for instance
we could change the grid staggering and give the field a different (and invalid)
STASH code (for testing purposes!):

.. code-block:: python

    >>> ff.fields[0].lbuser4 = 99999
    >>> ff.fixed_length_header.grid_staggering = 3

.. Warning::

    Clearly this is just an example and in a lot of cases you should not be
    doing operations like this without good reason.  A lot of the time header
    values will have inter-dependencies and cannot simply be changed without
    the file becoming invalid.  The API will check for very obvious errors in
    when you try to write the file but it cannot guarantee that the file is 
    completely correct - that is up to you.

We can now write out the file, providing a suitable filename (in this case a
file in your home directory - amend as necessary):

.. code-block:: python

    >>> ff.to_file(os.path.expanduser("~/mule_example.ff"))

If you inspect the file produced using a different tool (or re-open it with
the API) you should find your changes are intact.  In a moment you should 
experiment with this process, but before you do there is a helpful feature
worth mentioning.

Copying File Objects
....................
When following the steps above you might have found yourself having to 
"refresh" the file object by re-loading the original file again if you made 
any mistakes manipulating the object.  In many cases it may be preferable 
to keep an un-modified copy of the original object instead of manipulating 
it directly.  You can take a copy of any UM file object in either of these 
forms:

.. code-block:: python

    >>> ff_copy = ff.copy()
    >>> ff_copy2 = ff.copy(include_fields=True)
    
.. Note::

    The "include_fields" flag enables you to choose whether or not you want 
    your copy to include *copies* of all the field objects or not (all of the 
    other header components are always copied).  Which approach is correct 
    depends on your application; you might want the copy to start with a blank 
    list if you intend to select only a few fields from the original object, 
    or you might prefer it to contain all fields if you intend to apply some 
    sort of processing to every field.

Now you should experiment a little with the processes above - in particular 
try the following (*solutions will follow in the next section!*):

  * What happens if you change the value of "num_p_levels" in the 
    integer constants and then try to write out the file?

  * Since the first field is the land-sea mask (sorry - spoiled the surprise -
    did you guess it earlier?) see if you can write a new file which contains
    only the first *two* fields in the file, and change the second field so 
    that it gets written out on land-points only.

    .. Note:: In case you don't have a copy of UMDP F03 to hand the "lbpack"
              code for an unpacked field on land-points only is "120".

Solutions 
,,,,,,,,,
If you tried the above you should have found that changing the number of 
levels produces a file object that can't be written out; because the setting
no longer agrees with the dimensions of the level dependent constants.

Did you manage to output the land packed field?  Here's a solution:

.. code-block:: python

    >>> test_file = mule.tests.testdata_filepath("n48_eg_regular_sample.ff")
    >>> ff = mule.FieldsFile.from_file(test_file)
    >>> ff.fields = ff.fields[0:2]
    >>> ff.fields[1].lbpack = 120
    >>> ff.fields[1].lbrow = 0
    >>> ff.fields[1].lbnpt = 0
    >>> ff.to_file(os.path.expanduser("~/mule_example.ff"))

You might have found that the API would not let you write the file without 
you also setting the number of rows and columns in the field to zero (which 
is a requirement for land-packed fields).


Working with STASHmaster files
------------------------------
Along with the basic file definition, a separate STASHmaster file exists at each
UM version.  This provides additional information specific to each field type
available to the UM, and can sometimes be useful for making sense of certain 
aspects of the field.

Mule provides a module which can read a STASHmaster file to help with this, and 
will also automatically do this when loading a file (if possible).  There are 
3 different ways to load a STASHmaster.  The simplest is to provide the path to
the file directly:

.. code-block:: python

    >>> from mule.stashmaster import STASHmaster
    >>> sm = STASHmaster.from_file("/path/to/stashmaster/file")

Alternatively, if your STASHmaster files are stored in paths which contain the 
relevant UM version number, you can load them from the version number:

.. code-block:: python

    >>> sm = STASHmaster.from_version("10.4")

Note that this uses the pattern defined by 
`mule.stashmaster.STASHMASTER_PATH_PATTERN` - you should customise this at
the beginning of your script if it doesn't suit your configuration; by default
it is set to:

.. code-block:: python

    >>> mule.stashmaster.STASHMASTER_PATH_PATTERN
    '$UMDIR/vn{0}/ctldata/STASHmaster/STASHmaster_A'

This mimics the location where the UM is traditionally installed.  Note that 
any environment variables in the pattern will be expanded, and the pattern will
expect to be passed to :meth:`str.format` to receive the version number.  

The final method for loading the STASHmaster is to load it based on the UM 
version from the header of a :class:`mule.UMFile` subclass instance:

.. code-block:: python

    >>> sm = STASHmaster.from_umfile(umfile_object)

.. Note::

   None of the methods for loading the STASHmaster result in a fatal error if
   they are unsuccessful - this is because the data in the STASHmaster is 
   useful but *not essential* and most operations in Mule will still work 
   without access to a STASHmaster file.  In the event of failing a warning
   will be printed and the returned object will be `None`.

Whichever method is used, the returned object is the same; it behaves very much
like a dictionary, accepting the STASH code of the desired entry as either an
integer or string:

.. code-block:: python

    >>> sm[16004]
    <stashmaster._STASHentry object: SC:16004 - "TEMPERATURE ON THETA LEVELS">
    >>> sm["10"]
    <stashmaster._STASHentry object: SC:   10 - "SPECIFIC HUMIDITY AFTER TIMESTEP">
    
It can also be filtered to return a new :class:`mule.stashmaster.STASHmaster` 
object containing a subset of the original (by either section code, item code,
or a regular expression based on the STASH name entry):

.. code-block:: python

    >>> sm
    <stashmaster.STASHmaster object: 3958 entries>
    >>> sm.by_section(0)
    <stashmaster.STASHmaster object: 375 entries>
    >>> sm.by_item(4)
    <stashmaster.STASHmaster object: 24 entries>
    >>> sm.by_regex(r"(WIND|TEMPERATURE)")
    <stashmaster.STASHmaster object: 151 entries>

The elements of the dictionary are fairly simple objects which store the data,
using the names taken from UMDP-C04.  Some of these are themselves dictionaries:

.. code-block:: python

    >>> entry = sm[16004]
    >>> entry.grid, entry.levelT, entry.ppfc
    (1, 2, 16)
    >>> entry.packing_codes
    {'PC8': -99, 'PC9': -99, 'PC2': -10, 'PC3': -3, 'PC1': -3, 'PC6': 21, 'PC7': -3, 'PC4': -3, 'PC5': -14, 'PCA': -99}

To save time when working with files - Mule will automatically load the 
STASHmaster when loading a :class:`mule.UMFile` subclass (assuming its UM 
version number translates to a path that exists).  It will attach a `stash` 
attribute to each field in the file found in the STASHmaster linking to its 
STASH entry for easy access to the STASH properties.  You can override the 
mechanism used to load the STASHmaster by passing an additional keyword to the
file loading command:

.. code-block:: python

    >>> import mule
    >>> ff = mule.FieldsFile.from_file("/path/to/your/file.ff", 
                                       stashmaster="/path/to/your/stashmaster")

.. Note::

    Since trying to load a non-existent STASHmaster file does not result in a 
    failure you can effectively "disable" the automatic loading by passing a 
    false path here.

You can also attach valid STASHmaster entries from any 
:class:`mule.stashmaster.STASHmaster` object after loading a file (all existing
attached entries will be replaced):

.. code-block:: python

    >>> ff.attach_stashmaster_info(sm)

Please see UMDP-CO4 for further details on the contents of the STASH entries.

Working with pp files
---------------------

Mule also has some basic support for reading and writing pp files - these are
a descendant format of a :class:`mule.FieldsFile`, but do not preserve enough 
of the typical file structure to be represented by a :class:`mule.UMFile` 
variant.  Instead a pp file is treated more as a read/write method - for example
to read in one of the pp files from the test suite:

.. code-block:: python

    >>> from mule.pp import fields_from_pp_file
    >>> test_file = mule.tests.testdata_filepath("n48_multi_field.pp")
    >>> fields = fields_from_pp_file(test_file)

This will return a list containing :class:`mule.pp.PPField` objects (which
are functionally very similar to :class:`mule.Field` objects).  These will have
lookup properties, a :meth:`get_data` method and everything you would expect
from a field object created as part of a :class:`mule.UMFile`.  You should 
be able to use the two interchangably (e.g. if you wish to output a field
read from a pp file into a fields-file simply insert its 
:class:`mule.pp.PPField` object into the list of fields attached to your 
:class:`mule.UMFile` object).  

pp files can also be variable resolution, and for these an extra property
is attached to each :class:`mule.pp.PPField` object called 
:meth:`pp_extra_data` which contains information about the variable grid.
(You can see an example if you try loading the `ukv_eg_variable_sample.pp` 
file).

You can write out field objects to a pp file in a similar way:

.. code-block:: python

    >>> from mule.pp import fields_to_pp_file
    >>> fields_to_pp_file("output_file.pp", fields)

.. Note::

    If you are trying to output pp fields which originated in a variable
    resolution :class:`mule.UMFile` you will need to provide a reference to
    the original :class:`mule.UMFile` object as a keyword to the above call.
    This will cause Mule to calculate the appropriate extra data to attach
    to the pp fields.

Conclusion
----------
Having worked through this section you should now be familiar with the basic 
elements of the API - you should be able to interrogate a file to access 
and modify its header values, and write it to a new file.  
    
