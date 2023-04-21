#!/bin/bash

# Deploy to ssc-jupyter.iwr.uni-heidelberg.de

set -e

# Push the built images to our JupyterHub instance
docker login ssc-jupyter.iwr.uni-heidelberg.de:5000
docker push ssc-jupyter.iwr.uni-heidelberg.de:5000/afwizard-free:latest
docker push ssc-jupyter.iwr.uni-heidelberg.de:5000/afwizard-proprietary:latest
docker logout

# Retag the public image and push it to DockerHub
docker tag ssc-jupyter.iwr.uni-heidelberg.de:5000/afwizard-free:latest ssciwr/afwizard:latest
docker login
docker push ssciwr/afwizard:latest
docker logout
