# This Dockerfile is meant to provide an environment to compile the llvm(clang) infrastructure

FROM debian:bookworm
# Based on sample Dockerfile by LLVM Developers
LABEL maintainer="danielituswapp@gmail.com"

# Install build dependencies of llvm.
# First, Update the apt's source list and include the sources of the packages.
RUN grep deb /etc/apt/sources.list | \
    sed 's/^deb/deb-src /g' >> /etc/apt/sources.list

# Install compiler, python and subversion.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates gnupg \
           build-essential cmake make python3 zlib1g wget subversion unzip git && \
    rm -rf /var/lib/apt/lists/*