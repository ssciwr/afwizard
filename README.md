# Welcome to the Adaptive Filtering Wizard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ssciwr/afwizard/CI)](https://github.com/ssciwr/afwizard/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/ssciwr/afwizard/branch/main/graph/badge.svg?token=ONIG38R74Y)](https://codecov.io/gh/ssciwr/afwizard)
[![Documentation Status](https://readthedocs.org/projects/afwizard/badge/)](https://afwizard.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ssciwr/afwizard/main)

**This library is currently under development.**

## Features

AFwizard is a Python package to enhance the productivity of ground point filtering workflows in archaeology and beyond.
It provides a Jupyter-based environment for "human-in-the-loop" tuned, spatially heterogeneous ground point filterings.
Core features:

* Working with Lidar datasets directly in Jupyter notebooks
  * Loading/Storing of LAS/LAZ files
  * Visualization using hillshade models and slope maps
  * Applying of ground point filtering algorithms
  * Cropping with a map-based user interface
* Accessibility of existing filtering algorithms under a unified data model:
  * [PDAL](https://pdal.io/): The Point Data Abstraction Library is an open source library for point cloud processing.
  * [OPALS](https://opals.geo.tuwien.ac.at/html/stable/index.html) is a proprietary library for processing Lidar data. It can be tested freely for datasets <1M points.
  * [LASTools](https://rapidlasso.com/) has a proprietary tool called `lasground_new` that can be used for ground point filtering.
* Access to predefined filter pipeline settings
  * Crowd-sourced library of filter pipelines at https://github.com/ssciwr/afwizard-library/
  * Filter definitions can be shared with colleagues as files
* Spatially heterogeneous application of filter pipelines
  * Assignment of filter pipeline settings to spatial subregions in map-based user interface
  * Command Line Interface for large scale application of filter pipelines

## Documentation

The documentation of AFwizard can be found here: [https://afwizard.readthedocs.io/en/latest](https://afwizard.readthedocs.io/en/latest)

## Prerequisites

In order to work with AFwizard, you need the following required pieces of Software.

* Python >= 3.7
* A [Conda installation](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)

If you want to use the respective backends, you also need to install the following pieces of software:

* [OPALS](https://opals.geo.tuwien.ac.at/html/stable/index.html) in the latest (nightly) version that contains the `TerrainFilter` module.
* [LASTools](https://rapidlasso.com/)

There are alternatives to Conda for installation, but we strongly advise you to use Conda as it offers the best experience for this type of project.

## Installing and using

### Using Conda

Having a [local installation of Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html), the following sequence of commands sets up a Conda environment for `afwizard`:

```
git clone https://github.com/ssciwr/afwizard.git
cd afwizard
conda env create -f environment.yml --force
conda run -n afwizard python -m pip install .
```

You can start the JupyterLab frontend by doing:

```
conda activate afwizard
jupyter lab
```

### Using Binder

You can try AFwizard without prior installation by using [Binder](https://mybinder.org/v2/gh/ssciwr/afwizard/main), which is a free cloud-hosted service to run Jupyter notebooks. This will give you an impression of the library's capabilities, but you will want to work on a local setup when using the library productively: On Binder, you might experience very long startup times, slow user experience and limitations to disk space and memory.

### Using Docker

Having set up [Docker](https://docs.docker.com/get-docker/), you can use AFwizard directly from a provided Docker image:

```
docker run -t -p 8888:8888 ssciwr/afwizard:latest
```

Having executed above command, paste the URL given on the command line into your browser and start using AFwizard by looking at the provided Jupyter notebooks.
This image is limited to working with non-proprietary filtering backends (PDAL only).

### Using Pip

We advise you to use Conda as AFwizard depends on a lot of other Python packages, some of which have external C/C++ dependencies. Using Conda, you get all of these installed automatically, using pip you might need to do a lot of manual work to get the same result.

That being said, `afwizard` can be installed from PyPI:

```
python -m pip install afwizard
```
