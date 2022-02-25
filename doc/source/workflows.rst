Overview of the workflows in adaptivefiltering
==============================================

The goal of adaptivefiltering is to provide a high productivity environment
for archaelogists and other researchers working with Lidar data to produce
high precision ground point filterings. To that end it implements an *adaptive*
approach that allows human-in-the-loop optimization of ground point filtering
algorithms. By adaptive we mean two things:

* Parameter Adaptivity: We allow interactive, human-in-the-loop finetuning of
  filtering algorithm parameters. Adaptivefiltering does not implement its own filtering
  algorithm, but instead provides access to a variety of established backends
  through a common interface (PDAL, OPALS, LASTools).
* Spatial Adaptivity: In order to produce high precision ground point filterings,
  parameters for filtering algorithms need to be spatially varied in order to choose
  the best algorithm for each terrain type. Adaptivefiltering manages this process
  in an interactive way.

adaptivefiltering is a Python library with deep integration into the Jupyter
ecosystem. Some familiarity with Python and Jupyter is useful when using it,
but the necessary skills can also be developed while using the library. In that
case you should start by reading our short `Introduction to Python + Jupyter`_.

The overall procedure when working with adaptivefiltering is described in the
following. This is at the same time an outline of the rest of this documentation.
Users are expected to have their own point cloud datasets acquired by airborne
laser scanning in LAS/LAZ format.

As Lidar datasets are typically be very large, the first important step is
to trim down the dataset to a region of interest which is expecting to be suitable
for filtering with one parameter set (because it e.g. contains the same terrain type)
and which is of a size that allows a truely interactive process (we recommend
e.g. 500k points). The handling and spatial restriction of datasets is described
in `Working with datasets`_.

Given such a dataset sample for a terrain type, the next step would be to choose and customize a
suitable filter pipeline from a number of available filter libraries. The concept of
filter libraries is explained in `Working with filter libraries`_. If you are new to
adaptivefiltering, you can leverage the existing crowd-sourced filter pipelines provided
with adaptivefiltering. The process of selecting and customizing the best filter pipeline
for your particular dataset sample is described in ..`Selecting a filter pipeline for a dataset`_.

If none of the provided filter pipelines matches your needs or you want to tune the
process even more, you can read about `Creating filter pipelines` yourself. You will
learn about the interactive process to define your own pipelines that combine the
strengths of the available filtering backends. If you found a filter pipeline that works
good for you, consider adding the required metadata and contribute it to the library of
crowd-sourced filters!

Once you know which filter pipelines you want to apply in which subregion of your dataset,
you should look into `Mapping filter pipelines to segmentations`_, which will explain you
how to add filter pipeline information to a GeoJSON file such that we can later generate
a digital elevation model for the entire dataset. You are expected to have created the
segmentation in e.g. a GIS and exported it as a GeoJSON file.

In a final step, the digital elevation model is generated. This is done from the command
line instead of through Jupyter, because you might want to consider doing this on a bigger
machine. The details about that are described in `Executing adaptive filter pipelines`_.

.. _Introduction to Python + Jupyter: python.nblink
.. _Working with datasets: datasets.nblink
.. _Working with filter libraries: libraries.nblink
.. _Selecting a filter pipeline for a dataset: selection.nblink
.. _Mapping filter pipelines to segmentations: segmentation.nblink
.. _Creating filter pipelines: filtering.ipynb
.. _Executing adaptive filter pipelines: execution