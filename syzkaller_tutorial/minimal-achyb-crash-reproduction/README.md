# Steps to reproduce a crash due to an introduced bug in linux v4.19.192:

Follow the same steps as [here](https://github.com/DaniWppner/tutorials/tree/main/syzkaller_tutorial/minimal-bug-reproduction), with the following changes:

- checkout v4.19.192 in the linux repository
- when compiling the linux kernel specify gcc-9 with the `CC` and `HOSTCC` flags in the `make` command:
```
make CC=gcc-9 HOSTCC=gcc-9 -j8
```
- use `accesscontrol_bug.cfg` as the syz-manager configuration instead

## If you don't have gcc-9 available
On Ubuntu, you can try:
```
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt-get update
sudo apt-get install gcc-9
```
Taken from https://stackoverflow.com/questions/448457/how-to-use-multiple-versions-of-gcc
