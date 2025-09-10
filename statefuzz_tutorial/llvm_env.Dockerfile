FROM ubuntu:20.04 as basic_env

LABEL maintainer="nop" email="nopitydays@gmail.com"
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Buenos_Aires

RUN export http_proxy="http://proxy.fcen.uba.ar:8080"; export HTTP_PROXY="http://proxy.fcen.uba.ar:8080"; \
    apt-get update && apt-get install -y --no-install-recommends sudo gcc g++ binutils \
    cmake make ninja-build clang lld \
    python automake autoconf libelf-dev bc git \
    flex bison python3 libssl-dev dwarves pkg-config \
    libxml2-dev sqlite3 libsqlite3-dev vim \
    ca-certificates



RUN useradd -ms /bin/bash fuzz
RUN echo "fuzz:fuzz" | chpasswd && \
    gpasswd -a fuzz sudo && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER fuzz
RUN mkdir -p /home/fuzz/code /home/fuzz/kernel /home/fuzz/kernel/fs

FROM basic_env as llvm_env
# compile llvm-11.0.1
RUN git clone --depth 1 --branch z3-4.12.2 https://github.com/Z3Prover/z3 /home/fuzz/code/z3
WORKDIR /home/fuzz/code/z3
RUN ./configure && cd build && make -j8 && sudo make install

COPY --chown=fuzz llvm-11.0.1 /home/fuzz/code/llvm-11.0.1
RUN mkdir /home/fuzz/code/llvm-11.0.1/build
WORKDIR /home/fuzz/code/llvm-11.0.1/build
# breaks here
RUN cmake -G Ninja -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_LINKER=lld -DLLVM_USE_LINKER=lld  .. 
#RUN ninja
