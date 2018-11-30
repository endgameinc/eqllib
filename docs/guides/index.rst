======================================
Getting Started
======================================

The EQL library current supports Python 2.7 and 3.5 - 3.7. Assuming a supported Python version is installed, run the command:

.. code-block:: console

    $ git clone https://github.com/endgameinc/eqllib
    $ cd eqllib
    $ python setup.py install

If Python is configured and already in the PATH, then ``eqllib`` will be readily available, and can be checked by running the command:

.. code-block:: console

    $ eqllib -h
    usage: eqllib [-h] {convert-query,convert-data,query,survey} ...

    EQL Analytics

    positional arguments:
      {convert-query,convert-data,query,survey}
                            Sub Command Help
        convert-query       Convert a query to specific data source
        convert-data        Convert data from a specific data source
        query               Query over a data source
        survey              Run multiple analytics over JSON data

.. toctree::
   :maxdepth: 2
   :caption: Contents

   cli
   sysmon