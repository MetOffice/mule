Handling Validation/Fixing Broken Files
=======================================
Unless you are very fortunate, it's inevitable that you will one day try to 
read or write a file with Mule and encounter a validation error.  The file 
classes perform validation both to protect themselves from unexpected 
errors when reading an invalid file, and to protect you and other systems by 
preventing invalid file/s being written.

Reading a file which won't validate
-----------------------------------
Suppose you have a file which you believe to be a :class:`mule.FieldsFile`,
but when you try to read it in you are presented with a traceback and the
following exception:

.. code-block:: python

    mule.ff.ValidateError: FieldsFile failed to validate: Incorrect dataset_type (found -32768, should be one of [1, 2, 3])
    
The error explains what the problem is, but since it won't let you read the
file in - how can you investigate further or fix the file?  This is where
the :class:`mule.UMFile` class is useful.  It has no nicely named properties
and is not able to interpret any field data, but it also has no validation;
meaning it should read in almost any type of UM file without issue.

So using it to read in the file producing the problem above we can navigate
to the source of the error:

.. code-block:: python

    umf = mule.UMFile.from_file("/path/to/problem_file.ff")

    print umf.fixed_length_header.dataset_type
    -32768

we can then fix the file manually and write it back out again:

.. code-block:: python

    umf.fixed_length_header.dataset_type = 3
    
    umf.to_file("/path/to/fixed_file.ff")

and then try to read the file again using the :class:`mule.FieldsFile` class.  
It's quite possible that this will throw another validation error, but this 
time referencing some other aspect of the file; for most simple cases of a
header being unset/set incorrectly this approach (although slightly tedious)
should eventually result in a readable file.

Re-casting parts of a UMFile object
-----------------------------------
In some cases, trying to fix a particularly broken file in the above way can 
become a little tiresome.  Not only that but if you encounter a problem with
the actual dimensions of part of the file, for instance:

.. code-block:: python

    mule.ff.ValidateError: FieldsFile failed to validate: Incorrect number of integer constants, (found 29, should be 46)

it's not quite such a simple fix as you need to add the missing values.  The 
nicest way to do this is to make use of the same parts of the API which your 
chosen :class:`mule.UMFile` subclass uses.  After loading the problematic file
in the same way as the earlier example, there are two ways to re-construct the
integer constants:

.. code-block:: python

    # Create an "empty" component, it'll be the right size for a FieldsFile
    # but will be filled with missing-data indicators
    int_const = mule.ff.FF_IntegerConstants.empty()

    # Set the values as you wish here, for instance if you want to
    # keep the values from the original
    int_const.raw[:len(umf.integer_constants.raw)] = umf.integer_constants.raw[:]
    # And make any other manual changes
    int_const.timestep = 500

    # Then replace the version in the file with the new one
    umf.integer_constants = int_const

As with many other operations there's no need to worry about positional 
header elements.  Note that once you have "re-cast" the component object it
will also gain the nice named attributes; this can be potentially useful when
working with a "broken" file even if it's dimensions are correct.  For example
again working with the above file if we assume the real constants were the 
correct size but we want to be able to access them by name we could do this:

.. code-block:: python

    umf.real_constants = mule.ff.FF_RealConstants(umf.real_constants.raw[1:])

The above uses a sligthly different form for constructing the new object; we
have to trim the 0th element from the original array, but we end up with an
identical object that has the named properties we wanted.  

Re-casting 2-dimensional arrays
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
The above tips become slightly more complicated when you are trying to apply 
them to 2-dimensional header components.  The reason behind this is that the
file objects do not typically know what at least one of the dimensions is 
supposed to be, requiring extra information.  To highlight this consider
these statements (which you might use if your level dependent constants need
fixing):

.. code-block:: python

    ldc = mule.ff.FF_LevelDependentConstants.empty(71, 8)

This will produce a set of level dependent constants for a 70 level file 
(remember a 70 level model defines 71 constants, due to the surface/rho levels)
and with 8 different constant types.  Both of the size arguments here are 
defined as optional; omitting them or passing either as "None" will cause the
class to look internally for the correct sizing information.  Thus if you run:

.. code-block:: python

    ldc = mule.ff.FF_LevelDependentConstants.empty(71)

You'll see that you *still* get a second dimension of 8 - because for a 
:class:`mule.FieldsFile` that is the valid size for that dimension.  However
the number of levels is an unkown dimension, so either of these commands will
not work:

.. code-block:: python

    ldc = mule.ff.FF_LevelDependentConstants.empty()
    ldc = mule.ff.FF_LevelDependentConstants.empty(None, 8)

Note that you can still use the same trick as in the 1-dimensional case to
give named-attributes to the header components (provided they are already
of the correct size) by trimming off the 0th elements of the final dimension
(which in all current file types is always the padded dimension)

.. code-block:: python

    umf.level_dependent_constants = (
         mule.ff.FF_LevelDependentConstants(
             umf.level_dependent_constants.raw[:,1:]))

Problems with Field objects
---------------------------
Compared the the remainder of the file relatively little validation is done
on the field objects it stores - in most cases if you run into any kind of 
error here it will be because the grid defined by the file headers doesn't
appear to match the grid defined by one (or more) of the fields.

When Mule does this part of the validation, it uses the field's grid 
definition to calculate the *final point* in the domain, and compares this
to the equivalent calcualtion based on the file's grid definition.  Assuming
we have a field failing to validate stating that it's longitudes are 
inconsistent; we can investigate it as follows:

.. code-block:: python

    # Get the field which was quoted in the error message
    field = umf.fields[1234]

    # Calculate the "final longitude" of the field
    field_lon = field.bzx + field.lbnpt*field.bdx

    # Calculate the "final longitude" of the file - we'll first re-cast
    # the header components we need as described above (for the nice names!)
    umf.integer_constants = mule.ff.FF_IntegerConstants(umf.integer_constants.raw[1:])
    umf.real_constants = mule.ff.FF_RealConstants(umf.real_constants.raw[1:])
    file_lon = (umf.real_constants.start_lon +
                umf.real_constants.col_spacing*umf.integer_constants.num_cols)

    # To be "valid" the two calculated longitudes must be no more than 1.5
    # grid-spacings apart (this accounts for the different grid-staggering and
    # grid-offset combinations without requiring the STASHmaster)
    print file_lon - field_lon
    3.75
    print umf.real_constants.col_spacing*1.5
    2.8125

In the example above it looks as though the calculated longitudes are actually
2 grid-spacings apart, making the grid definition inconsistent by (at least)
half a grid spacing.  This is about as far as this guide can get you in terms
of how to fix this problem however. In some cases it will be sufficient to 
correct one or more of the headers, in others the source of the original data
will need investigating (as it may be producing inconsistent output).

If the inconsistency is in the field latitude instead of the longitude the 
exact same set of steps applies (but using the latitude-specific versions of
each header item instead).

Conclusion
----------
Having worked through this section you should hopefully be familiar with some
of the most common problems which you may encounter when working with files
using Mule, and have an idea of where to start correcting the files or giving
the issue further investigation.
