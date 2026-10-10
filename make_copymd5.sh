#!/bin/sh
# Build copymd5 (Linux) and copymd5.exe (Windows / MinGW).
set -e
cd "$(dirname "$0")"

gcc -O2 -o copymd5 copymd5_lin.c -pthread
x86_64-w64-mingw32-gcc -O2 -o copymd5.exe copymd5.c -lshell32

echo "Built copymd5 and copymd5.exe"
