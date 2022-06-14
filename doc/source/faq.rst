Frequently Asked Questions (FAQ)
================================

My dataset produces *Global encoding WKT flag not set for point format 6 - 10*
------------------------------------------------------------------------------

This means that your dataset is not conform to the LAS 1.4 specification,
which requires datasets that use the latest point formats (6 - 10) to also
specify the CRS in WKT. Previous versions of PDAL processed these files
nevertheless, but throwing in error is correct according to the format specification.

If you are affected by this error, you should look into fixing your dataset.
This can e.g. be done using this LASTools command:

.. code::

    las2las -i <input> -o <output> -epsg <code>

Additionally, you might want to report bugs to tools that produce this type
of non-conforming LAS files.
