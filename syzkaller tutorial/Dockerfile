FROM gcr.io/syzkaller/env

RUN apt-get install -y qemu-system-x86
RUN apt autoremove -y -q
ENTRYPOINT ["bash"]