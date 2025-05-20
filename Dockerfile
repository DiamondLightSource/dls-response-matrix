# This file is for use as a devcontainer and a runtime container
#
# The devcontainer should use the build target and run as root with podman
# or docker with user namespaces.
#
FROM python:3.10 as build

ARG PIP_OPTIONS=.

# Add any system dependencies for the developer/build environment here e.g.
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libqt5gui5 \
    && rm -rf /var/lib/apt/lists/*

# set up a virtual environment and put it in PATH
RUN python -m venv /venv

# these sometimes seem to get lost, idk why but ive put them in twice so they can be seen both when using devcontainer and from the podman CLI
ENV PATH=/venv/bin:$PATH
ENV EPICS_CA_SERVER_PORT=8064
ENV EPICS_CA_REPEATER_PORT=8065

# Copy any required context for the pip install over
COPY . /context
WORKDIR /context

# install python package into /venv
RUN pip install ${PIP_OPTIONS}

FROM python:3.10-slim as runtime

# Add apt-get system dependecies for runtime here if needed
RUN apt-get update && apt-get upgrade -y && \
apt-get install -y --no-install-recommends \
libqt5gui5 \
&& rm -rf /var/lib/apt/lists/*

# copy the virtual environment from the build stage and put it in PATH
COPY --from=build /venv/ /venv/

ENV PATH=/venv/bin:$PATH
ENV EPICS_CA_SERVER_PORT=8064
ENV EPICS_CA_REPEATER_PORT=8065

# change this entrypoint if it is not the same as the repo
ENTRYPOINT ["dls-response-matrix-gui"]

