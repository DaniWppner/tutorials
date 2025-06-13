- Serie de pasos para instalar debug symbols en la instalación de ubuntu local:
[Respuesta de Colin Ian King y dragosb](https://askubuntu.com/questions/197016/how-to-install-a-package-that-contains-ubuntu-kernel-debug-symbols)

- Install systemtap:
```sudo apt-get install systemtap```

- Ejecutar el script de bpftrace:
`bpftrace trace_vfs_open_inodes`