Quickstart
==========

This quickstart will guide you through the process of preparing
datasets, filters, and segments, and through the application of the
adaptive filtering library with sample data from the adaptive filtering
library. A more indepth workflow with alternative decisions and data can
be found in the workflow overview.

Prerequisits
------------

You have a conda installation, either Miniconda or Anaconda of version
ßß or higher installed (download, instructions) and you have downloaded
and installed the adaptive filtering libraries (see in workflow).

Data provided with the adaptive filtering library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  3D Point Cloud data (.las/.laz)

   -  The sample data are from the Gokuyama subregion of the Nakadake
      foothills in Southjapan (nakadake-gky.laz)

-  Segment data of the 3D point cloud data (GeoJSON)

   -  Segments are created according to specific characteristics of the
      subregion like vegetation or terrain and will be matched with
      certain filters and filter settings before running the adaptive
      filtering library (nakadake-gky.geojson).

-  Filter pipeline (JSON)

   -  The library provides the PDAL options for working with 3D data
      points for all users, these are OpenSource and applied in the
      Quickstart.

      -  Adaptive Filtering also works with the filter frameworks OPALS
         and LAStools, which are not fully OpenSource and are not used
         in the QuickStart.

   -  For the QuickStart, the adaptive filtering library ships with two
      filter pipelines that were set up for the sample 3D point cloud
      data; one that works with individual classification of the region
      (nakadake-gky-specific.json), the other with a generic
      classification according to terrain and vegetation
      (nakadake-gky-generic.json).

Workflow in the quickstart tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Quickstart introduces three simple workflows with data and options
that are delivered in this library.

(A) Applying prepared filterpipelines and segment matches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Load 3D point data ``nakadake-gky.laz``.

2. Load segment file ``nakadake-gky.geojson``.

3. Load Load filter pipeline ``nakadake-gky-generic.json``.

4. Match segment types with filter pipelines.

5. Run ``adaptive filtering`` in the terminal with the parameters set in
   steps 1 to 4.

(B) Create a variation of a filter pipeline and new segment matches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Load 3D point data ``nakadake-gky.laz``.

2. Load segment file ``nakadake-gky.geojson``.

3. Load Load filter pipeline ``nakadake-gky-generic.json``.

   1. Create variations of filter parameters.

   2. Store new filter settings as new filter pipeline
      ``nakadake-gky-generic.new.json``.

   3. Load new filter pipeline.

4. Match segment types with new filter pipelines.

5. Run ``adaptive filtering`` in the terminal with the parameters set in
   steps 1 to 4.

(C) Create a filter pipeline from scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Load 3D point data ``nakadake-gky.laz``.

   1. Restrict the region to a subregion of interest.

2. Create a filter pipeline that matches the subregion.

3. TODO / TO_UNDERSTAND:

   1. Either: Add this filter pipeline as a new setting to match a
      certain segment class in your segment GeoJSON file

   2. Or: Create a new filter pipeline with old settings and this new
      setting?

4. Match segment types with new filter pipelines.

5. Run ``adaptive filtering`` in the terminal with the parameters set in
   steps 1 to 4.

Quickstart tutorials
--------------------

Load the library
~~~~~~~~~~~~~~~~

Before starting a session, the ``adaptive filtering`` library has to be
loaded to the Conda environment. TODO shall we suggest to create a new
environment beside (base)?

.. code:: python

   import adaptivefiltering

Scenario A: Applying prepared filter pipelines and segment matches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use prepared data and settings and just to get the library running.

1. Load 3D point cloud with the command
   ``dataset = adaptivefiltering.DataSet(filename="nakadake-gky.laz")``.
