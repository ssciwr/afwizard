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

I changed the :code:`pipeline_title` field in my GeoJSON, but it has no effect
------------------------------------------------------------------------------

The :code:`pipeline_title` key is added to the GeoJSON file when using
:ref:`~afwizard.assign_pipeline` purely for informational purpose. AFwizard
draws all required information from hash stored in the :code:`pipeline` key.
This hash is determined from the filters metadata. This allows you to move
your filter pipelines freely without invalidating segmentation GeoJSONs (which
would be the case when storing paths) and to finetune filter pipelines after
creating the segmentation GeoJSON (which would not be possible if the GeoJSON
stored the full filter configuration).
