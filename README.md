# Welcome to the Adaptive Filtering Wizard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/ssciwr/afwizard/ci.yml?branch=main)](https://github.com/ssciwr/afwizard/actions/workflow/ci.yml)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/afwizard.svg)](https://anaconda.org/conda-forge/afwizard)
[![codecov](https://codecov.io/gh/ssciwr/afwizard/branch/main/graph/badge.svg?token=ONIG38R74Y)](https://codecov.io/gh/ssciwr/afwizard)
[![Documentation Status](https://readthedocs.org/projects/afwizard/badge/)](https://afwizard.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ssciwr/afwizard/main)

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

* A [Conda installation](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)

If you want to use the respective backends, you also need to install the following pieces of software:

* [OPALS](https://opals.geo.tuwien.ac.at/html/stable/index.html) in version 2.5
* [LASTools](https://rapidlasso.com/)

## Installing and using

### Using Conda

Having a [local installation of Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html), the following sequence of commands sets up a new Conda environment and installs `afwizard` into it:

```
conda create -n afwizard
conda activate afwizard
conda install -c conda-forge afwizard
```

You can start the JupyterLab frontend by doing:

```
conda activate afwizard
jupyter lab
```

If you need some example notebooks to get started, you can copy them into the current working directory like this:

```
conda activate afwizard
copy_afwizard_notebooks
```

### Development Build

If you are intending to contribute to the development of the library, we recommend the following setup:

```
git clone https://github.com/ssciwr/afwizard.git
cd afwizard
conda env create -f environment-dev.yml --force
conda run -n afwizard-dev python -m pip install --no-deps .
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

## Citation - How to cite AFwizard

The following scientific article can be referenced when using AFwizard in your research.

- Doneus, M., Höfle, B., Kempf, D., Daskalakis, G. & Shinoto, M. (2022): Human-in-the-loop development of spatially adaptive ground point filtering pipelines — An archaeological case study. _Archaeological Prospection_. Vol. 29 (4), pp. 503-524.  DOI: [https://doi.org/10.1002/arp.1873](https://doi.org/10.1002/arp.1873)

Related Bibtex entry:
```
@Article{Doneus_2022,
  author  = {Michael Doneus and Bernhard H\"ofle and Dominic Kempf and Gwydion Daskalakis and Maria Shinoto},
  title   = {Human-in-the-loop development of spatially adaptive ground point filtering pipelines {\textemdash} An archaeological case study},
  journal = {Archaeological Prospection},
  year    = {2022},
  volume  = {29},
  number  = {4},
  pages   = {503--524},
  doi     = {10.1002/arp.1873},
  url     = {https://doi.org/10.1002/arp.1873} }
```

The data from the Nakadake Sanroku Kiln Site Center in Japan used in above article is also accessible under CC-BY-SA 4.0 in the [data repository of the 3D Spatial Data Processing Group](https://heidata.uni-heidelberg.de/dataverse/3dgeo):

```
@data{data/TJNQZG_2022,
  author    = {Shinoto, Maria and Doneus, Michael and Haijima, Hideyuki and Weiser, Hannah and Zahs, Vivien and Kempf, Dominic and Daskalakis, Gwydion and Höfle, Bernhard and Nakamura, Naoko},
  publisher = {heiDATA},
  title     = {{3D Point Cloud from Nakadake Sanroku Kiln Site Center, Japan: Sample Data for the Application of Adaptive Filtering with the AFwizard}},
  year      = {2022},
  version   = {V2},
  doi       = {10.11588/data/TJNQZG},
  url       = {https://doi.org/10.11588/data/TJNQZG}
}
```

## Troubleshooting

If you run into problems using AFwizard, we kindly ask you to do the following in this order:

* Have a look at the list of our [Frequently Asked Questions](https://afwizard.readthedocs.io/en/latest/faq.html) for a solution
* Search through the [GitHub issue tracker](https://github.com/ssciwr/afwizard/issues)
* Open a new issue on the [GitHub issue tracker](https://github.com/ssciwr/afwizard/issues) providing
  * The version of `afwizard` used
  * Information about your OS
  * The output of `conda list` on your machine
  * As much information as possible about how to reproduce the bug
  * If you can share the data that produced the error, it is much appreciated.
