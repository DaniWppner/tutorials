FROM ubuntu:20.04 as basic_env

LABEL maintainer="nop" email="nopitydays@gmail.com"
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Buenos_Aires

RUN DEBIAN_FRONTEND=noninteractive http_proxy=http://proxy.fcen.uba.ar:8080 HTTP_PROXY=http://proxy.fcen.uba.ar:8080 apt-get update && \
    DEBIAN_FRONTEND=noninteractive http_proxy=http://proxy.fcen.uba.ar:8080 HTTP_PROXY=http://proxy.fcen.uba.ar:8080 apt-get install -y --no-install-recommends \
    sudo gcc g++ binutils \
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
RUN cmake -G Ninja -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_LINKER=lld -DLLVM_USE_LINKER=lld  .. 
RUN ninja

FROM llvm_env as difuze_env
# build DIFUZE, stop before executing it (it requires output from kernel build)
ENV PATH="$PATH:/home/fuzz/code/llvm-11.0.1/build/bin:/home/fuzz/code/difuze/difuze_deps/sparse"
ENV LLVM_ROOT="LLVM_ROOT=/home/fuzz/code/llvm-11.0.1/build"
RUN mkdir -p /tmp/difuze/ home/fuzz/kernel/ioctlfinded-linux /home/fuzz/kernel/lvout-linux
COPY --chown=fuzz difuze /home/fuzz/code/difuze
RUN git clone --depth 1 --branch v0.6.4 git://git.kernel.org/pub/scm/devel/sparse/sparse.git /home/fuzz/code/difuze/difuze_deps/sparse
WORKDIR /home/fuzz/code/difuze/difuze_deps/sparse
RUN mv /home/fuzz/code/difuze/deps/sparse/pre-process.c /home/fuzz/code/difuze/difuze_deps/sparse/ && rm -rf /home/fuzz/code/difuze/deps/
RUN make -j8
WORKDIR /home/fuzz/code/difuze/InterfaceHandlers
RUN chmod +x build.sh && ./build.sh

# example of usage, commented out to avoid running it at build time:
# WORKDIR /home/fuzz/code/difuze/helper_scripts
# RUN python run_all.py -l /home/fuzz/kernel/lvout-linux -a 5 -m /home/fuzz/kernel/linux/makeout.txt -g /home/fuzz/code/llvm-11.0.1/build/bin/clang -n 3 -o /home/fuzz/kernel/linux-out -k /home/fuzz/kernel/linux -f /home/fuzz/kernel/ioctlfinded-linux -clangp /home/fuzz/code/llvm-11.0.1/build/bin/clang 2>&1 | tee output.log && sudo rm /tmp/tmp*
