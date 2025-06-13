// file_opener.c
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>

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

    if (mkdir("./tmp/a", 0755) == 0) {
        printf("Created directory ./tmp/a\n");
    }

    if (link("./tmp/testfile.txt", "./tmp/a/b.txt") == 0) {
        printf("Created hard link ./tmp/a/b.txt -> ./tmp/testfile.txt\n");
    }

    if (unlink("./tmp/a/b.txt") == 0) {
        printf("Deleted ./tmp/a/b.txt\n");
    }

    if (rmdir("./tmp/a") == 0) {
        printf("Deleted directory ./tmp/a\n");
    }
    
    return 0;
}
