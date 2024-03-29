#!/bin/bash

# Make sure to run this from the top-level directory of AFwizard
# To build the proprietary container, place the following files into
# the AFwizard root directory before running this script:
#
# * opals_2.5.0_linux64.tar.gz
#       The OPALS (Linux) tarball that you downloaded
#       from https://opals.geo.tuwien.ac.at/html/stable/index.html
#       Note that AFwizard requires OPALS v2.5.
# * opals.key
#       The OPALS keyfile. This file will be present
#       in the built image. Do only share the image with people that
#       you are allowed to share the key with.
# * LASTools.zip
#       The ZIP archive with LASTools sources
#

# Exit on errors
set -e

# Build the open source Docker image
docker build \
    -t ssc-jupyter.iwr.uni-heidelberg.de:5000/afwizard-free:latest \
    .

# Build the image that includes OPALS
docker build \
    -t ssc-jupyter.iwr.uni-heidelberg.de:5000/afwizard-proprietary:latest \
    --file ./docker/proprietary.dockerfile \
    .
