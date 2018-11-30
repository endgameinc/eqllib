==================================
``eqllib`` Command-Line Interface
==================================
The EQL Analytics Library comes with a utility that can search, normalize, and survey JSON data.
See :doc:`index` for instructions on installing ``eqllib`` locally.


convert-data
-------------
**eqllib** *convert-data* [*OPTIONS*] <*input-json-file*> <*output-json-file*>

The :program:`convert-data` command normalizes data, generating a new JSON file that matches the schema.

.. note::
    Be aware, that if you attempt to convert data which does not match the specified format, there will be an error. For instance, if data is converted from Sysmon but is missing the UtcTime field, an exception will be raised.

    .. code-block:: console

       $ eqllib convert-data -s "Microsoft Sysmon" non-sysmon-data.json output.json
       Traceback (most recent call last):
        ...

             File "eqllib/normalization.py", line 285, in normalize_callback
               ts = data[self.time_field]
           KeyError: u'UtcTime'


Arguments
^^^^^^^^^
.. program:: convert-data

.. option:: input-json-file

    Path to a JSON file of unnormalized events.

.. option:: output-json-file

    Path to an output JSON file to store normalized events.


Options
^^^^^^^
.. program:: convert-data

.. option:: -h

    Show the help message and exit

.. option:: -s <data-source>

    Required: the source schema for the events. (e.g. ``"Microsoft Sysmon"``)

.. option:: -e <encoding>

    Source file encoding. (e.g. ``ascii``, ``utf8``, ``utf16``, etc.)


convert-query
-------------
**eqllib** *convert-query* [*OPTIONS*] <*eql-query*>

The :program:`convert-query` command takes an EQL query that matches a normalized schema,
and will print out the query converted to match a different schema.


Arguments
^^^^^^^^^
.. program:: convert-query

.. option:: eql-query

    Input EQL query written for the normalization schema


Options
^^^^^^^
.. program:: convert-query

.. option:: -h

    Show the help message and exit

.. option:: -s <data-source>

    Required: the target schema to convert the query into.


query
-----
The :program:`query` command reads JSON events and print matching output events back as JSON.
Unless specified with :option:`-s`, data is assumed to already be normalized against the schema.

**eqllib** *query* [*OPTIONS*] <*input-query*> <*json-file*>



Arguments
^^^^^^^^^
.. program:: query

.. option:: input-query

    Query in EQL syntax that matches the common schema.

.. option:: json-file

    Path to a JSON file of normalized or unnormalized events.


Options
^^^^^^^
.. program:: query

.. option:: -h

    Show the help message and exit

.. option:: -s <data-source>

    Specify the source schema for the events. (e.g. ``"Microsoft Sysmon"``)

.. option:: -e <encoding>

    Source file encoding. (e.g. ``ascii``, ``utf8``, ``utf16``, etc.)


survey
------
**eqllib** *survey* [*OPTIONS*] <*json-file*> <*analytic-path*> [*analytic-path*, ...]

The :program:`survey` command can be used to run multiple analytics against a single JSON file.
Unless specified with :option:`-s`, data is assumed to already be normalized against the schema.


Arguments
^^^^^^^^^
.. program:: survey

.. option:: json-file

    Path to a JSON file of normalized or unnormalized events.


.. option:: analytic-path [analytic-path, ...]

    Path(s) to analytic TOML files or a directory of analytics.

Options
^^^^^^^
.. program:: survey

.. option:: -h

    Show the help message and exit

.. option:: -s <data-source>

    Specify the source schema for the events. (e.g. ``"Microsoft Sysmon"``)

.. option:: -e <encoding>

    Source file encoding. (e.g. ``ascii``, ``utf8``, ``utf16``, etc.)

.. option:: -c

    Output counts per analytic instead of the individual hits.


View usage for the related `EQL utility <https://eql.readthedocs.io/cli.html>`_.
