# Welcome to the Adaptive Ground Point Filtering Library

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/ssciwr/filteradapt/CI)](https://github.com/ssciwr/filteradapt/actions?query=workflow%3ACI)
[![codecov](https://codecov.io/gh/ssciwr/filteradapt/branch/main/graph/badge.svg?token=ONIG38R74Y)](https://codecov.io/gh/ssciwr/filteradapt)
[![Documentation Status](https://readthedocs.org/projects/filteradapt/badge/)](https://filteradapt.readthedocs.io/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/ssciwr/filteradapt/main)

**This library is currently under development.**

## Features

`filteradapt` is a Python package to enhance the productivity of ground point filtering workflows in archaelogy and beyond.
Main features are:

* Visualization of Point Cloud Data directly in Jupyter
* *many more to come soon*

## Installing and using

You can try `filteradapt` without prior installation by using [Binder](https://mybinder.org/v2/gh/ssciwr/filteradapt/main).
You might experience long startup times, slow user experience and limitations to disk space and memory though.

### Using Conda

Having a [local installation of Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html), the following sequence of commands sets up a Conda environment for `filteradapt`:

```
git clone https://github.com/ssciwr/filteradapt.git
cd filteradapt
conda env create -f environment.yml --force
conda run -n filteradapt python -m pip install .
```

You can start the JupyterLab frontend by doing:

```
conda activate filteradapt
jupyter lab
```

### Using Docker

Having set up [Docker](https://docs.docker.com/get-docker/), the following sequence of commands will build an image containing `filteradapt`:

```
git clone https://github.com/ssciwr/filteradapt.git
cd filteradapt
docker build -t filteradapt:latest .
```

You can start the the JupyterLab frontend by doing:

```
docker run -t -p 8888:8888 filteradapt:latest
```
