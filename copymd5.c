/* Copy one source file or directory into a destination directory.
 * A directory is copied recursively. Several files are copied at once.
 * Each file uses overlapped, unbuffered transfers (512 MiB when that buffer
 * can be allocated) and a direct MD5.
 * Each file appends one tab-separated line to the tsv file:
 * "<relative_path>" <md5> <source_size> <destination_size> <result>.
 * A failed read appends ERROR, the source size, ERROR, and READ_ERROR.
 * A failed write appends the digest, both sizes, and WRITE_ERROR.
 * A size mismatch appends the digest, both sizes, and SIZE_MISMATCH.
 * A new tsv file starts with a header. An existing tsv file is appended to.
 * Stdout and stderr are UTF-8. Stdout prints the bytes written so far and the
 * number of copied files, separated by a space, and is flushed once a second.
 * Read and write errors are tolerated up to 20 each; the run aborts only when
 * either count goes past that. Size mismatches are recorded and never abort.
 * When any file fails, stderr ends with the write, read, and size-mismatch
 * counts. Stderr stays empty when the copy succeeds.
 *
 * cl /O2 /utf-8 copymd5.c
 * x86_64-w64-mingw32-gcc -O2 -o copymd5.exe copymd5.c -lshell32
 */

#define VERSION "1.0.0-2026-11-28"

#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <string.h>
#include <io.h>
#include <fcntl.h>
#ifdef _MSC_VER
#include <intrin.h>
#define MD5_ROTL(x, n) _rotl((x), (n))
#else
#define MD5_ROTL(x, n) (((x) << (n)) | ((x) >> (32 - (n))))
#endif

#ifdef _MSC_VER
#pragma comment(lib, "shell32.lib")
#endif

#define ALIGN_SIZE 4096u
#define BLOCK_SIZE (512u << 20)
#define MIN_BLOCK (1u << 20)
#define IO_ATTEMPTS 3
#define MAX_IO_ERRORS 20
#define MAX_TASKS 8

static CRITICAL_SECTION g_out_lock;
static volatile LONG g_out_lock_ready;
static LONG64 g_files;
static LONG64 g_processed;
static LONG64 g_read_errors;
static LONG64 g_write_errors;
static LONG64 g_size_mismatches;
static volatile LONG g_io_error;
static FILE *g_tsv;
static LPCWSTR g_tsv_path;
static const char g_tsv_header[] = "Path\tMD5\tSourceSize\tDestinationSize\tResult\n";

static void out_lock(void)
{
	if (g_out_lock_ready)
		EnterCriticalSection(&g_out_lock);
}

static void out_unlock(void)
{
	if (g_out_lock_ready)
		LeaveCriticalSection(&g_out_lock);
}

static void fail(LPCWSTR what)
{
	DWORD err = GetLastError();

	out_lock();
	fwprintf(stderr, L"%s failed: %lu\n", what, err);
	out_unlock();
}

static void fail_path(LPCWSTR path, LPCWSTR what)
{
	DWORD err = GetLastError();

	out_lock();
	fwprintf(stderr, L"%s: %s failed: %lu\n", path, what, err);
	out_unlock();
}

static LPCWSTR basename_w(LPCWSTR path)
{
	LPCWSTR name = path;

	for (; *path; path++) {
		if (*path == L'\\' || *path == L'/')
			name = path + 1;
	}
	return name;
}

static LPWSTR join_dir_file(LPCWSTR dir, LPCWSTR name)
{
	int dlen = lstrlenW(dir);
	int nlen = lstrlenW(name);
	int sep = (dlen == 0 || (dir[dlen - 1] != L'\\' && dir[dlen - 1] != L'/'));
	LPWSTR out = (LPWSTR)LocalAlloc(LMEM_FIXED,
		(dlen + sep + nlen + 1) * sizeof(WCHAR));

	if (!out)
		return NULL;
	lstrcpyW(out, dir);
	if (sep)
		lstrcatW(out, L"\\");
	lstrcatW(out, name);
	return out;
}

static LPWSTR wcsdup_w(LPCWSTR s)
{
	int n = lstrlenW(s);
	LPWSTR out = (LPWSTR)LocalAlloc(LMEM_FIXED, (n + 1) * sizeof(WCHAR));

	if (out)
		lstrcpyW(out, s);
	return out;
}

static int ends_with_sep(LPCWSTR s, int n)
{
	return n > 0 && (s[n - 1] == L'\\' || s[n - 1] == L'/');
}

static void strip_dir_slash(LPWSTR path)
{
	int n = lstrlenW(path);

	while (n > 1 && ends_with_sep(path, n) && path[n - 2] != L':')
		path[--n] = 0;
}

static void slashes_to_backslashes(LPWSTR path)
{
	for (; *path; path++) {
		if (*path == L'/')
			*path = L'\\';
	}
}

static LPWSTR full_path(LPCWSTR path)
{
	DWORD n;
	LPWSTR tmp, out;
	int len = lstrlenW(path);

	tmp = (LPWSTR)LocalAlloc(LMEM_FIXED, (len + 1) * sizeof(WCHAR));
	if (!tmp)
		return NULL;
	lstrcpyW(tmp, path);
	slashes_to_backslashes(tmp);
	n = GetFullPathNameW(tmp, 0, NULL, NULL);
	if (!n) {
		LocalFree(tmp);
		return NULL;
	}
	out = (LPWSTR)LocalAlloc(LMEM_FIXED, n * sizeof(WCHAR));
	if (!out) {
		LocalFree(tmp);
		return NULL;
	}
	if (!GetFullPathNameW(tmp, n, out, NULL)) {
		LocalFree(tmp);
		LocalFree(out);
		return NULL;
	}
	LocalFree(tmp);
	slashes_to_backslashes(out);
	strip_dir_slash(out);
	return out;
}

static int is_same_or_child(LPCWSTR parent, LPCWSTR child)
{
	int plen = lstrlenW(parent);
	int clen = lstrlenW(child);
	int parent_root;

	if (plen > 1 && ends_with_sep(parent, plen) && !(plen == 3 && parent[1] == L':'))
		plen--;
	parent_root = ends_with_sep(parent, plen);
	if (clen < plen)
		return 0;
	if (CompareStringOrdinal(parent, plen, child, plen, TRUE) != CSTR_EQUAL)
		return 0;
	if (clen == plen || parent_root)
		return 1;
	return child[plen] == L'\\' || child[plen] == L'/';
}

struct md5 {
	unsigned int s[4];
	unsigned char buf[64];
	ULONGLONG nbytes;
	unsigned int nbuf;
};

struct io_slot {
	OVERLAPPED ov;
	HANDLE ev;
	int pending;
	DWORD got;
	DWORD want;
};

#define MD5_F(x, y, z) ((z) ^ ((x) & ((y) ^ (z))))
#define MD5_G(x, y, z) ((y) ^ ((z) & ((x) ^ (y))))
#define MD5_H(x, y, z) ((x) ^ (y) ^ (z))
#define MD5_I(x, y, z) ((y) ^ ((x) | ~(z)))
#define MD5_STEP(f, a, b, c, d, w, sh, ac) do { \
	(a) += f((b), (c), (d)) + (w) + (unsigned int)(ac); \
	(a) = MD5_ROTL((a), (sh)); \
	(a) += (b); \
} while (0)

static unsigned int md5_load(const unsigned char *p)
{
	unsigned int v;

	memcpy(&v, p, 4);
	return v;
}

static void md5_block(unsigned int st[4], const unsigned char *blk)
{
	unsigned int a = st[0], b = st[1], c = st[2], d = st[3];
	unsigned int w0 = md5_load(blk), w1 = md5_load(blk + 4);
	unsigned int w2 = md5_load(blk + 8), w3 = md5_load(blk + 12);
	unsigned int w4 = md5_load(blk + 16), w5 = md5_load(blk + 20);
	unsigned int w6 = md5_load(blk + 24), w7 = md5_load(blk + 28);
	unsigned int w8 = md5_load(blk + 32), w9 = md5_load(blk + 36);
	unsigned int w10 = md5_load(blk + 40), w11 = md5_load(blk + 44);
	unsigned int w12 = md5_load(blk + 48), w13 = md5_load(blk + 52);
	unsigned int w14 = md5_load(blk + 56), w15 = md5_load(blk + 60);

	MD5_STEP(MD5_F, a, b, c, d, w0, 7, 0xd76aa478); MD5_STEP(MD5_F, d, a, b, c, w1, 12, 0xe8c7b756);
	MD5_STEP(MD5_F, c, d, a, b, w2, 17, 0x242070db); MD5_STEP(MD5_F, b, c, d, a, w3, 22, 0xc1bdceee);
	MD5_STEP(MD5_F, a, b, c, d, w4, 7, 0xf57c0faf); MD5_STEP(MD5_F, d, a, b, c, w5, 12, 0x4787c62a);
	MD5_STEP(MD5_F, c, d, a, b, w6, 17, 0xa8304613); MD5_STEP(MD5_F, b, c, d, a, w7, 22, 0xfd469501);
	MD5_STEP(MD5_F, a, b, c, d, w8, 7, 0x698098d8); MD5_STEP(MD5_F, d, a, b, c, w9, 12, 0x8b44f7af);
	MD5_STEP(MD5_F, c, d, a, b, w10, 17, 0xffff5bb1); MD5_STEP(MD5_F, b, c, d, a, w11, 22, 0x895cd7be);
	MD5_STEP(MD5_F, a, b, c, d, w12, 7, 0x6b901122); MD5_STEP(MD5_F, d, a, b, c, w13, 12, 0xfd987193);
	MD5_STEP(MD5_F, c, d, a, b, w14, 17, 0xa679438e); MD5_STEP(MD5_F, b, c, d, a, w15, 22, 0x49b40821);

	MD5_STEP(MD5_G, a, b, c, d, w1, 5, 0xf61e2562); MD5_STEP(MD5_G, d, a, b, c, w6, 9, 0xc040b340);
	MD5_STEP(MD5_G, c, d, a, b, w11, 14, 0x265e5a51); MD5_STEP(MD5_G, b, c, d, a, w0, 20, 0xe9b6c7aa);
	MD5_STEP(MD5_G, a, b, c, d, w5, 5, 0xd62f105d); MD5_STEP(MD5_G, d, a, b, c, w10, 9, 0x02441453);
	MD5_STEP(MD5_G, c, d, a, b, w15, 14, 0xd8a1e681); MD5_STEP(MD5_G, b, c, d, a, w4, 20, 0xe7d3fbc8);
	MD5_STEP(MD5_G, a, b, c, d, w9, 5, 0x21e1cde6); MD5_STEP(MD5_G, d, a, b, c, w14, 9, 0xc33707d6);
	MD5_STEP(MD5_G, c, d, a, b, w3, 14, 0xf4d50d87); MD5_STEP(MD5_G, b, c, d, a, w8, 20, 0x455a14ed);
	MD5_STEP(MD5_G, a, b, c, d, w13, 5, 0xa9e3e905); MD5_STEP(MD5_G, d, a, b, c, w2, 9, 0xfcefa3f8);
	MD5_STEP(MD5_G, c, d, a, b, w7, 14, 0x676f02d9); MD5_STEP(MD5_G, b, c, d, a, w12, 20, 0x8d2a4c8a);

	MD5_STEP(MD5_H, a, b, c, d, w5, 4, 0xfffa3942); MD5_STEP(MD5_H, d, a, b, c, w8, 11, 0x8771f681);
	MD5_STEP(MD5_H, c, d, a, b, w11, 16, 0x6d9d6122); MD5_STEP(MD5_H, b, c, d, a, w14, 23, 0xfde5380c);
	MD5_STEP(MD5_H, a, b, c, d, w1, 4, 0xa4beea44); MD5_STEP(MD5_H, d, a, b, c, w4, 11, 0x4bdecfa9);
	MD5_STEP(MD5_H, c, d, a, b, w7, 16, 0xf6bb4b60); MD5_STEP(MD5_H, b, c, d, a, w10, 23, 0xbebfbc70);
	MD5_STEP(MD5_H, a, b, c, d, w13, 4, 0x289b7ec6); MD5_STEP(MD5_H, d, a, b, c, w0, 11, 0xeaa127fa);
	MD5_STEP(MD5_H, c, d, a, b, w3, 16, 0xd4ef3085); MD5_STEP(MD5_H, b, c, d, a, w6, 23, 0x04881d05);
	MD5_STEP(MD5_H, a, b, c, d, w9, 4, 0xd9d4d039); MD5_STEP(MD5_H, d, a, b, c, w12, 11, 0xe6db99e5);
	MD5_STEP(MD5_H, c, d, a, b, w15, 16, 0x1fa27cf8); MD5_STEP(MD5_H, b, c, d, a, w2, 23, 0xc4ac5665);

	MD5_STEP(MD5_I, a, b, c, d, w0, 6, 0xf4292244); MD5_STEP(MD5_I, d, a, b, c, w7, 10, 0x432aff97);
	MD5_STEP(MD5_I, c, d, a, b, w14, 15, 0xab9423a7); MD5_STEP(MD5_I, b, c, d, a, w5, 21, 0xfc93a039);
	MD5_STEP(MD5_I, a, b, c, d, w12, 6, 0x655b59c3); MD5_STEP(MD5_I, d, a, b, c, w3, 10, 0x8f0ccc92);
	MD5_STEP(MD5_I, c, d, a, b, w10, 15, 0xffeff47d); MD5_STEP(MD5_I, b, c, d, a, w1, 21, 0x85845dd1);
	MD5_STEP(MD5_I, a, b, c, d, w8, 6, 0x6fa87e4f); MD5_STEP(MD5_I, d, a, b, c, w15, 10, 0xfe2ce6e0);
	MD5_STEP(MD5_I, c, d, a, b, w6, 15, 0xa3014314); MD5_STEP(MD5_I, b, c, d, a, w13, 21, 0x4e0811a1);
	MD5_STEP(MD5_I, a, b, c, d, w4, 6, 0xf7537e82); MD5_STEP(MD5_I, d, a, b, c, w11, 10, 0xbd3af235);
	MD5_STEP(MD5_I, c, d, a, b, w2, 15, 0x2ad7d2bb); MD5_STEP(MD5_I, b, c, d, a, w9, 21, 0xeb86d391);

	st[0] += a;
	st[1] += b;
	st[2] += c;
	st[3] += d;
}

static void md5_init(struct md5 *m)
{
	m->s[0] = 0x67452301u;
	m->s[1] = 0xefcdab89u;
	m->s[2] = 0x98badcfeu;
	m->s[3] = 0x10325476u;
	m->nbytes = 0;
	m->nbuf = 0;
}

static void md5_update(struct md5 *m, const void *data, unsigned int len)
{
	const unsigned char *p = data;

	m->nbytes += len;
	if (m->nbuf) {
		unsigned int take = 64 - m->nbuf;

		if (take > len)
			take = len;
		memcpy(m->buf + m->nbuf, p, take);
		m->nbuf += take;
		p += take;
		len -= take;
		if (m->nbuf == 64) {
			md5_block(m->s, m->buf);
			m->nbuf = 0;
		}
	}
	while (len >= 64) {
		unsigned int blocks = len >> 6;

		do {
			md5_block(m->s, p);
			p += 64;
		} while (--blocks);
		len &= 63;
	}
	if (len) {
		memcpy(m->buf + m->nbuf, p, len);
		m->nbuf += len;
	}
}

static void md5_final(struct md5 *m, unsigned char out[16])
{
	ULONGLONG bits = m->nbytes << 3;
	unsigned int n = m->nbuf, i;

	m->buf[n++] = 0x80;
	if (n > 56) {
		while (n < 64)
			m->buf[n++] = 0;
		md5_block(m->s, m->buf);
		n = 0;
	}
	while (n < 56)
		m->buf[n++] = 0;
	for (i = 0; i < 8; i++)
		m->buf[56 + i] = (unsigned char)(bits >> (8 * i));
	md5_block(m->s, m->buf);
	for (i = 0; i < 4; i++) {
		out[i * 4] = (unsigned char)m->s[i];
		out[i * 4 + 1] = (unsigned char)(m->s[i] >> 8);
		out[i * 4 + 2] = (unsigned char)(m->s[i] >> 16);
		out[i * 4 + 3] = (unsigned char)(m->s[i] >> 24);
	}
}

static DWORD bail(int report, LPCWSTR path, LPCWSTR what)
{
	DWORD e = GetLastError();

	if (!e)
		e = ERROR_GEN_FAILURE;
	if (report) {
		SetLastError(e);
		if (path)
			fail_path(path, what);
		else
			fail(what);
	}
	return e;
}

static int io_too_big(DWORD err)
{
	return err == ERROR_INVALID_PARAMETER
		|| err == ERROR_NO_SYSTEM_RESOURCES
		|| err == ERROR_NOT_ENOUGH_MEMORY
		|| err == ERROR_WORKING_SET_QUOTA;
}

static DWORD alloc_buffers(LPVOID buf[2])
{
	DWORD size;

	for (size = BLOCK_SIZE; size >= MIN_BLOCK; size >>= 1) {
		buf[0] = VirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
		buf[1] = VirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
		if (buf[0] && buf[1])
			return size;
		if (buf[0])
			VirtualFree(buf[0], 0, MEM_RELEASE);
		if (buf[1])
			VirtualFree(buf[1], 0, MEM_RELEASE);
		buf[0] = buf[1] = NULL;
	}
	return 0;
}

static DWORD io_chunk(ULONGLONG aligned, ULONGLONG at, DWORD xfer)
{
	ULONGLONG left = aligned - at;

	if (left > xfer)
		return xfer;
	return (DWORD)left;
}

static int set_eof(HANDLE file, ULONGLONG n)
{
	FILE_END_OF_FILE_INFO eof;
	FILE_ALLOCATION_INFO alloc;
	ULONGLONG reserve = (n + (ALIGN_SIZE - 1)) & ~(ULONGLONG)(ALIGN_SIZE - 1);

	if (reserve) {
		alloc.AllocationSize.QuadPart = (LONGLONG)reserve;
		SetFileInformationByHandle(file, FileAllocationInfo, &alloc, sizeof(alloc));
	}
	eof.EndOfFile.QuadPart = (LONGLONG)n;
	return SetFileInformationByHandle(file, FileEndOfFileInfo, &eof, sizeof(eof));
}

static int begin_io(HANDLE file, struct io_slot *op, int write, void *buf, DWORD len, ULONGLONG offset)
{
	BOOL ok;
	DWORD n = 0;

	op->pending = 0;
	op->want = len;
	op->got = 0;
	ZeroMemory(&op->ov, sizeof(op->ov));
	op->ov.Offset = (DWORD)offset;
	op->ov.OffsetHigh = (DWORD)(offset >> 32);
	op->ov.hEvent = op->ev;
	ResetEvent(op->ev);
	if (write)
		ok = WriteFile(file, buf, len, &n, &op->ov);
	else
		ok = ReadFile(file, buf, len, &n, &op->ov);
	if (!ok) {
		if (GetLastError() != ERROR_IO_PENDING)
			return 0;
		op->pending = 1;
		return 1;
	}
	op->got = n;
	return n == len;
}

static int end_io(HANDLE file, struct io_slot *op)
{
	DWORD n = op->got;

	if (op->pending) {
		if (!GetOverlappedResult(file, &op->ov, &n, TRUE)) {
			op->pending = 0;
			return 0;
		}
		op->pending = 0;
		op->got = n;
	}
	return n == op->want;
}

static void drop_io(HANDLE file, struct io_slot *op)
{
	DWORD n;

	if (!op->pending || file == INVALID_HANDLE_VALUE)
		return;
	CancelIoEx(file, &op->ov);
	GetOverlappedResult(file, &op->ov, &n, TRUE);
	op->pending = 0;
}

static int retry_begin(HANDLE file, struct io_slot *op, int write, void *buf, DWORD len, ULONGLONG offset)
{
	int attempt;

	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		if (begin_io(file, op, write, buf, len, offset))
			return 1;
	}
	return 0;
}

static int retry_end(HANDLE file, struct io_slot *op, int write, void *buf, DWORD len, ULONGLONG offset)
{
	int attempt;

	if (end_io(file, op))
		return 1;
	for (attempt = 1; attempt < IO_ATTEMPTS; attempt++) {
		drop_io(file, op);
		if (!begin_io(file, op, write, buf, len, offset))
			continue;
		if (end_io(file, op))
			return 1;
	}
	return 0;
}

static void show_progress(void)
{
	out_lock();
	fwprintf(stdout, L"%lld %lld\n", (long long)g_processed, (long long)g_files);
	fflush(stdout);
	out_unlock();
}

static void report_errors(void)
{
	if (!g_write_errors && !g_read_errors && !g_size_mismatches)
		return;
	out_lock();
	fwprintf(stderr,
		L"ERRORS occurred: %lld / %lld / %lld (WRITE ERRORS / READ ERRORS / SIZE MISMATCHES)\n",
		(long long)g_write_errors, (long long)g_read_errors, (long long)g_size_mismatches);
	out_unlock();
}

static void check_io_abort(void)
{
	if (g_read_errors > MAX_IO_ERRORS || g_write_errors > MAX_IO_ERRORS)
		InterlockedExchange(&g_io_error, 1);
}

static DWORD WINAPI progress_stdout(LPVOID param)
{
	HANDLE stop = param;

	for (;;) {
		if (WaitForSingleObject(stop, 1000) == WAIT_OBJECT_0)
			break;
		show_progress();
	}
	return 0;
}

static void tsv_write_error(void)
{
	DWORD e = GetLastError();

	if (!e)
		e = ERROR_GEN_FAILURE;
	InterlockedExchange(&g_io_error, 1);
	SetLastError(e);
	if (g_tsv_path)
		fail_path(g_tsv_path, L"Write tsv");
	else
		fail(L"Write tsv");
}

static int open_tsv(LPCWSTR path)
{
	DWORD attr = GetFileAttributesW(path);
	size_t n;
	int exists = 0;

	g_tsv_path = path;
	if (attr == INVALID_FILE_ATTRIBUTES) {
		DWORD e = GetLastError();

		if (e != ERROR_FILE_NOT_FOUND) {
			SetLastError(e);
			fail_path(path, L"Open tsv");
			return 1;
		}
	} else if (attr & FILE_ATTRIBUTE_DIRECTORY) {
		fwprintf(stderr, L"TSV path is not a file: %s\n", path);
		return 1;
	} else {
		exists = 1;
	}
	g_tsv = _wfopen(path, exists ? L"ab" : L"wb");
	if (!g_tsv) {
		fail_path(path, L"Open tsv");
		return 1;
	}
	if (exists)
		return 0;
	n = sizeof(g_tsv_header) - 1;
	if (fwrite(g_tsv_header, 1, n, g_tsv) != n || fflush(g_tsv) != 0) {
		fail_path(path, L"Write tsv");
		return 1;
	}
	return 0;
}

static void write_result(const BYTE md5[16], LPCWSTR rel, ULONGLONG src_size, ULONGLONG dst_size, int kind)
{
	char *rel8 = NULL;
	char *line = NULL;
	int n, i, pos;
	size_t len, cap;

	if (kind == 1) {
		InterlockedIncrement64(&g_read_errors);
		check_io_abort();
	} else if (kind == 2) {
		InterlockedIncrement64(&g_write_errors);
		check_io_abort();
	} else if (kind == 3)
		InterlockedIncrement64(&g_size_mismatches);
	n = WideCharToMultiByte(CP_UTF8, 0, rel, -1, NULL, 0, NULL, NULL);
	if (n <= 0) {
		tsv_write_error();
		return;
	}
	rel8 = (char *)LocalAlloc(LMEM_FIXED, (size_t)n);
	if (!rel8) {
		tsv_write_error();
		return;
	}
	if (!WideCharToMultiByte(CP_UTF8, 0, rel, -1, rel8, n, NULL, NULL)) {
		LocalFree(rel8);
		tsv_write_error();
		return;
	}
	len = strlen(rel8);
	cap = len + 128;
	line = (char *)LocalAlloc(LMEM_FIXED, cap);
	if (!line) {
		LocalFree(rel8);
		tsv_write_error();
		return;
	}
	pos = snprintf(line, cap, "\"%s\"\t", rel8);
	if (pos < 0 || (size_t)pos >= cap) {
		LocalFree(rel8);
		LocalFree(line);
		tsv_write_error();
		return;
	}
	if (kind == 1) {
		pos += snprintf(line + pos, cap - (size_t)pos, "ERROR\t%llu\tERROR\tREAD_ERROR\n",
			(unsigned long long)src_size);
	} else {
		for (i = 0; i < 16; i++)
			pos += snprintf(line + pos, cap - (size_t)pos, "%02x", md5[i]);
		if (kind == 2)
			pos += snprintf(line + pos, cap - (size_t)pos, "\t%llu\t%llu\tWRITE_ERROR\n",
				(unsigned long long)src_size, (unsigned long long)dst_size);
		else if (kind == 3)
			pos += snprintf(line + pos, cap - (size_t)pos, "\t%llu\t%llu\tSIZE_MISMATCH\n",
				(unsigned long long)src_size, (unsigned long long)dst_size);
		else
			pos += snprintf(line + pos, cap - (size_t)pos, "\t%llu\t%llu\tOK\n",
				(unsigned long long)src_size, (unsigned long long)dst_size);
	}
	if (pos < 0 || (size_t)pos >= cap) {
		LocalFree(rel8);
		LocalFree(line);
		tsv_write_error();
		return;
	}
	out_lock();
	if (!g_tsv || fwrite(line, 1, (size_t)pos, g_tsv) != (size_t)pos || fflush(g_tsv) != 0) {
		out_unlock();
		LocalFree(rel8);
		LocalFree(line);
		tsv_write_error();
		return;
	}
	out_unlock();
	LocalFree(rel8);
	LocalFree(line);
}

static int same_size(LPCWSTR src, LPCWSTR dst)
{
	WIN32_FILE_ATTRIBUTE_DATA a, b;
	ULONGLONG asz, bsz;

	if (!GetFileAttributesExW(src, GetFileExInfoStandard, &a))
		return 0;
	if (!GetFileAttributesExW(dst, GetFileExInfoStandard, &b))
		return 0;
	asz = ((ULONGLONG)a.nFileSizeHigh << 32) | a.nFileSizeLow;
	bsz = ((ULONGLONG)b.nFileSizeHigh << 32) | b.nFileSizeLow;
	return asz == bsz;
}

static void file_size(LPCWSTR path, ULONGLONG *size)
{
	WIN32_FILE_ATTRIBUTE_DATA a;

	if (GetFileAttributesExW(path, GetFileExInfoStandard, &a))
		*size = ((ULONGLONG)a.nFileSizeHigh << 32) | a.nFileSizeLow;
}

static DWORD copy_tail(LPCWSTR src_path, LPCWSTR dst_path, ULONGLONG offset, DWORD len,
	struct md5 *hash, int report, int *write_fail)
{
	HANDLE src = INVALID_HANDLE_VALUE, dst = INVALID_HANDLE_VALUE;
	unsigned char tail[ALIGN_SIZE];
	LARGE_INTEGER pos;
	DWORD got = 0, wrote = 0, err = 0;
	int attempt;

	*write_fail = 0;
	src = CreateFileW(src_path, GENERIC_READ, FILE_SHARE_READ, NULL,
		OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (src == INVALID_HANDLE_VALUE) {
		err = bail(report, src_path, L"Open source");
		goto done;
	}
	dst = CreateFileW(dst_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
		OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (dst == INVALID_HANDLE_VALUE) {
		*write_fail = 1;
		err = bail(report, dst_path, L"Open destination");
		goto done;
	}
	pos.QuadPart = (LONGLONG)offset;
	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		got = 0;
		if (SetFilePointerEx(src, pos, NULL, FILE_BEGIN)
			&& ReadFile(src, tail, len, &got, NULL) && got == len)
			break;
	}
	if (attempt == IO_ATTEMPTS) {
		err = bail(report, src_path, L"Read");
		goto done;
	}
	md5_update(hash, tail, len);
	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		wrote = 0;
		if (SetFilePointerEx(dst, pos, NULL, FILE_BEGIN)
			&& WriteFile(dst, tail, len, &wrote, NULL) && wrote == len)
			break;
	}
	if (attempt == IO_ATTEMPTS) {
		*write_fail = 1;
		err = bail(report, dst_path, L"Write");
		goto done;
	}
	InterlockedAdd64(&g_processed, (LONG64)len);

done:
	if (src != INVALID_HANDLE_VALUE)
		CloseHandle(src);
	if (dst != INVALID_HANDLE_VALUE)
		CloseHandle(dst);
	return err;
}

static DWORD copy_file(LPCWSTR src_path, LPCWSTR dst_path, LPVOID buf[2], BYTE md5out[16],
	ULONGLONG *copied, DWORD xfer, int report, int *write_fail)
{
	int reading = 0, writing = 0, slot = 0, wr_slot = 0, writing_failed = 0, tail_write = 0;
	HANDLE src = INVALID_HANDLE_VALUE, dst = INVALID_HANDLE_VALUE;
	struct io_slot rd, wr;
	struct md5 hash;
	LARGE_INTEGER size;
	ULONGLONG logical, aligned, rd_at = 0, wr_at = 0, wr_off = 0;
	DWORD rd_len = 0, wr_len = 0, err = 0;
	DWORD flags = FILE_FLAG_OVERLAPPED | FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN;

	ZeroMemory(&rd, sizeof(rd));
	ZeroMemory(&wr, sizeof(wr));
	md5_init(&hash);

	src = CreateFileW(src_path, GENERIC_READ, FILE_SHARE_READ, NULL,
		OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (src == INVALID_HANDLE_VALUE) {
		err = bail(report, src_path, L"Open source");
		goto done;
	}
	if (!GetFileSizeEx(src, &size)) {
		err = bail(report, src_path, L"Read size");
		goto done;
	}
	CloseHandle(src);
	src = INVALID_HANDLE_VALUE;
	logical = (ULONGLONG)size.QuadPart;
	aligned = logical & ~(ULONGLONG)(ALIGN_SIZE - 1);

	SetFileAttributesW(dst_path, FILE_ATTRIBUTE_NORMAL);
	dst = CreateFileW(dst_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
		CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
	if (dst == INVALID_HANDLE_VALUE) {
		writing_failed = 1;
		err = bail(report, dst_path, L"Open destination");
		goto done;
	}
	if (!set_eof(dst, logical)) {
		writing_failed = 1;
		err = bail(report, dst_path, L"Preallocate destination");
		goto done;
	}

	if (aligned) {
		CloseHandle(dst);
		dst = INVALID_HANDLE_VALUE;
		rd.ev = CreateEventW(NULL, TRUE, FALSE, NULL);
		wr.ev = CreateEventW(NULL, TRUE, FALSE, NULL);
		if (!rd.ev || !wr.ev) {
			writing_failed = 1;
			err = bail(report, NULL, L"Create event");
			goto done;
		}
		src = CreateFileW(src_path, GENERIC_READ, FILE_SHARE_READ, NULL,
			OPEN_EXISTING, flags, NULL);
		dst = CreateFileW(dst_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
			OPEN_EXISTING, flags, NULL);
		if (src == INVALID_HANDLE_VALUE) {
			err = bail(report, src_path, L"Open source");
			goto done;
		}
		if (dst == INVALID_HANDLE_VALUE) {
			writing_failed = 1;
			err = bail(report, dst_path, L"Open destination");
			goto done;
		}
		rd_len = io_chunk(aligned, 0, xfer);
		if (!retry_begin(src, &rd, 0, buf[0], rd_len, 0)) {
			err = bail(report, src_path, L"Read");
			goto done;
		}
		reading = 1;
	}

	while (reading || writing) {
		if (reading) {
			DWORD hash_len;
			int hash_slot;

			if (!retry_end(src, &rd, 0, buf[slot], rd_len, rd_at)) {
				err = bail(report, src_path, L"Read");
				goto done;
			}
			reading = 0;
			if (writing) {
				if (!retry_end(dst, &wr, 1, buf[wr_slot], wr_len, wr_off)) {
					writing_failed = 1;
					err = bail(report, dst_path, L"Write");
					goto done;
				}
				writing = 0;
				InterlockedAdd64(&g_processed, (LONG64)wr_len);
			}
			wr_slot = slot;
			wr_len = rd_len;
			wr_off = wr_at;
			if (!retry_begin(dst, &wr, 1, buf[slot], rd_len, wr_at)) {
				writing_failed = 1;
				err = bail(report, dst_path, L"Write");
				goto done;
			}
			writing = 1;
			wr_at += rd_len;
			hash_slot = slot;
			hash_len = rd_len;
			rd_at += rd_len;
			if (rd_at < aligned) {
				slot ^= 1;
				rd_len = io_chunk(aligned, rd_at, xfer);
				if (!retry_begin(src, &rd, 0, buf[slot], rd_len, rd_at)) {
					err = bail(report, src_path, L"Read");
					goto done;
				}
				reading = 1;
			}
			md5_update(&hash, buf[hash_slot], hash_len);
		} else if (writing) {
			if (!retry_end(dst, &wr, 1, buf[wr_slot], wr_len, wr_off)) {
				writing_failed = 1;
				err = bail(report, dst_path, L"Write");
				goto done;
			}
			writing = 0;
			InterlockedAdd64(&g_processed, (LONG64)wr_len);
		}
	}

	drop_io(src, &rd);
	drop_io(dst, &wr);
	if (src != INVALID_HANDLE_VALUE) {
		CloseHandle(src);
		src = INVALID_HANDLE_VALUE;
	}
	if (dst != INVALID_HANDLE_VALUE) {
		CloseHandle(dst);
		dst = INVALID_HANDLE_VALUE;
	}

	if (logical > aligned) {
		err = copy_tail(src_path, dst_path, aligned, (DWORD)(logical - aligned), &hash, report, &tail_write);
		if (err) {
			writing_failed = tail_write;
			goto done;
		}
	}

	md5_final(&hash, md5out);
	if (copied)
		*copied = logical;

done:
	if (write_fail)
		*write_fail = writing_failed;
	drop_io(src, &rd);
	drop_io(dst, &wr);
	if (rd.ev)
		CloseHandle(rd.ev);
	if (wr.ev)
		CloseHandle(wr.ev);
	if (src != INVALID_HANDLE_VALUE)
		CloseHandle(src);
	if (dst != INVALID_HANDLE_VALUE)
		CloseHandle(dst);
	return err;
}

struct job {
	LPWSTR src;
	LPWSTR dst;
	LPWSTR rel;
	struct job *next;
};

struct job_queue {
	struct job *head;
	struct job *tail;
	CRITICAL_SECTION lock;
	HANDLE sem;
	HANDLE init_sem;
	volatile LONG failed;
	volatile LONG ready;
};

static int task_count(void)
{
	SYSTEM_INFO si;
	DWORD n;

	GetSystemInfo(&si);
	n = si.dwNumberOfProcessors;
	if (n < 2)
		n = 2;
	if (n > MAX_TASKS)
		n = MAX_TASKS;
	return (int)n;
}

static int enqueue(struct job_queue *q, LPWSTR src, LPWSTR dst, LPWSTR rel)
{
	struct job *j = (struct job *)LocalAlloc(LMEM_FIXED, sizeof(*j));

	if (!j)
		return 1;
	j->src = src;
	j->dst = dst;
	j->rel = rel;
	j->next = NULL;
	EnterCriticalSection(&q->lock);
	if (q->tail)
		q->tail->next = j;
	else
		q->head = j;
	q->tail = j;
	LeaveCriticalSection(&q->lock);
	ReleaseSemaphore(q->sem, 1, NULL);
	return 0;
}

static int queue_file(LPCWSTR src, LPCWSTR dst_dir, struct job_queue *q)
{
	LPCWSTR name = basename_w(src);
	LPWSTR src_dup = wcsdup_w(src);
	LPWSTR dst = join_dir_file(dst_dir, name);
	LPWSTR rel = wcsdup_w(name);

	if (!src_dup || !dst || !rel) {
		if (src_dup)
			LocalFree(src_dup);
		if (dst)
			LocalFree(dst);
		if (rel)
			LocalFree(rel);
		fail(L"Build path");
		return 1;
	}
	if (enqueue(q, src_dup, dst, rel)) {
		LocalFree(src_dup);
		LocalFree(dst);
		LocalFree(rel);
		fail(L"Queue file");
		return 1;
	}
	return 0;
}

static struct job *dequeue(struct job_queue *q)
{
	struct job *j;

	WaitForSingleObject(q->sem, INFINITE);
	EnterCriticalSection(&q->lock);
	j = q->head;
	if (j) {
		q->head = j->next;
		if (!q->head)
			q->tail = NULL;
	}
	LeaveCriticalSection(&q->lock);
	return j;
}

static void free_jobs(struct job_queue *q)
{
	struct job *j = q->head;

	while (j) {
		struct job *next = j->next;

		if (j->src)
			LocalFree(j->src);
		if (j->dst)
			LocalFree(j->dst);
		if (j->rel)
			LocalFree(j->rel);
		LocalFree(j);
		j = next;
	}
	q->head = q->tail = NULL;
}

static DWORD hash_file(LPCWSTR src_path, LPVOID buf, DWORD xfer, BYTE md5out[16], ULONGLONG *size_out)
{
	HANDLE src = INVALID_HANDLE_VALUE;
	struct md5 hash;
	LARGE_INTEGER size;
	ULONGLONG left;
	DWORD err = 0;
	int attempt;

	src = CreateFileW(src_path, GENERIC_READ, FILE_SHARE_READ, NULL,
		OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
	if (src == INVALID_HANDLE_VALUE)
		return GetLastError();
	if (!GetFileSizeEx(src, &size)) {
		err = GetLastError();
		CloseHandle(src);
		return err;
	}
	left = (ULONGLONG)size.QuadPart;
	md5_init(&hash);
	while (left) {
		LARGE_INTEGER pos;
		DWORD want = left > xfer ? xfer : (DWORD)left;
		DWORD got = 0;
		ULONGLONG at = (ULONGLONG)size.QuadPart - left;

		pos.QuadPart = (LONGLONG)at;
		for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
			got = 0;
			if (SetFilePointerEx(src, pos, NULL, FILE_BEGIN)
				&& ReadFile(src, buf, want, &got, NULL) && got == want)
				break;
		}
		if (attempt == IO_ATTEMPTS) {
			err = GetLastError();
			if (!err)
				err = ERROR_GEN_FAILURE;
			CloseHandle(src);
			return err;
		}
		md5_update(&hash, buf, want);
		left -= want;
	}
	md5_final(&hash, md5out);
	if (size_out)
		*size_out = (ULONGLONG)size.QuadPart;
	CloseHandle(src);
	return 0;
}

static DWORD WINAPI copy_task(LPVOID param)
{
	struct job_queue *q = param;
	LPVOID buf[2] = {NULL, NULL};
	BYTE md5[16];
	ULONGLONG copied = 0;
	DWORD xfer;

	xfer = alloc_buffers(buf);
	if (xfer)
		InterlockedIncrement(&q->ready);
	ReleaseSemaphore(q->init_sem, 1, NULL);
	if (!xfer)
		return 0;

	for (;;) {
		struct job *j = dequeue(q);
		DWORD use, err;
		int write_fail;

		if (!j || !j->src) {
			if (j)
				LocalFree(j);
			break;
		}
		if (g_io_error) {
			LocalFree(j->src);
			LocalFree(j->dst);
			LocalFree(j->rel);
			LocalFree(j);
			continue;
		}
		use = xfer;
		err = 0;
		write_fail = 0;
		for (;;) {
			int last = use <= MIN_BLOCK;

			err = copy_file(j->src, j->dst, buf, md5, &copied, use, last, &write_fail);
			if (!err)
				break;
			if (last || !io_too_big(err)) {
				if (!last) {
					SetLastError(err);
					fail_path(j->src, L"Copy");
				}
				break;
			}
			use >>= 1;
		}
		if (!err) {
			xfer = use;
			if (!same_size(j->src, j->dst)) {
				ULONGLONG src_sz = copied, dst_sz = 0;

				file_size(j->src, &src_sz);
				file_size(j->dst, &dst_sz);
				write_result(md5, j->rel, src_sz, dst_sz, 3);
			} else {
				InterlockedIncrement64(&g_files);
				write_result(md5, j->rel, copied, copied, 0);
			}
		} else if (write_fail && !hash_file(j->src, buf[0], xfer, md5, &copied)) {
			ULONGLONG dst_sz = 0;

			file_size(j->dst, &dst_sz);
			write_result(md5, j->rel, copied, dst_sz, 2);
		} else {
			ULONGLONG src_sz = 0;

			file_size(j->src, &src_sz);
			write_result(NULL, j->rel, src_sz, 0, 1);
		}
		LocalFree(j->src);
		LocalFree(j->dst);
		LocalFree(j->rel);
		LocalFree(j);
	}
	if (buf[0])
		VirtualFree(buf[0], 0, MEM_RELEASE);
	if (buf[1])
		VirtualFree(buf[1], 0, MEM_RELEASE);
	return 0;
}

static int copy_tree(LPCWSTR src, LPCWSTR dst, LPCWSTR rel, struct job_queue *q)
{
	WIN32_FIND_DATAW fd;
	HANDLE find = INVALID_HANDLE_VALUE;
	LPWSTR pattern = NULL;
	int rc = 1;
	DWORD err;

	pattern = join_dir_file(src, L"*");
	if (!pattern) {
		fail(L"Build search path");
		return 1;
	}
	find = FindFirstFileW(pattern, &fd);
	if (find == INVALID_HANDLE_VALUE) {
		err = GetLastError();
		LocalFree(pattern);
		if (err == ERROR_FILE_NOT_FOUND)
			return 0;
		SetLastError(err);
		fail_path(src, L"List directory");
		return 1;
	}

	rc = 0;
	do {
		LPWSTR child_src = NULL;
		LPWSTR child_dst = NULL;
		LPWSTR child_rel = NULL;
		DWORD e, attr;

		if (g_io_error) {
			rc = 1;
			break;
		}
		if (fd.cFileName[0] == L'.' && (fd.cFileName[1] == 0
			|| (fd.cFileName[1] == L'.' && fd.cFileName[2] == 0)))
			continue;

		child_src = join_dir_file(src, fd.cFileName);
		child_dst = join_dir_file(dst, fd.cFileName);
		if (rel[0])
			child_rel = join_dir_file(rel, fd.cFileName);
		else
			child_rel = wcsdup_w(fd.cFileName);
		if (!child_src || !child_dst || !child_rel) {
			fail(L"Build path");
			rc = 1;
			goto next;
		}

		if (fd.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
			goto next;

		if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
			if (!CreateDirectoryW(child_dst, NULL)) {
				e = GetLastError();
				if (e != ERROR_ALREADY_EXISTS) {
					SetLastError(e);
					fail_path(child_dst, L"Create directory");
					rc = 1;
					goto next;
				}
				attr = GetFileAttributesW(child_dst);
				if (attr == INVALID_FILE_ATTRIBUTES || !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
					out_lock();
					fwprintf(stderr, L"Destination is not a directory: %s\n", child_dst);
					out_unlock();
					rc = 1;
					goto next;
				}
			}
			if (copy_tree(child_src, child_dst, child_rel, q))
				rc = 1;
		} else if (enqueue(q, child_src, child_dst, child_rel)) {
			fail(L"Queue file");
			rc = 1;
		} else {
			child_src = NULL;
			child_dst = NULL;
			child_rel = NULL;
		}

	next:
		if (child_src)
			LocalFree(child_src);
		if (child_dst)
			LocalFree(child_dst);
		if (child_rel)
			LocalFree(child_rel);
		if (rc)
			break;
	} while (FindNextFileW(find, &fd));

	if (!rc) {
		err = GetLastError();
		if (err != ERROR_NO_MORE_FILES) {
			SetLastError(err);
			fail_path(src, L"List directory");
			rc = 1;
		}
	}
	FindClose(find);
	LocalFree(pattern);
	return rc;
}

static void help(void)
{
	fwprintf(stdout,
		L"copymd5 for Windows Version %hs\n"
		L"Copy one file or directory into a destination directory.\n"
		L"A directory is copied recursively.\n"
		L"\n"
		L"Usage: copymd5 <source directory or file> <destination directory> <tsv file>\n"
		L"       copymd5 /?\n"
		L"\n"
		L"A source directory is created inside the destination under its own name.\n"
		L"A source file is copied into the destination directory.\n"
		L"Paths may use \\ or / and may end with a slash.\n"
		L"\n"
		L"Each file appends one tab-separated line to the tsv file:\n"
		L"\"relative\\path\"\t<md5>\t<source size>\t<destination size>\tOK\n"
		L"A failed read:\n"
		L"\"relative\\path\"\tERROR\t<source size>\tERROR\tREAD_ERROR\n"
		L"A failed write:\n"
		L"\"relative\\path\"\t<md5>\t<source size>\t<destination size>\tWRITE_ERROR\n"
		L"A size mismatch:\n"
		L"\"relative\\path\"\t<md5>\t<source size>\t<destination size>\tSIZE_MISMATCH\n"
		L"\n"
		L"A new tsv file starts with this header:\n"
		L"Path\tMD5\tSourceSize\tDestinationSize\tResult\n"
		L"An existing tsv file is appended to.\n"
		L"\n"
		L"Stdout prints <bytes> <files> and is flushed once a second.\n"
		L"Up to 20 read errors and 20 write errors are tolerated; the run aborts only when\n"
		L"either count goes past that. Size mismatches are recorded and never abort.\n"
		L"When any file fails, stderr ends with:\n"
		L"ERRORS occurred: <write> / <read> / <size mismatch> (WRITE ERRORS / READ ERRORS / SIZE MISMATCHES)\n"
		L"The exit code is 0 when every file copies, and 1 when any read, write, size check,\n"
		L"or abort threshold is hit.\n",
		VERSION);
}

int main(void)
{
	int argc, rc = 1, ntasks, started = 0, t, src_is_dir = 0;
	LPWSTR *argv;
	LPWSTR src_full = NULL, dst_full = NULL, dst_root = NULL, tsv_full = NULL;
	LPCWSTR src_name;
	struct job_queue queue;
	HANDLE threads[MAX_TASKS];
	HANDLE progress_stop = NULL, progress_thread = NULL;
	DWORD attr, err;
	int queue_ready = 0;

	_setmode(_fileno(stdout), _O_U8TEXT);
	_setmode(_fileno(stderr), _O_U8TEXT);

	argv = CommandLineToArgvW(GetCommandLineW(), &argc);
	if (!argv) {
		fwprintf(stderr, L"Usage: copymd5 <source directory or file> <destination directory> <tsv file>\n");
		return 1;
	}
	if (argc == 2 && lstrcmpW(argv[1], L"/?") == 0) {
		help();
		LocalFree(argv);
		return 0;
	}
	if (argc != 4) {
		fwprintf(stderr, L"Usage: copymd5 <source directory or file> <destination directory> <tsv file>\n");
		fwprintf(stderr, L"       copymd5 /?\n");
		LocalFree(argv);
		return 1;
	}

	src_full = full_path(argv[1]);
	if (!src_full) {
		fail(L"Resolve path");
		goto done;
	}
	dst_full = full_path(argv[2]);
	if (!dst_full) {
		fail(L"Resolve path");
		goto done;
	}
	tsv_full = full_path(argv[3]);
	if (!tsv_full) {
		fail(L"Resolve path");
		goto done;
	}

	attr = GetFileAttributesW(src_full);
	if (attr == INVALID_FILE_ATTRIBUTES) {
		fail_path(src_full, L"Source");
		goto done;
	}
	src_is_dir = (attr & FILE_ATTRIBUTE_DIRECTORY) != 0;

	attr = GetFileAttributesW(dst_full);
	if (attr == INVALID_FILE_ATTRIBUTES) {
		fail_path(dst_full, L"Destination directory");
		goto done;
	}
	if (!(attr & FILE_ATTRIBUTE_DIRECTORY)) {
		fwprintf(stderr, L"Destination is not a directory\n");
		goto done;
	}

	if (src_is_dir) {
		src_name = basename_w(src_full);
		if (!src_name[0]) {
			fwprintf(stderr, L"Source path has no directory name\n");
			goto done;
		}
		dst_root = join_dir_file(dst_full, src_name);
		if (!dst_root) {
			fail(L"Build destination path");
			goto done;
		}
		if (is_same_or_child(src_full, dst_root)) {
			fwprintf(stderr, L"Destination is inside the source directory\n");
			goto done;
		}
		if (!CreateDirectoryW(dst_root, NULL)) {
			err = GetLastError();
			if (err != ERROR_ALREADY_EXISTS) {
				SetLastError(err);
				fail_path(dst_root, L"Create directory");
				goto done;
			}
			attr = GetFileAttributesW(dst_root);
			if (attr == INVALID_FILE_ATTRIBUTES || !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
				fwprintf(stderr, L"Destination is not a directory: %s\n", dst_root);
				goto done;
			}
		}
	} else {
		LPWSTR dst_file = join_dir_file(dst_full, basename_w(src_full));

		if (!dst_file) {
			fail(L"Build destination path");
			goto done;
		}
		if (CompareStringOrdinal(src_full, -1, dst_file, -1, TRUE) == CSTR_EQUAL) {
			fwprintf(stderr, L"Source and destination are the same file\n");
			LocalFree(dst_file);
			goto done;
		}
		LocalFree(dst_file);
		dst_root = wcsdup_w(dst_full);
		if (!dst_root) {
			fail(L"Build destination path");
			goto done;
		}
	}
	if (open_tsv(tsv_full))
		goto done;

	ZeroMemory(&queue, sizeof(queue));
	InitializeCriticalSection(&queue.lock);
	queue.sem = CreateSemaphoreW(NULL, 0, 0x7fffffff, NULL);
	queue.init_sem = CreateSemaphoreW(NULL, 0, MAX_TASKS, NULL);
	if (!queue.sem || !queue.init_sem) {
		if (queue.sem)
			CloseHandle(queue.sem);
		if (queue.init_sem)
			CloseHandle(queue.init_sem);
		DeleteCriticalSection(&queue.lock);
		fail(L"Create queue");
		goto done;
	}
	queue_ready = 1;
	InitializeCriticalSection(&g_out_lock);
	g_out_lock_ready = 1;

	ntasks = task_count();
	started = 0;
	for (t = 0; t < ntasks; t++) {
		threads[t] = CreateThread(NULL, 0, copy_task, &queue, 0, NULL);
		if (!threads[t])
			break;
		started++;
	}
	if (!started) {
		fail(L"Start task");
		goto done;
	}
	for (t = 0; t < started; t++)
		WaitForSingleObject(queue.init_sem, INFINITE);
	if (!queue.ready) {
		for (t = 0; t < started; t++) {
			WaitForSingleObject(threads[t], INFINITE);
			CloseHandle(threads[t]);
		}
		started = 0;
		fail(L"Allocate buffer");
		goto done;
	}

	progress_stop = CreateEventW(NULL, TRUE, FALSE, NULL);
	if (progress_stop)
		progress_thread = CreateThread(NULL, 0, progress_stdout, progress_stop, 0, NULL);
	if (src_is_dir) {
		if (copy_tree(src_full, dst_root, L"", &queue))
			InterlockedExchange(&queue.failed, 1);
	} else if (queue_file(src_full, dst_root, &queue)) {
		InterlockedExchange(&queue.failed, 1);
	}
	for (t = 0; t < queue.ready; t++)
		enqueue(&queue, NULL, NULL, NULL);
	for (t = 0; t < started; t++) {
		WaitForSingleObject(threads[t], INFINITE);
		CloseHandle(threads[t]);
	}
	started = 0;
	if (progress_stop)
		SetEvent(progress_stop);
	if (progress_thread) {
		WaitForSingleObject(progress_thread, INFINITE);
		CloseHandle(progress_thread);
		progress_thread = NULL;
	}
	show_progress();
	report_errors();
	rc = (g_io_error || queue.failed || g_read_errors || g_write_errors || g_size_mismatches) ? 1 : 0;

done:
	if (progress_thread) {
		if (progress_stop)
			SetEvent(progress_stop);
		WaitForSingleObject(progress_thread, INFINITE);
		CloseHandle(progress_thread);
	}
	if (progress_stop)
		CloseHandle(progress_stop);
	if (queue_ready) {
		if (!started)
			free_jobs(&queue);
		CloseHandle(queue.sem);
		CloseHandle(queue.init_sem);
		DeleteCriticalSection(&queue.lock);
	}
	if (g_out_lock_ready) {
		DeleteCriticalSection(&g_out_lock);
		g_out_lock_ready = 0;
	}
	if (g_tsv && fclose(g_tsv) != 0) {
		g_tsv = NULL;
		tsv_write_error();
		rc = 1;
	}
	g_tsv = NULL;
	if (dst_root)
		LocalFree(dst_root);
	if (src_full)
		LocalFree(src_full);
	if (dst_full)
		LocalFree(dst_full);
	if (tsv_full)
		LocalFree(tsv_full);
	if (argv)
		LocalFree(argv);
	return rc;
}
