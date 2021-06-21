# Welcome to the Adaptive Ground Point Filtering Library

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ssciwr/adaptivefiltering/CI)](https://github.com/ssciwr/adaptivefiltering/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/ssciwr/adaptivefiltering/branch/main/graph/badge.svg?token=ONIG38R74Y)](https://codecov.io/gh/ssciwr/adaptivefiltering)
[![Documentation Status](https://readthedocs.org/projects/adaptivefiltering/badge/)](https://adaptivefiltering.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ssciwr/adaptivefiltering/main)

**This library is currently under development.**

## Features

`adaptivefiltering` is a Python package to enhance the productivity of ground point filtering workflows in archaelogy and beyond.
Main features are:

* Visualization of Point Cloud Data directly in Jupyter
* *many more to come soon*

## Installing and using

You can try `adaptivefiltering` without prior installation by using [Binder](https://mybinder.org/v2/gh/ssciwr/adaptivefiltering/main).
You might experience long startup times, slow user experience and limitations to disk space and memory though.

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
