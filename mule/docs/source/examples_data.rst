Examples: Modifying data in individual fields
=============================================

Example 1: Set all real data fields to zero
-------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import ScaleFactorOperator

    zero_operator = ScaleFactorOperator(0.0)

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    for field in ff.fields:
        if field.lbrel in (2,3) and field.lbuser4 != 30:
            ff_out.fields.append(zero_operator(field))
        else:
            ff_out.fields.append(field)

    ff_out.to_file("OutputFile")

.. Note::

    * A copy of the original file object is not strictly necessary, but
      it avoids overwriting the original field objects.
    * The built-in operators in `mule.operators` handle mdi points in a 
      sensible way - in this example points set to mdi will not be changed.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters out fields with the STASH code `30` - this is the
      land-sea mask, and probably should not be zeroed; note that since only
      fields with valid header releases define the `lbuser4` property it is 
      important that the two `if` conditions are placed in the order above.
    * Since the packing code (`lbpack`) of the modified fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy - in some cases this might not be suitable so you may need to 
      consider whether to update the value of `lbpack` on each field before 
      appending it to the file.
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 2: Set level-1 u fields (STASH code 2) to their absolute values
-----------------------------------------------------------------------

.. code-block:: python

    import mule
    import numpy as np

    class AbsoluteOperator(mule.DataOperator):
        """Operator which sets all non-missing points to their absolute value"""
        def __init__(self):
            pass
        def new_field(self, source_field):
            """Creates the new field object"""
            field = source_field.copy()
            return field
        def transform(self, source_field, new_field):
            """Performs the data manipulation"""
            data = source_field.get_data()
            data_out = np.abs(data)
            # If the field defines MDI, reset missing points from original
            # field back to MDI in the output
            if hasattr(source_field, "bmdi"):
                mdi = source_field.bmdi
                mask = (data == mdi)
                data_out[mask] = mdi
            return data_out

    abs_operator = AbsoluteOperator()

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lbuser4 == 2 and field.lblev == 1:
            ff.fields[ifield] = abs_operator(field)
            
    ff.to_file("OutputFile")

.. Note::

    * There aren't any built-in operators in `mule.operators` which provide 
      this functionality, so this example creates a custom operator.
    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required STASH code and level; note that
      since only fields with valid header release numbers define `lbuser4` and 
      `lblev`, so it is important that the `if` conditions for these appear 
      after the check on `lbrel`.
    * Since the packing code (`lbpack`) of the modified fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy - in some cases this might not be suitable so you may need to 
      consider whether to update the value of `lbpack` on each field before 
      appending it to the file (or inside the operator's `new_field` method).
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 3: Raise all fields valid at 12Z to the power 3
-------------------------------------------------------

.. code-block:: python

    import mule

    class ExponentOperator(mule.DataOperator):
        """Operator which raises all non-missing points to an exponent"""
        def __init__(self, exponent):
            """Initialise the operator, setting the exponent value"""
            self.exponent = exponent
        def new_field(self, source_field):
            """Creates the new field object"""
            field = source_field.copy()
            return field
        def transform(self, source_field, new_field):
            """Performs the data manipulation"""
            data = source_field.get_data()
            data_out = data**self.exponent
            # If the field defines MDI, reset missing points from original
            # field back to MDI in the output
            if hasattr(source_field, "bmdi"):
                mdi = source_field.bmdi
                mask = (data == mdi)
                data_out[mask] = mdi
            return data_out

    exp_operator = ExponentOperator(3)

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lbhr == 12:
            ff.fields[ifield] = exp_operator(field)

    ff.to_file("OutputFile")

.. Note::

    * There aren't any built-in operators in `mule.operators` which provide 
      this functionality, so this example creates a custom operator.
    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required forecast time; note that since 
      only fields with valid header release numbers define `lbhr` it is 
      important that the `if` conditions for these appear after the check 
      on `lbrel`.
    * Since the packing code (`lbpack`) of the modified fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy - in some cases this might not be suitable so you may need to 
      consider whether to update the value of `lbpack` on each field before 
      appending it to the file (or inside the operator's `new_field` method).
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 4: Remove negative specific humidities (STASH code 10)
--------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import HardLimitOperator

    neg_to_zero_operator = HardLimitOperator(lower_limit=0.0)

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lbuser4 == 10:
            ff.fields[ifield] = neg_to_zero_operator(field)

    ff.to_file("OutputFile")

.. Note::

    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required STASH code; note that since 
      only fields with valid header release numbers define `lbuser4` it is 
      important that the `if` conditions for these appear after the check 
      on `lbrel`.


Example 5: Set all level-38 fields to -1
----------------------------------------

.. code-block:: python

    import mule
    from mule.operators import ScaleFactorOperator, AddScalarOperator

    zero_operator = ScaleFactorOperator(0.0)
    subtract_one_operator = AddScalarOperator(-1.0) 

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lblev == 38:
            ff.fields[ifield] = (
                subtract_one_operator(zero_operator(field)))

    ff.to_file("OutputFile")

.. Note::

    * There isn't a single built-in operator in `mule.operators` which 
      provides this functionality, but it can be achieved by combining the
      effects of 2 operators - note the way in which they can be "chained"
      together to apply multiple operations.
    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required level; note that since only 
      fields with valid header release numbers define `lblev` it is important 
      that the `if` conditions for these appear after the check on `lbrel`.
    * Since the packing code (`lbpack`) of the modified fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy - in some cases this might not be suitable so you may need to 
      consider whether to update the value of `lbpack` on each field before 
      appending it to the file (or inside the operator's `new_field` method).
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 6: Set all level-38 32 bit packed (LBPACK 21 = 2) fields to -1
----------------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import ScaleFactorOperator, AddScalarOperator

    zero_operator = ScaleFactorOperator(0.0)
    subtract_one_operator = AddScalarOperator(-1.0) 

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lblev == 38 and field.lbpack == 2:
            ff.fields[ifield] = (
                subtract_one_operator(zero_operator(field)))

    ff.to_file("OutputFile")

.. Note::

    * There isn't a single built-in operator in `mule.operators` which 
      provides this functionality, but it can be achieved by combining the
      effects of 2 operators - note the way in which they can be "chained"
      together to apply multiple operations.
    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required level; note that since only 
      fields with valid header release numbers define `lblev` and `lbpack` it 
      is important that the `if` conditions for these appear after the check 
      on `lbrel`.
    * It is common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 7: Add random perturbations at the level of the least significant bit to all theta fields (STASH code 4)
----------------------------------------------------------------------------------------------------------------

.. code-block:: python

    import sys
    import mule
    import numpy as np

    EPSILON = sys.float_info.epsilon

    class LSBPerturbOperator(mule.DataOperator):
        """Operator which adds LSB perturbations to a field"""
        def __init__(self):
            pass
        def new_field(self, source_field):
            """Creates the new field object"""
            field = source_field.copy()
            return field
        def transform(self, source_field, new_field):
            """Performs the data manipulation"""
            data = source_field.get_data()
            # Create an array of perturbations and apply them to the data
            random_numbers = (2.0*np.random.random(data.shape) - 1.0)*EPSILON
            data_out = data + data*random_numbers
            # If the field defines MDI, reset missing points from original
            # field back to MDI in the output
            if hasattr(source_field, "bmdi"):
                mdi = source_field.bmdi
                mask = (data == mdi)
                data_out[mask] = mdi
            return data_out

    lsb_perturb_operator = LSBPerturbOperator()

    ff = mule.FieldsFile.from_file("InputFile")

    for ifield, field in enumerate(ff.fields):
        if field.lbrel in (2,3) and field.lbuser4 == 4:
            ff.fields[ifield] = lsb_perturb_operator(field)

    ff.to_file("OutputFile")

.. Note::

    * There aren't any built-in operators in `mule.operators` which provide 
      this functionality, so this example creates a custom operator.
    * Unlike example 1 - this example modifies the fields in the file object 
      in-place; this is neater but overwrites the point of access to the 
      original fields so might not always be ideal.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required STASH code; note that since 
      only fields with valid header release numbers define `lbuser4` it is 
      important that the `if` conditions for these appear after the check 
      on `lbrel`.
    * Since the packing code (`lbpack`) of the modified fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy - in some cases this might not be suitable so you may need to 
      consider whether to update the value of `lbpack` on each field before 
      appending it to the file (or inside the operator's `new_field` method).
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).


Example 8: Add 1.0 to fields with Item Numbers 2 or 3, only outputting fields operated on
-----------------------------------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import AddScalarOperator

    add_1_operator = AddScalarOperator(1.0)

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    for field in ff.fields:
        if field.lbrel in (2,3) and field.lbuser4 in (2,3):
            ff_out.fields.append(add_1_operator(field))

    ff_out.to_file("OutputFile")

.. Note::

    * Unlike many of the other examples, this example makes a copy of the
      original object - this allows only the desired fields to be added and
      hence written out.
    * Notice the check on `lbrel` - this is to make sure only fields with
      valid header release numbers are processed.
    * The loop also filters for the required STASH codes; note that since 
      only fields with valid header release numbers define `lbuser4` it is 
      important that the `if` conditions for these appear after the check 
      on `lbrel`.
    * It is common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required (or do it
      inside the operator's `new_field` method).

