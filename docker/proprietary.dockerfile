# The image with proprietary filter frameworks is an extension of the free one
FROM ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest AS opals-unpack
USER ${NB_USER}

# Copy the tarball into the container
COPY --chown=${NB_UID} ./opals_nightly_linux64.tar.gz /opt/opals/opals_nightly_linux64.tar.gz

# Extract the tarball
WORKDIR /opt/opals
RUN tar xzvf opals_nightly_linux64.tar.gz && \
    rm opals_nightly_linux64.tar.gz

# Copy the license file into the correct location
ADD --chown=${NB_UID} opals.key /opt/opals/opals_2.3.2/cfg

# Remove some parts of OPALS that are just not needed for our purpose but take up a lot of space
RUN rm -rf /opt/opals/opals_2.3.2/demo && \
    rm -rf /opt/opals/opals_2.3.2/doc

FROM ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest AS lastools-unpack

# We need unzip to unpack LASTools
USER root
RUN apt update && \
    apt install --no-install-recommends --yes unzip
USER ${NB_USER}

# Copy the lastools archive into the correct location
ADD --chown=${NB_UID} LAStools.zip /opt/lastools/LAStools.zip

# Extract the archive
WORKDIR /opt/lastools
RUN unzip LAStools.zip && rm LAStools.zip
WORKDIR ${HOME}

# Create the final image that only contains the absolute necssary minimum
FROM ssc-jupyter.iwr.uni-heidelberg.de:5000/filter-library-free:latest

# Install some system dependencies - mainly because OPALS does
# not find required shared libraries from Conda. Wine is required
# to be able to run the pre-compiled Windows binaries for LASTools
USER root
RUN apt update && \
    apt install --no-install-recommends --yes \
      libcurl4 \
      libxml2 \
      wine && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
USER ${NB_USER}

# Copy OPALS and LASTools
COPY --from=opals-unpack /opt/opals /opt/opals
COPY --from=lastools-unpack /opt/lastools /opt/lastools

# Export the locations as environment variables
ENV OPALS_DIR=/opt/opals/opals_2.3.2
ENV LASTOOLS_DIR=/opt/lastools/LASTools
