/* Copy one file in 1 MiB blocks (good for local NTFS and SMB/CIFS),
 * hashing MD5 of the copied bytes. Prints the 32-char hex digest on stdout.
 *
 * cl /O2 /utf-8 fastcopy.c
 * gcc -O2 -o fastcopy.exe fastcopy.c -lshell32 -ladvapi32
 */

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <wincrypt.h>
#include <stdio.h>

#define BLOCK_SIZE (1u << 20)

static void fail(LPCWSTR what)
{
	fwprintf(stderr, L"%s failed: %lu\n", what, GetLastError());
}

int main(void)
{
	int argc, i, rc = 1;
	LPWSTR *argv;
	HANDLE src = INVALID_HANDLE_VALUE, dst = INVALID_HANDLE_VALUE;
	LPVOID buf = NULL;
	HCRYPTPROV prov = 0;
	HCRYPTHASH hash = 0;
	LARGE_INTEGER size, zero = {0};
	DWORD nread, nwritten, md5_len = 16;
	BYTE md5[16];

	argv = CommandLineToArgvW(GetCommandLineW(), &argc);
	if (!argv || argc != 3) {
		fwprintf(stderr, L"Usage: fastcopy <source> <destination>\n");
		return 1;
	}

	src = CreateFileW(argv[1], GENERIC_READ, FILE_SHARE_READ, NULL,
		OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (src == INVALID_HANDLE_VALUE) {
		fail(L"Open source");
		goto done;
	}

	dst = CreateFileW(argv[2], GENERIC_WRITE, 0, NULL,
		CREATE_ALWAYS, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (dst == INVALID_HANDLE_VALUE) {
		fail(L"Open destination");
		goto done;
	}

	if (!GetFileSizeEx(src, &size)
		|| !SetFilePointerEx(dst, size, NULL, FILE_BEGIN)
		|| !SetEndOfFile(dst)
		|| !SetFilePointerEx(dst, zero, NULL, FILE_BEGIN)) {
		fail(L"Preallocate destination");
		goto done;
	}

	buf = VirtualAlloc(NULL, BLOCK_SIZE, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
	if (!buf) {
		fail(L"Allocate buffer");
		goto done;
	}

	if (!CryptAcquireContextW(&prov, NULL, NULL, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT)
		|| !CryptCreateHash(prov, CALG_MD5, 0, 0, &hash)) {
		fail(L"Create MD5");
		goto done;
	}

	for (;;) {
		if (!ReadFile(src, buf, BLOCK_SIZE, &nread, NULL)) {
			fail(L"Read");
			goto done;
		}
		if (nread == 0)
			break;
		if (!CryptHashData(hash, buf, nread, 0)) {
			fail(L"Hash");
			goto done;
		}
		if (!WriteFile(dst, buf, nread, &nwritten, NULL) || nwritten != nread) {
			fail(L"Write");
			goto done;
		}
	}

	if (!CryptGetHashParam(hash, HP_HASHVAL, md5, &md5_len, 0)) {
		fail(L"Finish MD5");
		goto done;
	}

	for (i = 0; i < 16; i++)
		printf("%02x", md5[i]);
	printf("\n");
	rc = 0;

done:
	if (hash)
		CryptDestroyHash(hash);
	if (prov)
		CryptReleaseContext(prov, 0);
	if (buf)
		VirtualFree(buf, 0, MEM_RELEASE);
	if (src != INVALID_HANDLE_VALUE)
		CloseHandle(src);
	if (dst != INVALID_HANDLE_VALUE)
		CloseHandle(dst);
	if (argv)
		LocalFree(argv);
	return rc;
}
