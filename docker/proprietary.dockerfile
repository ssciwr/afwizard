# The image with proprietary filter frameworks is an extension of the free one
FROM ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest

# Install some system dependencies - mainly because OPALS does
# not find required shared libraries from Conda. Wine is required
# to be able to run the pre-compiled Windows binaries for LASTools
USER root
RUN apt update && \
    apt install --no-install-recommends --yes \
      libcurl4 \
      libxml2 \
      unzip \
      wine && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
USER ${NB_USER}

# Copy the tarball into the container
COPY --chown=${NB_UID} ./opals_nightly_linux64.tar.gz /opt/opals/opals_nightly_linux64.tar.gz

# Extract the tarball
WORKDIR /opt/opals
RUN tar xzvf opals_nightly_linux64.tar.gz && \
    rm opals_nightly_linux64.tar.gz
WORKDIR ${HOME}

# Copy the license file into the correct location
ADD --chown=${NB_UID} opals.key /opt/opals/opals_2.3.2/cfg

# Export the location of OPALS
ENV OPALS_DIR=/opt/opals/opals_2.3.2

# Copy the lastools archive into the correct location
ADD --chown=${NB_UID} LAStools.zip /opt/lastools/LAStools.zip

# Extract the archive
WORKDIR /opt/lastools
RUN unzip LAStools.zip && rm LAStools.zip
WORKDIR ${HOME}

# Export the location of LASTools
ENV LASTOOLS_DIR=/opt/lastools/LASTools
