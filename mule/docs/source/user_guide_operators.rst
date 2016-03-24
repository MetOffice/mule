Data Operators
==============
So far there is one aspect of manipulating UM files which hasn't been 
addressed - modifying the actual data content of the fields.  This 
section will cover how to do this in detail, as it is a bit more involved
than simple filtering and header modifications.


The principles behind operators
-------------------------------
A key goal of this API is to be fairly lightweight and efficient, this
is at its most difficult when trying to process large UM files containing
tens of thousands of fields.  In the basic part of the user guide you
saw how a :class:`mule.Field` object doesn't store any data, only a 
method :meth:`get_data` which returns a data array when accessed; this
is central to the way data operators work.

In the case of fields in a file object loaded from disk, the :meth:`get_data`
method is directly linked to some subclass of the :class:`mule.DataProvider` 
class attached to the field.  When reading from a file that class contains
instructions to:
  
  * Open the file containing the field (if it wasn't already open).
  * Read in the raw data of the field.
  * Unpack and/or uncompress the field data if it was packed.

All of the above then allow the 2-d array data to be returned to you.  In 
the earlier section we called :meth:`get_data` manually to do this, but 
consider what is happening when you don't do this and you try to write out
some fields to a new file.  For each field being written the API first 
calls :meth:`get_data` to retrieve the data in the field, then it writes
the data out to the new file.

.. Note::
    Actually, it is a little more complicated than this - if the field's
    data *hasn't been modified* as we are about to describe and the packing
    settings (lbpack and bacc) of the field *haven't been changed*, the 
    data provider actually bypasses step 3 above (because there's no 
    point in unpacking all the data only to immediately re-pack it again!)

So with all that in mind - in order to efficiently make changes to the data
in the field you hook into this :meth:`get_data` mechanism; intercepting
the data given by the field's normal data provider and adding your own
changes.  A :class:`mule.DataOperator` provides a simple and re-usable 
framework to do exactly this.


Defining an operator
--------------------
Before we dive in and try to write a :class:`mule.DataOperator` let's first 
quickly examine what parts make up an operator.  Here's a definition of an
operator:

.. code-block:: python

    import mule
    
    class ExampleOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, source_field):
            return source_field.copy()

        def transform(self, source_field, new_field):
            return source_field.get_data()


This is pretty much the absolute barebones minimal example of an operator,
if you carried the example through it would work, but it won't actually
have any effect on anything right now.  But still, let's take a moment to
analyse what we can see above.

Firstly, the operator inherits from :class:`mule.DataOperator` - this is an
important detail, as without the logic contained in this parent class the
functionality will not work.  Your operator **must** override the 3 methods
you see here (not doing so will cause it to raise an exception when used).  
Each of these methods has a special purpose.


The :meth:`new_field` method
,,,,,,,,,,,,,,,,,,,,,,,,,,,,
Let's start with the :meth:`new_field` method - when you come to use this
operator you will apply it to an existing :class:`mule.Field` object.  At
that point a reference to the original field object will pass through 
:meth:`new_field`.  The method *must* return a new field object (as the
name implies), and in the example above it is doing so by taking an exact
copy of the original field.  However in practice this is where you might 
want to make changes to the lookup header that are required by the 
operation, for instance:

.. code-block:: python

    import mule
    
    class ExampleOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, source_field):
            field = source_field.copy()
                        
            field.lbproc += 512

            return field

        def transform(self, source_field, new_field):
            return source_field.get_data()

Now the :meth:`new_field` method is again copying the source field, but it
is incrementing the "lbproc" value of the new field by 512 before returning it
- to save you reaching for UMDP F03 this change is supposed to indicate that 
the field's data is the "square root of a field" - so if this operator were 
designed to take the square root of the original data this would be a suitable 
change to make here.

.. Warning::
    It is highly advisable **not** to modify the "source_field" argument in
    this routine.  If you do then the original field will be modified after
    the call to your operator -  if you aren't being very careful this will 
    be confusing and could lead to all sorts of problems.


The :meth:`transform` method
,,,,,,,,,,,,,,,,,,,,,,,,,,,,
This is the most important method in the operator - it is exactly the method
that will be called by the new field object (returned by the :meth:`new_field`
method) when the field's :meth:`get_data` method is called.  It must return 
the data array for the field and **this** is where you will introduce your own
modifications (because in practice this won't get called until it is time to
write the field out to a new file).

As with the :meth:`new_field` method this method will be passed a reference to 
the original field object, as well as a reference to the *new* field object.  
In the example above the :meth:`transform` method was simply taking the data
from the original field and returning it (resulting in no change) so let's
update that:

.. code-block:: python

    import mule
    import numpy as np
    
    class ExampleOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, source_field):
            field = source_field.copy()
                        
            field.lbproc += 512

            return field

        def transform(self, source_field, new_field):
            data = source_field.get_data()

            data = np.sqrt(data)
            
            return data


Continuing the idea from the :meth:`new_field` method - our :meth:`transform`
method now does what the new "lbproc" code indicates.  It first obtains the
original data from the source field (by calling its :meth:`get_data` method)
and then calculates the element-wise square root before returning it.

.. Warning::
    Just like with the :meth:`new_field` method - it is strongly recommended
    that you **do not** modify either the "source_field" or "new_field" 
    arguments in this routine.  They are intended to be for reference only.


The :meth:`__init__` method
,,,,,,,,,,,,,,,,,,,,,,,,,,,
That only leaves the init method - this method is just like any other class
initialising method in Python - there are no special requirements here for
what it should do, but it might be used to pass additional information to
different instances of the same operator.  An example of this will be in
the upcoming example.


Your first operator
-------------------
Let's actually create a real operator now and try applying it to some fields,
we'll start with the same barebones example as above.  (You may want to put
this into a script at this point, as running this at the command line will
become tiresome!):

.. code-block:: python

    import mule
    
    class ExampleOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, source_field):
            return source_field.copy()

        def transform(self, source_field, new_field):
            return source_field.get_data()

To make it easy to see what the operator is doing we are going to scale
a region of the input field by a factor.  Here's some code to do that (note 
we will also re-name the operator here to something more relevant):

.. code-block:: python

    class ScaleBoxOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, source_field):
            return source_field.copy()

        def transform(self, source_field, new_field):
            data = source_field.get_data()

            size_x = new_field.lbrow
            size_y = new_field.lbnpt

            x_1 = size_x/3
            x_2 = 2*x_1
            y_1 = size_y/3
            y_2 = 2*y_1

            data[x_1:x_2, y_1:y_2] = 0.1*data[x_1:x_2, y_1:y_2]

            return data


We're just grabbing approximately the middle third of the data and lowering
the values by 90%.  Before we continue let's apply this to a field (we'll 
take a field from one of the example files used in the basic section of the 
guide, see that section for details):

.. code-block:: python

    scale_operator = ScaleBoxOperator()

    # "ff" is a FieldsFile object and we take the second field this time
    field = ff.fields[1]

    new_field = scale_operator(field)

Try calling the :meth:`get_data` method of either the original field or the
new field and plotting the data (again see the basic section for details).  
You should be able to see that the new field has the central region scaled
as we intended.
    
Notice that the operator still needs to be instantiated (the first line above),
but it can then be used to process any number of fields.  The initial call is
the point you could include arguments to the :meth:`__init__` method, for 
example here it might be logical to be able to pass in the scaling factor:


.. code-block:: python

    class ScaleBoxOperator(mule.DataOperator):

        def __init__(self, factor):
            self.factor = factor

        def new_field(self, source_field):
            return source_field.copy()

        def transform(self, source_field, new_field):
            data = source_field.get_data()

            size_x = new_field.lbrow
            size_y = new_field.lbnpt

            x_1 = size_x/3
            x_2 = 2*x_1
            y_1 = size_y/3
            y_2 = 2*y_1

            data[x_1:x_2, y_1:y_2] = self.factor*data[x_1:x_2, y_1:y_2]

            return data


The passed argument is simply saved to the operator and then re-used in the
:meth:`transform` method as required.  By doing it this way we can create
slightly different operator instances from the same class, like this:

.. code-block:: python

    scale_half_operator = ScaleBoxOperator(0.5)
    scale_quarter_operator = ScaleBoxOperator(0.25)


We aren't going to do anything in the :meth:`new_field` method here, because
we already covered it in the example above (and there isn't really anything 
sensible we can set in the header for this slightly odd manipulation) but it
would work in just the same way.


Multi-field or other operators
------------------------------
In some cases the formula discussed above might not be quite sufficient for
a task - for example if the new field is supposed to be a product or a 
difference of two or more existing fields, or if the new field isn't actually
based on an existing field at all.

The operator class allows for this; the first argument to both the 
:meth:`new_field` and :meth:`transform` method is actually completely 
generic.  You can pass any type you like to these, so long as the methods 
still return the correct result (a new :class:`mule.Field` object and a
data array, respectively).  So for example an operator which multiplies
two existing fields together might look like this:


.. code-block:: python

    class FieldProductOperator(mule.DataOperator):

        def __init__(self):
            pass

        def new_field(self, field_list):
            field = field_list[0].copy()
            
            field.lbproc += 256

            return field

        def transform(self, field_list, new_field):

            data_1 = field_list[0].get_data()
            data_2 = field_list[1].get_data()

            return data_1*data_2


Note that our input to :meth:`new_field` is now a list of fields, and we 
simply assume the headers should copy from the first field in the list 
(we update "lbproc" by 256 - "Product of two fields" according to UMDP F03).
The operator then simply retrieves the data from both fields and multiplies
them together.

.. Note::
    This example is designed for brevity but in practice you might want
    to include some input checking in the methods - for example the above
    could check that the input is actually a list and that it contains
    2 fields (and maybe that it contains *exactly* 2 fields).  However 
    note that you don't need to repeat the checks in both of the methods
    (the argument passed to :meth:`transform` will always be *exactly* 
    what was passed to :meth:`new_field`)

In actual fact the first argument can be literally *anything* - so you are 
free to implement your operator however you wish (as long as each method
returns the correct output).
    

Provided Operators for LBCs
---------------------------
Compared to the other file types the data sections of the fields in LBC files
are slightly more awkward to interpret.  In this section we will explain the 
features which can help with transforming the LBC data - for full details of 
exactly how the data is arranged consult the main UM documentation.

Supposing we have loaded an LBC file, then accessing the data from the first
field will return an array with one dimension being the vertical level and the 
other containing all points in the field in an LBC specific ordering:

.. code-block:: python

    >>> # "lbc" is an LBCFile object
    >>> field = lbc.fields[0]
    >>> data = field.get_data()
    >>> data.shape
    (38, 272)

In some cases this might be suitable for your requirements without any extra
interpretation.  For example if you simply want to scale the entire field by
a factor or add it to another field, it doesn't matter that the points are 
arranged in this way.  However if your processing needs to refer to specific 
parts of the domain or if you wish to visualise the data in some way, you can 
make use of the following built-in operator:

.. code-block:: python

    >>> from mule.lbc import LBCToMaskedArrayOperator
    >>> lbc_to_masked = LBCToMaskedArrayOperator()
    >>> masked_field = lbc_to_masked(field)
    >>> data = masked_field.get_data()
    >>> type(data)
    <class 'numpy.ma.core.MaskedArray'>
    >>> data.shape
    (38, 18, 24)

It's a simple operator, requiring no arguments and mapping directly from a 
standard LBC field.  The resulting object's :meth:`get_data` method returns
a masked-array where the central portion of the LBC domain provides the mask. 
It still has the level dimension but the other one has been expanded to appear 
as a 2d array.

Of course if this is being done as part of a broader (set of) data operations
with the intention of writing out the field with modifications, it will need 
to be translated back the other way before writing.  An equivalent operator
exists to perform this reverse-translation:

.. code-block:: python

    >>> from mule.lbc import MaskedArrayToLBCOperator
    >>> masked_to_lbc = MaskedArrayToLBCOperator()
    >>> field = masked_to_lbc(masked_field)
    >>> data = field.get_data()
    >>> type(data)
    <type 'numpy.ndarray'>
    >>> data.shape
    (38, 272)

As discussed above the modular nature of the operators means that for LBC files
a common pattern will be to apply the :class:`LBCToMaskedArrayOperator` to a
field from an input file, followed by an operator of your own and then 
eventually use the :class:`MaskedArrayToLBCOperator` to prepare it for output.


Conclusion
----------
Having read through this section you should have an idea of how you can use
data operators to manipulate the data in UM files.  As a slightly abstract 
concept the best way to improve your understanding from here is to try writing
a few simple operators of your own and see what you can come up with!
