#!/bin/bash

# Make sure to run this from the top-level directory of adaptivefiltering
# To build the proprietary container, place the following files into
# the adaptivefiltering root directory before running this script:
#
# * opals_nightly_linux64.tar.gz
#       The OPALS (Linux) tarball that you downloaded
#       from https://opals.geo.tuwien.ac.at/html/stable/index.html
#       Note that the latest development version is required, not
#       the latest stable release (as of June 21).
# * opals.key
#       The OPALS keyfile. This file will be present
#       in the built image. Do only share the image with people that
#       you are allowed to share the key with.

# Exit on errors
set -e

# Build the open source Docker image
docker build \
    -t ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest \
    .

# Build the image that includes OPALS
docker build \
    -t ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-proprietary:latest \
    --file ./docker/proprietary.dockerfile \
    .
