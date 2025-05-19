# Steps to reproduce a crash due to an introduced bug in linux v6.15-rc5:

### 1. Clone syzkaller and linux repos
Make sure to checkout the **v6.15-rc5** tag inside the linux repo.

### 2. Add crash to ptrace syscall in linux/kernel/ptrace.c
```diff
diff --git a/kernel/ptrace.c b/kernel/ptrace.c
index d5f89f9ef29f..11b866f69e20 100644
--- a/kernel/ptrace.c
+++ b/kernel/ptrace.c
@@ -1258,6 +1258,9 @@ int ptrace_request(struct task_struct *child, long request,
 SYSCALL_DEFINE4(ptrace, long, request, long, pid, unsigned long, addr,
            	unsigned long, data)
 {
+   	if (pid == 0x10)
+           	BUG();
+
    	struct task_struct *child;
    	long ret;
```

### 3. Compile kernel with appropiate configurations
Execute the following commands inside the kernel source root.
path/to/syzkaller.config refers to syzkaller.config available on the root of this tutorial. 
```
make defconfig
make kvm_guest.config
scripts/kconfig/merge_config.sh .config path/to/syzkaller.config
make olddefconfig
make -j8
```
You may update the ammount of compilation threads according to the available CPUs.

### 4. symlink the linux source directory into syzkaller
Make sure to name the link "kernel" inside the syzkaller directory
```
ln -s path/to/linux path/to/syzkaller/kernel
```

### 5. Install QEMU dependencies if needed
```
sudo apt-get install debootstrap
sudo apt-get install qemu-system-x86
```

### 6. (ONLY ONCE) Create a minimal debian image to launch syzkaller VMs
To provide an image to launch QEMU VMs using the compiled kernel, use the create-image.sh tool at syzkaller repo.

Execute the following commands inside the syzkaller repo:
```
mkdir tmp
cd tmp
../tools/create-image.sh
```
`ptrace_bug.cfg` assumes that you executed this script from inside the `syzkaller/tmp` directory.

### 7. Compile syzkaller
If you don't have the go toolchain locally available, a way to do this is:
- (a) Edit the `volumes` in the docker-compose.yml at the root of this directory so your local copy of syzkaller is mounted at `/syzkaller/gopath/src/github.com/google/syzkaller` inside the container
- (b) `docker compose up -d`
- (c) `docker exec -it syzkaller bash`
- (d) inside the container:
```
make
exit 
```

### 8. Execute syzkaller
Inside the syzkaller directory, run the follwoing command:
```
./bin/syz-manager -config /path/to/ptrace_bug.cfg
```