Examples: Operations with multiple fields as input
==================================================

Example 1: Subtract fields in InputFile2 from corresponding fields in InputFile1
--------------------------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import SubtractFieldsOperator

    subtract_operator = SubtractFieldsOperator()

    ff1 = mule.FieldsFile.from_file("InputFile1")
    ff2 = mule.FieldsFile.from_file("InputFile2")

    ff_out = ff1.copy()

    for field_1 in ff1.fields:
        if field_1.lbrel in (2,3) and field_1.lbuser4 != 30:
            for field_2 in list(ff2.fields):
                if field_2.lbrel not in (2,3):
                    ff2.fields.remove(field_2)
                    continue
                elif ((field_1.lbuser4 == field_2.lbuser4) and
                      (field_1.lbft == field_2.lbft) and
                      (field_1.lblev == field_2.lblev)):
                    ff_out.fields.append(subtract_operator([field_1, field_2]))
                    ff2.fields.remove(field_2)
                    break
            else:
                ff_out.fields.append(field_1)
        else:
            ff_out.fields.append(field_1)

    ff_out.to_file("OutputFile")

.. Note::

    * Like the single field operators, the multi-field operators will handle
      missing points sensibly - by default any points in the fields being
      subtracted which are MDI will remain MDI in the result (though this can
      be configured).
    * Notice the outer-loop check on `lbrel` and `lbuser4` - this is to make 
      sure only fields with valid header release numbers are considered, and
      to avoid processing the land-sea mask (STASH code `30`).
    * Note the use of the `list` command on the inner-loop argument; this is
      to ensure a copy of the field list is made to loop over, because fields
      from file 2 which are matched (or ignored) are removed from the original
      inside the loop (to gradually reduce the number of comparisons on each 
      pass of the outer-loop).
    * The inner-loop starts with a similar check to ignore any fields from
      file 2 which don't have a valid `lbrel` header release.
    * After this the inner-loop must determine what constitutes a "matching 
      field"; in this case a field with the same STASH code, level index and 
      forecast time is considered a match.
    * Note the first `else` statement, which is not an alignment mistake!
      It really is part of the `for` loop; it will be executed only if the loop
      reaches the end normally (which in this case will be if no match was
      found).  See `this section of the Python docs
      <https://docs.python.org/2/tutorial/controlflow.html#break-and-continue-statements-and-else-clauses-on-loops>`_
      for more details.
    * The two `else` clauses are ensuring that any field from file 1 which has
      no match in file 2 is written unaltered to the output file.  If these 
      clauses are removed the output file will only contain fields which are
      the matched differences between the two files.
    * Since the packing code (`lbpack`) of the difference fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy as the first input field - in some cases this might not be 
      suitable so you may need to consider whether to update the value of 
      `lbpack` on each difference field before appending it to the file.
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required.

.. _Python docs: 

Example 2: Add pressure (STASH code 407) and level-3 exner (STASH code 255) fields in InputFile2 to corresponding fields in InputFile1 
--------------------------------------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import AddFieldsOperator

    add_operator = AddFieldsOperator()

    ff1 = mule.FieldsFile.from_file("InputFile1")
    ff2 = mule.FieldsFile.from_file("InputFile2")

    ff_out = ff1.copy()

    for field_1 in ff1.fields:
        if (field_1.lbrel in (2,3) and field_1.lbuser4 == 407 or
            (field_1.lbuser4 == 255 and field_1.lblev == 3)):
            for field_2 in list(ff2.fields):
                if field_2.lbrel not in (2,3):
                    ff2.fields.remove(field_2)
                    continue
                elif ((field_1.lbuser4 == field_2.lbuser4) and
                      (field_1.lbft == field_2.lbft) and
                      (field_1.lblev == field_2.lblev)):
                    ff_out.fields.append(add_operator([field_1, field_2]))
                    ff2.fields.remove(field_2)
                    break
            else:
                ff_out.fields.append(field_1)
        else:
            ff_out.fields.append(field_1)

    ff_out.to_file("OutputFile")

.. Note::

    * Like the single field operators, the multi-field operators will handle
      missing points sensibly - by default any points in the fields being
      subtracted which are MDI will remain MDI in the result (though this can
      be configured).
    * Notice the outer-loop check on `lbrel`, `lbuser4` and `lblev` - this is 
      to make sure only fields with valid header release numbers are 
      considered, and to restrict processing to the desired fields.
    * Note the use of the `list` command on the inner-loop argument; this is
      to ensure a copy of the field list is made to loop over, because fields
      from file 2 which are matched (or ignored) are removed from the orginal
      inside the loop (to gradually reduce the number of comparisons on each 
      pass of the outer-loop).
    * The inner-loop starts with a similar check to ignore any fields from
      file 2 which don't have a valid `lbrel` header release.
    * After this the inner-loop must determine what constitutes a "matching 
      field"; in this case a field with the same STASH code, level index and 
      forecast time is considered a match.
    * Note the first `else` statement, which is not an alignment mistake!
      It really is part of the `for` loop; it will be executed only if the loop
      reaches the end normally (which in this case will be if no match was
      found).
    * The two `else` clauses are ensuring that any field from file 1 which has
      no match in file 2 is written unaltered to the output file.  If these 
      clauses are removed the output file will only contain fields which are
      the matched differences between the two files.
    * Since the packing code (`lbpack`) of the difference fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy as the first input field - in some cases this might not be 
      suitable so you may need to consider whether to update the value of 
      `lbpack` on each difference field before appending it to the file.
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required.

Example 3: Perform a weighted mean of corresponding fields in InputFile1 and InputFile2, giving double weight to the fields in InputFile1
-----------------------------------------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule

    class WeightedMeanOperator(mule.DataOperator):
        """Operator which calculates a weighted mean between 2 fields"""
        def __init__(self, weighting):
            """Initialise operator, passing the weight for the 2nd field"""
            self.weighting = weighting
        def new_field(self, field_list):
            """Creates the new field object""" 
            field = field_list[0].copy()
            return field
        def transform(self, field_list, new_field):
            """Performs the data manipulation"""
            data1 = field_list[0].get_data()
            data2 = field_list[1].get_data()
            data_out = (data1 + self.weighting*data2)/(self.weighting + 1)

            # If the first field defines MDI, reset missing points from 
            # either of the original fields back to MDI in the output
            if hasattr(field_list[0], "bmdi"):
                mdi = field_list[0].bmdi
                mask1 = (data1 == mdi)
                mask2 = (data2 == mdi)
                data_out[mask1] = mdi
                data_out[mask2] = mdi

            return data_out

    mean_w2_operator = WeightedMeanOperator(2.0)

    ff1 = mule.FieldsFile.from_file("InputFile1")
    ff2 = mule.FieldsFile.from_file("InputFile2")

    ff_out = ff1.copy()

    for field_1 in ff1.fields:
        if field_1.lbrel not in (2,3):
            continue
        for field_2 in list(ff2.fields):
            if field_2.lblrel not in (2,3):
                ff2.fields.remove(field_2)
                break
            elif ((field_1.lbuser4 == field_2.lbuser4) and
                  (field_1.lbft == field_2.lbft) and
                  (field_1.lblev == field_2.lblev)):
                ff_out.fields.append(mean_w2_operator([field_1, field_2]))
                ff2.fields.remove(field_2)
                break

    ff_out.to_file("OutputFile")

.. Note::

    * There aren't any built-in operators in `mule.operators` which provide 
      this functionality, so this example creates a custom operator.
    * The operator is designed to handle MDI sensibly - any points in either
      input field which are MDI will remain MDI in the result.
    * Notice the outer-loop check on `lbrel` - this is to make sure only 
      fields with valid header release numbers are considered, and to restrict 
      processing to the desired fields.
    * Note the use of the `list` command on the inner-loop argument; this is
      to ensure a copy of the field list is made to loop over, because fields
      from file 2 which are matched are removed from the orginal inside the 
      loop (to gradually reduce the number of comparisons on each pass of the 
      outer-loop).
    * The inner-loop starts with a similar check to ignore any fields from
      file 2 which don't have a valid `lbrel` header release.
    * After this the inner-loop must determine what constitutes a "matching 
      field"; in this case a field with the same STASH code, level index and 
      forecast time is considered a match.
    * This example only outputs the matched fields; see examples 1 and 2 for
      the method to output all fields.
    * Since the packing code (`lbpack`) of the averaged fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy as the first input field - in some cases this might not be 
      suitable so you may need to consider whether to update the value of 
      `lbpack` on each difference field before appending it to the file.
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required.


Example 4: Add QCF (STASH code 12), QCL (STASH code 254) and Q (STASH code 10) fields from 3 separate files
-----------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule
    from mule.operators import AddFieldsOperator

    add_operator = AddFieldsOperator()

    ff1 = mule.FieldsFile.from_file("InputFile1")
    ff2 = mule.FieldsFile.from_file("InputFile2")
    ff3 = mule.FieldsFile.from_file("InputFile3")

    ff_out = ff1.copy()

    for field_1 in ff1.fields:
        qcl_field = None
        q_field = None
        if field_1.lbrel in (2,3) and field_1.lbuser4 == 12:
            for field_2 in ff2.fields:
                if ((field_2.lbrel in (2,3)) and
                    (field_2.lbuser4 == 254) and
                    (field_1.lbft == field_2.lbft) and
                    (field_1.lblev == field_2.lblev)):
                        qcl_field = field_2
                        ff2.fields.remove(field_2)
                        break

            for field_3 in ff3.fields:
                if ((field_3.lbrel in (2,3)) and
                    (field_3.lbuser4 == 10) and
                    (field_1.lbft == field_3.lbft) and
                    (field_1.lblev == field_3.lblev)):
                        q_field = field_3
                        ff3.fields.remove(field_3)
                        break

            if qcl_field is not None and q_field is not None:
                new_field = add_operator([field_1, qcl_field, q_field])
                new_field.lbuser4 = 18001
                ff_out.fields.append(new_field)
                continue
            

    ff_out.to_file("OutputFile")

.. Note::

    * Like the single field operators, the multi-field operators will handle
      missing points sensibly - by default any points in the fields being
      subtracted which are MDI will remain MDI in the result (though this can
      be configured).
    * Notice the outer-loop check on `lbrel` and `lbuser4` - this is to make 
      sure only fields with valid header release numbers are considered, and 
      to restrict processing to the desired fields.
    * A pair of variables are used to capture references to the 2 required
      fields that need to be added to the field from file 1; the code which
      executes the operator will only run if both matching fields are found.
    * The inner-loops start with a similar check to ignore any fields from
      files 2 and 3 which don't have a valid `lbrel` header release, and to 
      match the desired STASH codes.
    * After this the inner-loops must determine what constitutes a "matching 
      field"; in this case a field with the same level index and forecast time 
      is considered a match.
    * This example only outputs the matched fields; see examples 1 and 2 for
      a method to output all fields.
    * Since the packing code (`lbpack`) of the summed fields is not changed
      Mule will try to write the fields out with the same packing method and
      accuracy as the first input field - in some cases this might not be 
      suitable so you may need to consider whether to update the value of 
      `lbpack` on each difference field before appending it to the file.
    * It is also common practice to update the `lbproc` value of the field's
      lookup header when the data has been modified (some applications use
      this to determine certain types of field) - you should update this value
      before appending the modified fields to the file if required.
