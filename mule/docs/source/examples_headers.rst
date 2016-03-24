Examples: Manipulating Headers
==============================

Example 1: Change the data time in the fixed header to 12:00 01/02/03
---------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    ff.fixed_length_header.t1_year = 2003
    ff.fixed_length_header.t1_month = 2
    ff.fixed_length_header.t1_day = 1
    ff.fixed_length_header.t1_hour = 12
    ff.fixed_length_header.t1_minute = 0

    ff.to_file("OutputFile")

.. Note::
    
    *  You could instead choose to refer to the indices of the raw array (e.g. 
       `ff.fixed_length_header.raw[21] = 2003`, etc.) though the form above is 
       preferable (more readable).


Example 2: Change the forecast time (lbft) in the 3rd lookup header to 12
-------------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")
    ff.fields[2].lbft = 12
    ff.to_file("OutputFile")

.. Note::
    
    * You could instead choose to refer to the indices of the raw array (e.g. 
      `ff.fields[2].raw[14] = 12`) though the named form is preferable (more 
      readable).

    * In this example we are assuming that the 2nd field in the file has a
      valid header release number (`lbrel == 2 or 3`); if it didn't then it may
      not have an `lbft` attribute.


Example 3: Change the validity time in all lookup headers to 12:00 01/02/03
---------------------------------------------------------------------------

.. code-block:: python

    import mule

    ff = mule.FieldsFile.from_file("InputFile")

    for field in ff.fields:
        if field.lbrel in (2,3):
            field.lbyr = 2003
            field.lbmon = 2
            field.lbdat = 1
            field.lbhr = 12
            field.lbmin = 0

    ff.to_file("OutputFile")

.. Note::

    * You could instead choose to refer to the indices of the raw array (e.g. 
      `field.raw[1] = 2003`) though the named form is preferable (more readable).

    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named lookup attributes (`lbyr`, `lbmon`, etc.) so 
      ignore other field types to avoid problems (good practice).


Example 4: Round the validity time in all lookup headers to the nearest hour
----------------------------------------------------------------------------

.. code-block:: python

    import mule
    from datetime import datetime, timedelta

    ff = mule.FieldsFile.from_file("InputFile")

    for field in ff.fields:
        if field.lbrel in (2,3):
            # Create a datetime object (handles date incrementing logic)
            field_date = datetime(
                field.lbyr, field.lbmon, field.lbdat, field.lbhr, field.lbmin)
            # Create and apply a timedelta to take the time to the nearest hour
            if field_date.minute >= 30:
                incr_seconds = (60 - field_date.minute)*60
                field_date += timedelta(seconds=incr_seconds)
            else:
                incr_seconds = field_date.minute*60
                field_date -= timedelta(seconds=incr_seconds)
            # Now extract the components again to set the lookup values
            field.lbyr = field_date.year
            field.lbmon = field_date.month
            field.lbdat = field_date.day
            field.lbhr = field_date.hour
            field.lbmin = field_date.minute

    ff.to_file("OutputFile")

.. Note::

    * You could instead choose to refer to the indices of the raw array (e.g. 
      `field.raw[1] = field_date.year`) though the named form is preferable 
      (more readable).

    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named lookup attributes (`lbyr`, `lbmon`, etc.) so 
      ignore other field types to avoid problems (good practice).

    * This example uses the Python `datetime` library, which should be treated
      with some caution (its timezone support is not particularly robust) - a
      possible alternative would be the isodatetime_ module.


Example 5: Change the data time in all lookup headers to 12:00 01/02/03 and reset forecast hour to match
--------------------------------------------------------------------------------------------------------

.. code-block:: python

    import mule
    from datetime import datetime, timedelta

    ff = mule.FieldsFile.from_file("InputFile")

    # Create a datetime object at the reference time
    field_data_t_new = datetime(2003, 2, 1, 12, 0)

    for field in ff.fields:
        if field.lbrel in (2,3):
            # Create a datetime object (handles date incrementing logic)
            field_data_t = datetime(
                field.lbyrd, field.lbmond, field.lbdatd, field.lbhrd, field.lbmind)
            # The datetime objects will return a timedelta object when subtracted
            data_t_delta = field_data_t_new - field_data_t
            # Convert this delta to whole hours (truncated)
            data_t_delta_hours = data_t_delta.days*24.0 + data_t_delta.seconds//3600
            # Set the lookup values
            field.lbyrd = field_data_t_new.year
            field.lbmond = field_data_t_new.month
            field.lbdatd = field_data_t_new.day
            field.lbhrd = field_data_t_new.hour
            field.lbmind = field_data_t_new.minute
            # Adjust the forecast time by the amount calculated above
            field.lbft += data_t_delta_hours

    ff.to_file("OutputFile")

.. Note::

    * You could instead choose to refer to the indices of the raw array (e.g. 
      `fields.raw[1] = field_date.year`) though the named form is preferable 
      (more readable).

    * Notice the check on `lbrel` - only fields with a valid release number will
      correctly support all named lookup attributes (`lbyrd`, `lbmond`, etc.) so 
      ignore other field types to avoid problems (good practice).

    * This example uses the Python `datetime` library, which should be treated
      with some caution (its timezone support is not particularly robust) - a
      possible alternative would be the isodatetime_ module.

.. _isodatetime: https://github.com/metomi/isodatetime
