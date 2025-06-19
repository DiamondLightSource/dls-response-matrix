# The devcontainer should use the developer target and run as root with podman
# or docker with user namespaces.
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION} AS developer

# Add any system dependencies for the developer/build environment here
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libqt5gui5 \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

# Set up a virtual environment and put it in PATH
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
ENV EPICS_CA_SERVER_PORT=8064
ENV EPICS_CA_REPEATER_PORT=8065

# The build stage installs the context into the venv
FROM developer AS build
COPY . /context
WORKDIR /context
RUN touch dev-requirements.txt && pip install --upgrade pip && pip install -c dev-requirements.txt .

# The runtime stage copies the built venv into a slim runtime container
FROM python:${PYTHON_VERSION}-slim AS runtime
# Add apt-get system dependecies for runtime here if needed
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libqt5gui5 \
    libxcb-cursor0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /venv/ /venv/
ENV PATH=/venv/bin:$PATH
ENV EPICS_CA_SERVER_PORT=8064
ENV EPICS_CA_REPEATER_PORT=8065

# change this entrypoint if it is not the same as the repo
ENTRYPOINT ["dls-response-matrix-gui"]
CMD ["--version"]
