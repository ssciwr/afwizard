FROM jupyter/base-notebook:2022-02-02 AS builder

# Copy the repository into the container
COPY --chown=${NB_UID} . /opt/adaptivefiltering

# Install Conda environment
RUN conda env update -n base --file /opt/adaptivefiltering/environment.yml

# Build and install the project
RUN conda run -n base python -m pip install /opt/adaptivefiltering

# Thoroughly clean up the conda environment to save space
RUN conda clean --force-pkgs-dirs -a -q -y

# Second stage of multistage build
FROM jupyter/base-notebook:2022-02-02

# Make JupyterLab the default for this application
ENV JUPYTER_ENABLE_LAB=yes

# I don't see why we need a work subdirectory in home
RUN rm -rf ${HOME}/work

# Copy the artifacts from stage 0 that we need
COPY --from=builder /opt/conda /opt/conda
COPY --from=builder /opt/adaptivefiltering/jupyter/* ${HOME}/
