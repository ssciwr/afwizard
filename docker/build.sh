#!/bin/bash

# Make sure to run this from the top-level directory of filteradapt

# Exit on errors
set -e

# Build the open source Docker image
docker build -t ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest --file ./docker/free.dockerfile .

# Build the image that includes OPALS
docker build -t ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-proprietary:latest --file ./docker/proprietary.dockerfile .
