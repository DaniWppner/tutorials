# This Dockerfile provides an environment to compile Linux kernel v4.11.0

FROM ubuntu:16.04
LABEL maintainer="danielituswapp@gmail.com"

# Install build dependencies.
# Update the apt's source list and include the sources of the packages.
RUN grep deb /etc/apt/sources.list | \
    sed 's/^deb/deb-src /g' >> /etc/apt/sources.list

# Install compiler, c++ libraries and utilities appropriate for ~2017
RUN TZ=AR DEBIAN_FRONTEND=noninteractive http_proxy=http://proxy.fcen.uba.ar:8080 HTTP_PROXY=http://proxy.fcen.uba.ar:8080 apt-get update && \
    TZ=AR DEBIAN_FRONTEND=noninteractive http_proxy=http://proxy.fcen.uba.ar:8080 HTTP_PROXY=http://proxy.fcen.uba.ar:8080 apt-get install -y --no-install-recommends \
       ca-certificates gnupg \
           # In Ubuntu 16.04, build-essential safely pulls GCC 5.4 natively
           build-essential cmake make zlib1g wget subversion unzip git \
           # These are needed to configure and build older Linux kernels
           flex bison bc libelf-dev libssl-dev libncurses5-dev

# Clean apt-get data
RUN rm -rf /var/lib/apt/lists/*