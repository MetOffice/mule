Examples: Filtering
===================

Example 1: Extract theta (STASH code 4) and pressure fields (STASH code 407) into a separate fieldsfile
-------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    for field in ff.fields:
        if field.lbrel in (2,3) and field.lbuser4 in (4,407):
            ff_out.fields.append(field)

    ff_out.to_file("OutputFile")


.. Note::
    
    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named attributes, so this check must come before
      the check on `lbuser4` to avoid errors.
    * In this case you could have instead used the `hasattr` function to look 
      for the presence of `lbuser4` directly, as an alternative.


Example 2: Remove all fields valid at 12Z
-----------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    for field in list(ff.fields):
        if field.lbrel in (2,3) and field.lbhrd == 12:
            ff.fields.remove(field)

    ff.to_file("OutputFile")

.. Note::
    
    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named attributes, so this check must come before
      the check on `lbhrd` to avoid errors.
    * In this case you could have instead used the `hasattr` function to look 
      for the presence of `lbhrd` directly, as an alternative.


Example 3: Extract field numbers 3, 5 and 8
-------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    # Remember Python uses 0-based indices for lists
    ff_out.fields = [ff.fields[i-1] for i in [3,5,8]]

    ff_out.to_file("OutputFile")


Example 4: Extract all 32 bit packed fields (LBPACK = 2) which have been unprocessed (LBPROC = 0)
-------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    for field in ff.fields:
        if field.lbrel in (2,3) and field.lbpack == 2 and field.lbproc == 0:
            ff_out.fields.append(field)

    ff_out.to_file("OutputFile")

.. Note::
    
    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named attributes, so this check must come before
      the checks on `lbpack` and `lbproc` to avoid errors.

Example 5: Extract 38-level fields with STASH code 2, 3 and 4. The fields have to be 32 bit packed (LBPACK = 2) and unprocessed (LBPROC = 0) for STASH code 2 and 4
-------------------------------------------------------------------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    ff_out = ff.copy()

    for field in ff.fields:
        if field.lbrel in (2,3) and field.lblev == 38:
            if field.lbuser4 in (2,4) and field.lbpack == 2 and field.lbproc == 0:
                ff_out.fields.append(field)
            elif field.lbuser4 == 3:
                ff_out.fields.append(field)

    ff_out.to_file("OutputFile")

.. Note::
    
    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named attributes, so this check must come before
      the checks on `lblev`, `lbuser4`, etc. to avoid errors.
