#!/bin/bash

# Deploy to ssc-jupyter.iwr.uni-heidelberg.de

set -e

docker login ssc-jupyter.iwr.uni-heidelberg.de:5000
docker push ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest
docker push ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-proprietary:latest
docker logout
