## Steps to reproduce kernel config (available at v4.19.192-syzkaller-btrfs-xfs.config)
First, make sure you have the following apt dependencies installed:
```
flex bison bc libelf-dev libssl-dev
```
Execute the following commands inside the kernel source root.
path/to/syzkaller.config refers to syzkaller.config available on the root of this tutorial. 
```
make defconfig
make kvm_guest.config
scripts/kconfig/merge_config.sh .config path/to/syzkaller_kernelversion_lessthan_5.12.config
make olddefconfig
make menuconfig
```
Inside menu config, you can enable the `btrfs` and `xfs` file systems. Leave everything else intact.
Now you can build with:
```
make CC=gcc-9 HOSTCC=gcc-9 -j8
```
Update the amount of compilation jobs accordingly.