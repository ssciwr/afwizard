# Welcome to the Adaptive Ground Point Filtering Library

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ssciwr/adaptivefiltering/CI)](https://github.com/ssciwr/adaptivefiltering/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/ssciwr/adaptivefiltering/branch/main/graph/badge.svg?token=ONIG38R74Y)](https://codecov.io/gh/ssciwr/adaptivefiltering)
[![Documentation Status](https://readthedocs.org/projects/adaptivefiltering/badge/)](https://adaptivefiltering.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ssciwr/adaptivefiltering/main)

**This library is currently under development.**

## Features

`adaptivefiltering` is a Python package to enhance the productivity of ground point filtering workflows in archaelogy and beyond.
We will write the main feature list here soon.

## Prerequisites

In order to work with `adaptivefiltering`, you need the following required pieces of Software.

* Python >= 3.7
* A [WebGL-enabled](https://get.webgl.org/) browser. We recommend Google Chrome and advise you to test with it whenever you experience difficulties with visualization.
* A [Conda installation](https://conda.io/projects/conda/en/latest/user-guide/install/index.html)

There are alternatives to Conda for installation, but we strongly advise you to use Conda as it offers the best experience for this type of project.

## Installing and using

### Using Conda

Having a [local installation of Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html), the following sequence of commands sets up a Conda environment for `adaptivefiltering`:

```
git clone https://github.com/ssciwr/adaptivefiltering.git
cd adaptivefiltering
conda env create -f environment.yml --force
conda run -n adaptivefiltering python -m pip install .
```

You can start the JupyterLab frontend by doing:

```
conda activate adaptivefiltering
jupyter lab
```

### Using Binder

You can try `adaptivefiltering` without prior installation by using [Binder](https://mybinder.org/v2/gh/ssciwr/adaptivefiltering/main), which is a free cloud-hosted service to run Jupyter notebooks. This will give you an impression of the library's capabilities, but you will want to work on a local setup when using the library productively: On Binder, you might experience very long startup times, slow user experience and limitations to disk space and memory.

### Using Docker

Having set up [Docker](https://docs.docker.com/get-docker/), the following sequence of commands will build an image containing `adaptivefiltering`:

```
git clone https://github.com/ssciwr/adaptivefiltering.git
cd adaptivefiltering
docker build -t adaptivefiltering:latest .
```

You can start the the JupyterLab frontend by doing:

```
docker run -t -p 8888:8888 adaptivefiltering:latest
```

### Using Pip

We advise you to use Conda instead for two reasons:

* We depend on a lot of other Python packages, some of which have external C/C++ dependencies. Using Conda, you get all of these installed automatically, using pip you will need to do a lot of manual work to get the same result.
* We make use of a lot of Jupyter (Lab) extensions that require an additional activation step after installation. These steps are automatically performed in Conda and need to be done manually with pip.

That being said, `adaptivefiltering` can be installed using a normal `pip install` workflow.
