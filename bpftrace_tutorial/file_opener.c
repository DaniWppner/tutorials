// file_opener.c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main() {
    int fd1 = open("/etc/hostname", O_RDONLY);
    if (fd1 >= 0){
	 printf("/etc/hostname opened with fd: %d\n", fd1);

	 close(fd1);
    }

    int fd2 = open("./tmp/testfile.txt", O_CREAT | O_WRONLY, 0644);
    if (fd2 >= 0){
	 printf("./tmp/testfile.txt opened with fd: %d\n", fd2);
	 close(fd2);
    }

    return 0;
}
