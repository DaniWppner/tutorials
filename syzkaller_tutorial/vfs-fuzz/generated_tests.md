## 1. open - open$dir - open$dir - open - pwritev- ioctl$FIDEDUPERANGE
```
open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r0 = open$dir(&(0x7f0000000780)='./file0\x00', 0x109082, 0xfa)
r1 = open$dir(&(0x7f0000000ec0)='.\x00', 0x8000, 0x30)
r2 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
pwritev(r0, &(0x7f0000000980)=[{&(0x7f00000007c0)="d56b8237602079233732", 0xa}], 0x1, 0x6, 0x8868)
ioctl$FIDEDUPERANGE(r2, 0xc0189436, &(0x7f00000000c0)={0x7, 0x9, 0x1, 0x0, 0x0, [{{r1}, 0x9}]})
```

## 2. open - open$dir - pwrite64 - open - ioctl$FIDEDUPERANGE
```
r0 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r1 = open$dir(&(0x7f0000001ac0)='./file0\x00', 0x1, 0x1c4)
pwrite64(r1, &(0x7f0000002300)='a', 0x1, 0x8000)
r2 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, &(0x7f0000000080)=ANY=[@ANYBLOB="760000000000000009000000000000000400000000000000", @ANYRES32=r0, @ANYBLOB="000000000100"/28, @ANYRES32=r0, @ANYBLOB="000000000100"/28, @ANYRES32=r1, @ANYBLOB='\x00\x00\x00\x00\b\x00'/28, @ANYRES32=r2, @ANYBLOB="00000000010000000000008000"])
```

## 3. open$dir - ioctl$FIDEDUPERANGE
```
r0 = open$dir(&(0x7f0000005f00)='./file1\x00', 0x88c2, 0x121)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, &(0x7f0000001180)=ANY=[])
```

## 4. open - open - ioctl$FIDEDUPERANGE
```
open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r0 = open(&(0x7f00000002c0)='./file0\x00', 0x600, 0x103)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, 0x0)
```

## 5. open - open - ioctl$FIDEDUPERANGE
```
open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r0 = open(&(0x7f00000002c0)='./file0\x00', 0x600, 0x103)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, &(0x7f00000003c0)={0x42df79c9, 0x1})
```

## 6. open - open$dir - ioctl$FIDEDUPERANGE
```
r0 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r1 = open$dir(&(0x7f0000001ac0)='./file0\x00', 0x1, 0x1c4)
pwrite64(r1, &(0x7f0000002300)='a', 0x1, 0x8000)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, &(0x7f0000000080)=ANY=[@ANYBLOB="7600000000000000090000000000000004"])
```

## 7. open - open$dir - pwritev - open$dir - ioctl$FIDEDUPERANGE
```
r0 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
r1 = open$dir(&(0x7f0000000780)='./file0\x00', 0x109082, 0xfa)
pwritev(r1, &(0x7f0000000980)=[{&(0x7f00000007c0)="d56b8237602079233732e2", 0xb}], 0x1, 0x6, 0x8868)
r2 = open$dir(&(0x7f0000000780)='./file0\x00', 0x109082, 0xfa)
ioctl$FIDEDUPERANGE(r1, 0xc0189436, &(0x7f0000000040)={0xf, 0x2, 0x2, 0x0, 0x0, [{{r0}, 0x9}, {{r2}}]})
```

## 8. open - ioctl$FIDEDUPERANGE
```
r0 = open(&(0x7f0000000000)='./file0\x00', 0x20040, 0x16)
ioctl$FIDEDUPERANGE(r0, 0xc0189436, &(0x7f00000000c0)=ANY=[@ANYBLOB="0000000000000000fdffffffffffffff0a"])
```