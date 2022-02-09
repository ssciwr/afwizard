Executing adaptive filter pipelines
===================================

Once you have completed the work of creating a segmentation for
your dataset and choosing the appropriate filter settings for your
terrain type, you might want to apply your filter to the entire dataset.
This step can be done in two ways: Either through the Python API or
more conveniently through a command line interface.

.. click:: adaptivefiltering.__main__:main
   :prog: adaptivefiltering

Python API
----------

.. autofunction:: adaptivefiltering.execute.apply_adaptive_pipeline
