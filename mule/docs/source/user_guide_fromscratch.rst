Creating files from scratch
===========================
What about when you don't have any files to start from?  This section covers
the features Mule has to assist in creating new files from scratch (though 
note that this mostly pertains to creating the right objects; populating the
various headers with *appropriate* values will still be required separately
as part of the process to produce truly UM compliant files).

Creating a new file from a template
-----------------------------------
Mule has some built in knowledge about the sizes and requirements of certain
parts of each recognised file-type.  You can combine this with some 
information provided in a "template" dictionary to quickly construct a
partially populated file object.

A Minimal Template
,,,,,,,,,,,,,,,,,,
Suppose we want to make an empty :class:`mule.UMFile` subclass; we know we 
want it to have 500x300 points and 70 levels.  The minimum possible template 
to achieve our result would look like this:

.. code-block:: python

    template = {
        'integer_constants':{
            'num_p_levels': 70,
            'num_cols': 500,
            'num_rows': 300 
            },
        'real_constants':{
            },
        'level_dependent_constants':{
            'dims': (71, None)
            }
        }

If you've been using the API in the earlier examples you should recognise 
the names used in the different keys here - they are the same attribute 
names used by the file classes.  The keys each correspond to one of the file 
header components, and the associated values are also dictionaries which map 
each header property onto a value.  

.. Note::
    The template must contain an entry for a component if you want it to 
    exist (even if you don't populate any of the values) - see the values
    for real constants in the template above.

.. Note::
    The special "dims" header attribute allows you to explicitly provide the 
    size/shape for the given component.  If any dimensions are not set Mule
    will try to use the file class's in-built dimension information to size
    the component (so in the example above both the integer and real constants
    and the 2nd dimension of the level dependent constants will be sized 
    automatically if possible)

The template can be used to generate the new object by passing it to one of
the specific classes:

.. code-block:: python

    import mule

    new_ff = mule.FieldsFile.from_template(template)

    new_dump = mule.DumpFile.from_template(template)

    new_lbc = mule.LBCFile.from_template(template)

    new_ancil = mule.AncilFile.from_template(template)

Feel free to give this a try - if you inspect the file objects these create
you should be able to confirm that they each contain a set of integer, real 
and level dependent constants.  Each of these will be the correct size for the
given file type and the properties mentioned in the dictionary should be set.

This is far from complete however - you'll find you can't write this out
or call the :meth:`validate` method without errors, because certain other key
headers aren't set.

A More Complete Template
,,,,,,,,,,,,,,,,,,,,,,,,
If we expand the earlier template example to something more typical of a 
standard fields-file it might look something like this:

.. code-block:: python

    n_rows = 300
    n_cols = 500
    n_levs = 70

    template = {
        'fixed_length_header':{
            'data_set_format_version': 20,  # Always fixed
            'sub_model': 1,                 # Atmosphere
            'vert_coord_type': 1,           # Hybrid heights
            'horiz_grid_type': 0,           # Global file
            'dataset_type': 3,              # Fieldsfile
            'grid_staggering': 6,           # ENDGame
            },
        'integer_constants':{
            'num_p_levels': n_levs,
            'num_cols': n_cols,
            'num_rows': n_rows 
            },
        'real_constants':{
            'col_spacing': 360.0/n_cols,
            'row_spacing': 180.0/n_rows,
            'start_lat': -90.0,
            'start_lon': 0.0,
            'north_pole_lat': 90.0,
            'north_pole_lon': 0.0,
            },
        'level_dependent_constants':{
            'dims': (n_levs + 1, None),
            'eta_at_theta': np.arange(n_levs + 1),
            }
        }

This sets up slightly more of the headers (though it could still go further), 
it also illustrates how the arrays in the level dependent constants can be set 
in this way (though in the example we aren't setting them to anything 
meaningful).  Note that we are also now explicitly setting the "dataset_type"
to indicate that this is a template for a fields-file; therefore a file object
constructed from this template will no longer validate unless it is of the 
specified type (:class:`mule.FieldsFile` in this case).

Creating Fields from Scratch
----------------------------
A new file object on its own isn't of much use - so we now need to put some
:class:`mule.Field` objects into it.  Similar to the creation of the files some 
manual work will be required to produce field's which are *completely* valid.  

Unlike the file objects there is no templating system for the fields, instead 
you must populate them by hand (though in practice if you were generating 
multiple fields it would probably make sense to do things in a loop or a 
method of some sort).  Carrying on from the earlier template example you could
do something like this, re-using some of the values from the earlier example:

.. code-block:: python
    
    new_ff = mule.FieldsFile.from_template(template)

    new_field = mule.Field3.empty()

    # To correspond to the header-release 3 class used
    new_field.lbrel = 3 

    # Several of the settings can be copied from the file object
    new_field.lbnpt = new_ff.integer_constants.num_cols
    new_field.lbrow = new_ff.integer_constants.num_rows

    new_field.bdx = new_ff.real_constants.col_spacing
    new_field.bdy = new_ff.real_constants.row_spacing

    # Assuming it's a P-grid field in our ENDGame file means the zeroth 
    # point for the field will be half a grid spacing behind the origin
    new_field.bzx = new_ff.real_constants.start_lon - 0.5*new_field.bdx
    new_field.bzy = new_ff.real_constants.start_lat - 0.5*new_field.bdy

    # Finally - since Mule uses the first element of the lookup to test
    # for unpopulated fields (and skips them) the first element should be
    # set to something.  Since it's typically the year that will do:
    new_field.raw[1] = 2017

.. Note::
    You can use either the :class:`mule.Field2` or :class:`mule.Field3` class
    for this, depending on your requirements (the two classes refer to the two
    different PP header releases).

Getting Data into the new Field
-------------------------------
You'll also need to add some data to your field. When you read an existing
file each :class:`mule.Field` object has a data provider attached to it which
allows it to read the data from disk (and possibly unpack it).  In order to 
provide your new field with the means to return data you will need to attach
your own data provider.  

For the simplest case - your data already exists in some way as a numpy array
and you wish to use that array as the field's data - there is a built in
provider class you can use.  Here's how to use it - we'll add a simple 
gradient array to our field above:

.. code-block:: python

    data_array = np.arange(300*500).reshape(500,300)

    array_provider = mule.ArrayDataProvider(data_array)

    new_field.set_data_provider(array_provider)

Once you do this, you should be able to call the :meth:`get_data()` method of
the field and it will return the array. 

Note however that the provider can technically be any class you choose to
create - as long as it defines a suitable :meth:`_data_array` method which 
returns a 2d numpy array.  For example suppose you wish to make use of data
contained in a separate NetCDF file using the Python module which can read it
(the `netCDF4` module syntax should be understandable but please refer to its 
documentation if anything isn't clear):

.. code-block:: python
    
    from netCDF4 import Dataset

    class NetCDFProvider(object):
        """
        A data provider class which returns some data from a specific 
        variable in a NetCDF file.

        """
        def __init__(self, ncdf_file, variable_name):
            """
            Initialises the provider with the path to the NetCDF file
            and the string-name of the variable containing the data.

            """
            self.filename = ncdf_file
            self.variable_name = variable_name
    
        def _data_array(self):
            """
            Provides the data as an array when requested by accessing the
            stored file and variable name.

            """
            with Dataset(self.filename) as ncdf:
                variable = ncdf.variables[self.variable_name]
                return variable[:,:]

    # Can create providers for different variables in the NetCDF file
    # (this would probably be done as part of creating the field objects)
    ncdf_t_provider = NetCDFProvider("/path/to/ncdf_file.nc", "temperature")
    ncdf_q_provider = NetCDFProvider("/path/to/ncdf_file.nc", "humidity")
    
    # If we had 2 suitable newly created field objects we could set them up
    # with the above providers
    new_t_field.set_data_provider(ncdf_t_provider)
    new_q_field.set_data_provider(ncdf_q_provider)

The advantage in this case is that since the file and data access are all
within the :meth:`_data_array` method, the data isn't stored in memory for 
every field and you gain the same benefits of deferred access.  

.. Note::
    The example above isn't perfect either; if it were a real example it would
    probably make more sense to have the class accept the 
    :class:`NetCDF4.Dataset` object at initialisation instead of the path to
    the file, though it depends on how many different variables this is being
    applied to. (Currently every call to :meth:`_data_array` opens and closes 
    the file, which may be inefficient if done too frequently).

Putting it all Together
-----------------------
All that's left to do is add the new fields to the new file; if you've been
using the API already or looked at the earlier parts of the user guide you'll
know that this is as simple as adding the :class:`mule.Field` objects to the
field-list.  The total process (heavily para-phrased) should look something 
like this:

.. code-block:: python

    # Create a new file from a template
    new_ff = mule.FieldsFile.from_template(template)

    # Let's assume we have some criteria to generate a set of "n_fields"
    for i_field in n_fields:

        # Create an empty field
        new_field = mule.Field3.empty()

        # To correspond to the header-release 3 class used
        new_field.lbrel = 3 
        
        # (etc etc etc) set new field headers

        # Attach some sort of data provider to return the desired data
        data_provider = MyDataProvider(arg1, arg2)
        new_field.set_data_provider(data_provider)

        # Finally add the field to the file
        new_ff.fields.append(new_field)

    # ... and write out the finished file once all fields are added
    new_ff.to_file("/your/output/file.ff")

Conclusion
----------
Having read through this section you should have an idea of the features 
available to save some time when creating new files.  However really the 
best way to understand how to fit this to your own needs is to experiment 
with the ideas above and see what works and what doesn't.
