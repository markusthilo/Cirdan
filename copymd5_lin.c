/* Recursively copy a source directory into a destination directory.
 * Several files are copied at once. Each file uses overlapped transfers
 * (512 MiB when that buffer can be allocated) and a direct MD5.
 * For each file, prints the relative path in quotes, a tab, the digest, a
 * tab, the size in bytes, a tab, and OK. A failed read prints FAILED, FAILED,
 * and ERROR. A failed write prints the digest, the size, and ERROR.
 * A size mismatch prints the digest, ERROR, and ERROR.
 * Stdout is flushed once a second. A blank line follows, then a summary of
 * the file count, byte count, and elapsed time.
 *
 * gcc -O2 -o copymd5 copymd5_lin.c -pthread
 */

#define VERSION "0.0.1-2026-10-06"

#define _GNU_SOURCE
#define _FILE_OFFSET_BITS 64

#include <aio.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <semaphore.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define MD5_ROTL(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

#define ALIGN_SIZE 4096u
#define BLOCK_SIZE (512u << 20)
#define MIN_BLOCK (1u << 20)
#define IO_ATTEMPTS 3
#define MAX_TASKS 8

static pthread_mutex_t g_out_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t g_flush_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t g_flush_cond = PTHREAD_COND_INITIALIZER;
static int g_flush_stop;
static long long g_files;
static long long g_bytes;
static int g_io_error;

struct md5 {
	unsigned int s[4];
	unsigned char buf[64];
	unsigned long long nbytes;
	unsigned int nbuf;
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
	unsigned long long bits = m->nbytes << 3;
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

static void fail(const char *what)
{
	int e = errno;

	pthread_mutex_lock(&g_out_lock);
	fprintf(stderr, "%s failed: %d\n", what, e);
	pthread_mutex_unlock(&g_out_lock);
}

static void fail_path(const char *path, const char *what)
{
	int e = errno;

	pthread_mutex_lock(&g_out_lock);
	fprintf(stderr, "%s: %s failed: %d\n", path, what, e);
	pthread_mutex_unlock(&g_out_lock);
}

static int bail(int report, const char *path, const char *what)
{
	int e = errno;

	if (!e)
		e = EIO;
	if (report) {
		errno = e;
		if (path)
			fail_path(path, what);
		else
			fail(what);
	}
	return e;
}

static int io_too_big(int err)
{
	return err == ENOMEM || err == ENOBUFS || err == EAGAIN || err == EMSGSIZE;
}

static int direct_rejected(int err)
{
	return err == EINVAL || err == EOPNOTSUPP || err == ENOTSUP
		|| err == EPERM || err == ENODEV;
}

static const char *basename_p(const char *path)
{
	const char *name = path;

	for (; *path; path++) {
		if (*path == '/')
			name = path + 1;
	}
	return name;
}

static char *join_dir_file(const char *dir, const char *name)
{
	size_t dlen = strlen(dir);
	size_t nlen = strlen(name);
	int sep = !(dlen == 0 || dir[dlen - 1] == '/');
	char *out = malloc(dlen + (size_t)sep + nlen + 1);

	if (!out)
		return NULL;
	memcpy(out, dir, dlen);
	if (sep)
		out[dlen] = '/';
	memcpy(out + dlen + (size_t)sep, name, nlen + 1);
	return out;
}

static void strip_dir_slash(char *path)
{
	size_t n = strlen(path);

	while (n > 1 && path[n - 1] == '/')
		path[--n] = 0;
}

static char *full_path(const char *path)
{
	char *out = realpath(path, NULL);

	if (out)
		strip_dir_slash(out);
	return out;
}

static int is_same_or_child(const char *parent, const char *child)
{
	size_t plen = strlen(parent);
	size_t clen = strlen(child);

	if (plen == 1 && parent[0] == '/')
		return 1;
	if (clen < plen || memcmp(parent, child, plen) != 0)
		return 0;
	return clen == plen || child[plen] == '/';
}

static size_t io_chunk(unsigned long long aligned, unsigned long long at, size_t xfer)
{
	unsigned long long left = aligned - at;

	if (left > xfer)
		return xfer;
	return (size_t)left;
}

static size_t alloc_buffers(void *buf[2])
{
	size_t size;

	for (size = BLOCK_SIZE; size >= MIN_BLOCK; size >>= 1) {
		buf[0] = buf[1] = NULL;
		if (posix_memalign(&buf[0], ALIGN_SIZE, size) != 0)
			buf[0] = NULL;
		if (posix_memalign(&buf[1], ALIGN_SIZE, size) != 0)
			buf[1] = NULL;
		if (buf[0] && buf[1])
			return size;
		free(buf[0]);
		free(buf[1]);
		buf[0] = buf[1] = NULL;
	}
	return 0;
}

struct io_slot {
	struct aiocb cb;
	int pending;
	void *buf;
	size_t len;
	off_t off;
	int write;
};

static void drop_io(struct io_slot *op)
{
	const struct aiocb *list;

	if (!op->pending)
		return;
	aio_cancel(op->cb.aio_fildes, &op->cb);
	list = &op->cb;
	while (aio_error(&op->cb) == EINPROGRESS)
		aio_suspend(&list, 1, NULL);
	aio_return(&op->cb);
	op->pending = 0;
}

static int begin_slot(struct io_slot *op, int fd, int write, void *buf, size_t len, off_t off)
{
	memset(&op->cb, 0, sizeof(op->cb));
	op->cb.aio_fildes = fd;
	op->cb.aio_buf = buf;
	op->cb.aio_nbytes = len;
	op->cb.aio_offset = off;
	op->cb.aio_sigevent.sigev_notify = SIGEV_NONE;
	op->buf = buf;
	op->len = len;
	op->off = off;
	op->write = write;
	op->pending = 0;
	if ((write ? aio_write(&op->cb) : aio_read(&op->cb)) != 0)
		return errno ? errno : EIO;
	op->pending = 1;
	return 0;
}

static int end_slot(struct io_slot *op)
{
	const struct aiocb *list;
	int e;
	ssize_t n;

	if (!op->pending)
		return 0;
	list = &op->cb;
	while ((e = aio_error(&op->cb)) == EINPROGRESS) {
		if (aio_suspend(&list, 1, NULL) != 0 && errno != EINTR)
			return errno ? errno : EIO;
	}
	n = aio_return(&op->cb);
	op->pending = 0;
	if (e != 0)
		return e;
	if (n != (ssize_t)op->len)
		return EIO;
	return 0;
}

static int retry_begin(struct io_slot *op, int fd, int write, void *buf, size_t len, off_t off)
{
	int attempt, err = EIO;

	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		err = begin_slot(op, fd, write, buf, len, off);
		if (!err)
			return 0;
	}
	errno = err;
	return err;
}

static int retry_end(struct io_slot *op, int fd)
{
	int attempt, err;

	err = end_slot(op);
	if (!err)
		return 0;
	for (attempt = 1; attempt < IO_ATTEMPTS; attempt++) {
		drop_io(op);
		err = begin_slot(op, fd, op->write, op->buf, op->len, op->off);
		if (err)
			continue;
		err = end_slot(op);
		if (!err)
			return 0;
	}
	errno = err;
	return err;
}

static int copy_tail(const char *src_path, const char *dst_path, unsigned long long offset,
	size_t len, struct md5 *hash, int report, int *write_fail)
{
	unsigned char tail[ALIGN_SIZE];
	int src = -1, dst = -1, attempt, err = 0;
	ssize_t n;

	*write_fail = 0;
	src = open(src_path, O_RDONLY);
	if (src < 0) {
		err = bail(report, src_path, "Open source");
		goto done;
	}
	dst = open(dst_path, O_WRONLY);
	if (dst < 0) {
		*write_fail = 1;
		err = bail(report, dst_path, "Open destination");
		goto done;
	}
	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		n = pread(src, tail, len, (off_t)offset);
		if (n == (ssize_t)len)
			break;
	}
	if (attempt == IO_ATTEMPTS) {
		err = bail(report, src_path, "Read");
		goto done;
	}
	md5_update(hash, tail, (unsigned int)len);
	for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
		n = pwrite(dst, tail, len, (off_t)offset);
		if (n == (ssize_t)len)
			break;
	}
	if (attempt == IO_ATTEMPTS) {
		*write_fail = 1;
		err = bail(report, dst_path, "Write");
		goto done;
	}

done:
	if (src >= 0)
		close(src);
	if (dst >= 0)
		close(dst);
	return err;
}

static int copy_file_mode(const char *src_path, const char *dst_path, void *buf[2],
	unsigned char md5out[16], unsigned long long *copied, size_t xfer, int report,
	int *write_fail, int direct)
{
	int src = -1, dst = -1, reading = 0, writing = 0, slot = 0;
	int err = 0, extra = direct ? O_DIRECT : 0;
	struct io_slot rd, wr;
	struct md5 hash;
	struct stat st;
	unsigned long long logical, aligned, rd_at = 0, wr_at = 0;
	size_t rd_len = 0;

	*write_fail = 0;
	memset(&rd, 0, sizeof(rd));
	memset(&wr, 0, sizeof(wr));
	md5_init(&hash);

	src = open(src_path, O_RDONLY | extra);
	if (src < 0) {
		err = bail(report, src_path, "Open source");
		goto done;
	}
	if (fstat(src, &st) != 0) {
		err = bail(report, src_path, "Read size");
		goto done;
	}
	logical = (unsigned long long)st.st_size;
	chmod(dst_path, 0666);
	dst = open(dst_path, O_WRONLY | O_CREAT | O_TRUNC | extra, 0666);
	if (dst < 0) {
		*write_fail = 1;
		err = bail(report, dst_path, "Open destination");
		goto done;
	}
	if (ftruncate(dst, (off_t)logical) != 0) {
		*write_fail = 1;
		err = bail(report, dst_path, "Preallocate destination");
		goto done;
	}
	if (!direct)
		posix_fadvise(src, 0, 0, POSIX_FADV_SEQUENTIAL);
	aligned = direct ? (logical & ~(unsigned long long)(ALIGN_SIZE - 1)) : logical;

	if (aligned) {
		rd_len = io_chunk(aligned, 0, xfer);
		err = retry_begin(&rd, src, 0, buf[0], rd_len, 0);
		if (err) {
			errno = err;
			err = bail(report, src_path, "Read");
			goto done;
		}
		reading = 1;
	}

	while (reading || writing) {
		if (reading) {
			size_t hash_len;
			int hash_slot;

			err = retry_end(&rd, src);
			if (err) {
				errno = err;
				err = bail(report, src_path, "Read");
				goto done;
			}
			reading = 0;
			if (writing) {
				err = retry_end(&wr, dst);
				if (err) {
					*write_fail = 1;
					errno = err;
					err = bail(report, dst_path, "Write");
					goto done;
				}
				writing = 0;
			}
			err = retry_begin(&wr, dst, 1, buf[slot], rd_len, (off_t)wr_at);
			if (err) {
				*write_fail = 1;
				errno = err;
				err = bail(report, dst_path, "Write");
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
				err = retry_begin(&rd, src, 0, buf[slot], rd_len, (off_t)rd_at);
				if (err) {
					errno = err;
					err = bail(report, src_path, "Read");
					goto done;
				}
				reading = 1;
			}
			md5_update(&hash, buf[hash_slot], (unsigned int)hash_len);
		} else if (writing) {
			err = retry_end(&wr, dst);
			if (err) {
				*write_fail = 1;
				errno = err;
				err = bail(report, dst_path, "Write");
				goto done;
			}
			writing = 0;
		}
	}

	drop_io(&rd);
	drop_io(&wr);
	if (src >= 0) {
		close(src);
		src = -1;
	}
	if (dst >= 0) {
		close(dst);
		dst = -1;
	}

	if (logical > aligned) {
		int tail_write = 0;

		err = copy_tail(src_path, dst_path, aligned, (size_t)(logical - aligned),
			&hash, report, &tail_write);
		if (err) {
			*write_fail = tail_write;
			goto done;
		}
	}

	md5_final(&hash, md5out);
	if (copied)
		*copied = logical;

done:
	drop_io(&rd);
	drop_io(&wr);
	if (src >= 0)
		close(src);
	if (dst >= 0)
		close(dst);
	return err;
}

static int copy_file(const char *src_path, const char *dst_path, void *buf[2],
	unsigned char md5out[16], unsigned long long *copied, size_t xfer, int report,
	int *write_fail)
{
	int err = copy_file_mode(src_path, dst_path, buf, md5out, copied, xfer, 0,
		write_fail, 1);

	if (!err)
		return 0;
	if (direct_rejected(err))
		return copy_file_mode(src_path, dst_path, buf, md5out, copied, xfer, report,
			write_fail, 0);
	if (report) {
		errno = err;
		fail_path(src_path, *write_fail ? "Write" : "Read");
	}
	return err;
}

static int hash_file(const char *src_path, void *buf, size_t xfer, unsigned char md5out[16],
	unsigned long long *size_out)
{
	int src, attempt;
	struct stat st;
	struct md5 hash;
	unsigned long long left, at;

	src = open(src_path, O_RDONLY);
	if (src < 0)
		return errno ? errno : EIO;
	if (fstat(src, &st) != 0) {
		int e = errno;
		close(src);
		return e ? e : EIO;
	}
	left = (unsigned long long)st.st_size;
	at = 0;
	md5_init(&hash);
	while (left) {
		size_t want = left > xfer ? xfer : (size_t)left;
		ssize_t got = 0;

		for (attempt = 0; attempt < IO_ATTEMPTS; attempt++) {
			got = pread(src, buf, want, (off_t)at);
			if (got == (ssize_t)want)
				break;
		}
		if (attempt == IO_ATTEMPTS) {
			int e = errno ? errno : EIO;
			close(src);
			return e;
		}
		md5_update(&hash, buf, (unsigned int)want);
		at += want;
		left -= want;
	}
	md5_final(&hash, md5out);
	if (size_out)
		*size_out = (unsigned long long)st.st_size;
	close(src);
	return 0;
}

static int same_size(const char *src, const char *dst)
{
	struct stat a, b;

	if (stat(src, &a) != 0 || stat(dst, &b) != 0)
		return 0;
	return a.st_size == b.st_size;
}

static void print_result(const unsigned char md5[16], const char *rel, unsigned long long size, int kind)
{
	int i;

	pthread_mutex_lock(&g_out_lock);
	fprintf(stdout, "\"%s\"\t", rel);
	if (kind == 1) {
		fprintf(stdout, "FAILED\tFAILED\tERROR\n");
		pthread_mutex_unlock(&g_out_lock);
		return;
	}
	if (md5) {
		for (i = 0; i < 16; i++)
			fprintf(stdout, "%02x", md5[i]);
	}
	if (kind == 3) {
		fprintf(stdout, "\tERROR\tERROR\n");
		pthread_mutex_unlock(&g_out_lock);
		return;
	}
	fprintf(stdout, "\t%llu\t%s\n", size, kind ? "ERROR" : "OK");
	pthread_mutex_unlock(&g_out_lock);
}

struct job {
	char *src;
	char *dst;
	char *rel;
	struct job *next;
};

struct job_queue {
	struct job *head;
	struct job *tail;
	pthread_mutex_t lock;
	sem_t sem;
	sem_t init_sem;
	int failed;
	int ready;
};

static int task_count(void)
{
	long n = sysconf(_SC_NPROCESSORS_ONLN);

	if (n < 2)
		n = 2;
	if (n > MAX_TASKS)
		n = MAX_TASKS;
	return (int)n;
}

static void sem_wait_intr(sem_t *sem)
{
	while (sem_wait(sem) != 0 && errno == EINTR)
		;
}

static int enqueue(struct job_queue *q, char *src, char *dst, char *rel)
{
	struct job *j = malloc(sizeof(*j));

	if (!j)
		return 1;
	j->src = src;
	j->dst = dst;
	j->rel = rel;
	j->next = NULL;
	pthread_mutex_lock(&q->lock);
	if (q->tail)
		q->tail->next = j;
	else
		q->head = j;
	q->tail = j;
	pthread_mutex_unlock(&q->lock);
	sem_post(&q->sem);
	return 0;
}

static struct job *dequeue(struct job_queue *q)
{
	struct job *j;

	sem_wait_intr(&q->sem);
	pthread_mutex_lock(&q->lock);
	j = q->head;
	if (j) {
		q->head = j->next;
		if (!q->head)
			q->tail = NULL;
	}
	pthread_mutex_unlock(&q->lock);
	return j;
}

static void free_jobs(struct job_queue *q)
{
	struct job *j = q->head;

	while (j) {
		struct job *next = j->next;

		free(j->src);
		free(j->dst);
		free(j->rel);
		free(j);
		j = next;
	}
	q->head = q->tail = NULL;
}

static void *copy_task(void *param)
{
	struct job_queue *q = param;
	void *buf[2] = {NULL, NULL};
	unsigned char md5[16];
	unsigned long long copied;
	size_t xfer;

	xfer = alloc_buffers(buf);
	if (xfer)
		__sync_fetch_and_add(&q->ready, 1);
	sem_post(&q->init_sem);
	if (!xfer)
		return NULL;

	for (;;) {
		struct job *j = dequeue(q);
		size_t use;
		int err, write_fail;

		if (!j || !j->src) {
			free(j);
			break;
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
					errno = err;
					fail_path(j->src, "Copy");
				}
				break;
			}
			use >>= 1;
		}
		if (!err) {
			xfer = use;
			if (!same_size(j->src, j->dst)) {
				__sync_lock_test_and_set(&g_io_error, 1);
				print_result(md5, j->rel, copied, 3);
			} else {
				__sync_fetch_and_add(&g_files, 1);
				__sync_fetch_and_add(&g_bytes, (long long)copied);
				print_result(md5, j->rel, copied, 0);
			}
		} else {
			__sync_lock_test_and_set(&g_io_error, 1);
			if (write_fail && !hash_file(j->src, buf[0], xfer, md5, &copied))
				print_result(md5, j->rel, copied, 2);
			else
				print_result(NULL, j->rel, 0, 1);
		}
		free(j->src);
		free(j->dst);
		free(j->rel);
		free(j);
	}
	free(buf[0]);
	free(buf[1]);
	return NULL;
}

static int copy_tree(const char *src, const char *dst, const char *rel, struct job_queue *q)
{
	DIR *dir;
	struct dirent *de;
	int rc = 0;

	dir = opendir(src);
	if (!dir) {
		fail_path(src, "List directory");
		return 1;
	}
	errno = 0;
	while ((de = readdir(dir)) != NULL) {
		char *child_src = NULL;
		char *child_dst = NULL;
		char *child_rel = NULL;
		struct stat st;

		if (de->d_name[0] == '.' && (de->d_name[1] == 0
			|| (de->d_name[1] == '.' && de->d_name[2] == 0)))
			continue;

		child_src = join_dir_file(src, de->d_name);
		child_dst = join_dir_file(dst, de->d_name);
		if (rel[0])
			child_rel = join_dir_file(rel, de->d_name);
		else
			child_rel = strdup(de->d_name);
		if (!child_src || !child_dst || !child_rel) {
			fail("Build path");
			rc = 1;
			goto next;
		}
		if (lstat(child_src, &st) != 0) {
			fail_path(child_src, "Stat");
			rc = 1;
			goto next;
		}
		if (S_ISLNK(st.st_mode)) {
			pthread_mutex_lock(&g_out_lock);
			fprintf(stderr, "Skipping symbolic link: %s\n", child_src);
			pthread_mutex_unlock(&g_out_lock);
			goto next;
		}
		if (S_ISDIR(st.st_mode)) {
			if (mkdir(child_dst, 0777) != 0 && errno != EEXIST) {
				fail_path(child_dst, "Create directory");
				rc = 1;
				goto next;
			}
			if (lstat(child_dst, &st) != 0 || !S_ISDIR(st.st_mode)) {
				pthread_mutex_lock(&g_out_lock);
				fprintf(stderr, "Destination is not a directory: %s\n", child_dst);
				pthread_mutex_unlock(&g_out_lock);
				rc = 1;
				goto next;
			}
			if (copy_tree(child_src, child_dst, child_rel, q))
				rc = 1;
		} else if (S_ISREG(st.st_mode)) {
			if (enqueue(q, child_src, child_dst, child_rel)) {
				fail("Queue file");
				rc = 1;
			} else {
				child_src = NULL;
				child_dst = NULL;
				child_rel = NULL;
			}
		} else {
			pthread_mutex_lock(&g_out_lock);
			fprintf(stderr, "Skipping special file: %s\n", child_src);
			pthread_mutex_unlock(&g_out_lock);
		}

	next:
		free(child_src);
		free(child_dst);
		free(child_rel);
		if (rc)
			break;
		errno = 0;
	}
	if (!rc && errno) {
		fail_path(src, "List directory");
		rc = 1;
	}
	closedir(dir);
	return rc;
}

static void *flush_stdout(void *arg)
{
	(void)arg;
	pthread_mutex_lock(&g_flush_lock);
	while (!g_flush_stop) {
		struct timespec ts;

		clock_gettime(CLOCK_REALTIME, &ts);
		ts.tv_sec += 1;
		if (pthread_cond_timedwait(&g_flush_cond, &g_flush_lock, &ts) == ETIMEDOUT) {
			pthread_mutex_lock(&g_out_lock);
			fflush(stdout);
			pthread_mutex_unlock(&g_out_lock);
		}
	}
	pthread_mutex_unlock(&g_flush_lock);
	return NULL;
}

static void help(void)
{
	printf("copymd5 for Linux Version %s\n"
		"Recursively copy a source directory into a destination directory.\n"
		"\n"
		"Usage: copymd5_lin <source directory> <destination directory>\n"
		"       copymd5_lin /?\n"
		"\n"
		"The source directory is created inside the destination under its own name.\n"
		"Paths may end with a slash.\n"
		"\n"
		"Each file prints one tab-separated line:\n"
		"\"relative/path\"\t<md5>\t<size>\tOK\n"
		"A failed read:\n"
		"\"relative/path\"\tFAILED\tFAILED\tERROR\n"
		"A failed write:\n"
		"\"relative/path\"\t<md5>\t<size>\tERROR\n"
		"A size mismatch:\n"
		"\"relative/path\"\t<md5>\tERROR\tERROR\n"
		"\n"
		"A blank line follows, then a summary that starts with ...finished:\n"
		"The exit code is 0 when every file copies, and 1 when any read, write, or size check fails.\n",
		VERSION);
}

static int is_help_arg(const char *arg)
{
	return strcmp(arg, "-h") == 0 || strcmp(arg, "--help") == 0;
}

int main(int argc, char **argv)
{
	int rc = 1, ntasks, started = 0, t, queue_ready = 0;
	char *src_full = NULL, *dst_full = NULL, *dst_root = NULL;
	const char *src_name;
	struct job_queue queue;
	pthread_t threads[MAX_TASKS];
	pthread_t flush_thread;
	int flush_started = 0;
	struct timespec t0, t1;
	struct stat st;
	unsigned long long elapsed_ms, hours, mins, secs, ms;
	long nsec;

	if (argc == 2 && is_help_arg(argv[1])) {
		help();
		return 0;
	}
	if (argc != 3) {
		fprintf(stderr, "Usage: copymd5_lin <source directory> <destination directory>\n");
		fprintf(stderr, "       copymd5_lin /?\n");
		return 1;
	}

	src_full = full_path(argv[1]);
	dst_full = full_path(argv[2]);
	if (!src_full || !dst_full) {
		fail("Resolve path");
		goto done;
	}
	if (stat(src_full, &st) != 0) {
		fail("Source directory");
		goto done;
	}
	if (!S_ISDIR(st.st_mode)) {
		fprintf(stderr, "Source is not a directory\n");
		goto done;
	}
	if (stat(dst_full, &st) != 0) {
		fail("Destination directory");
		goto done;
	}
	if (!S_ISDIR(st.st_mode)) {
		fprintf(stderr, "Destination is not a directory\n");
		goto done;
	}

	src_name = basename_p(src_full);
	if (!src_name[0]) {
		fprintf(stderr, "Source path has no directory name\n");
		goto done;
	}
	dst_root = join_dir_file(dst_full, src_name);
	if (!dst_root) {
		fail("Build destination path");
		goto done;
	}
	if (is_same_or_child(src_full, dst_root)) {
		fprintf(stderr, "Destination is inside the source directory\n");
		goto done;
	}
	if (mkdir(dst_root, 0777) != 0 && errno != EEXIST) {
		fail_path(dst_root, "Create directory");
		goto done;
	}
	if (stat(dst_root, &st) != 0 || !S_ISDIR(st.st_mode)) {
		fprintf(stderr, "Destination is not a directory: %s\n", dst_root);
		goto done;
	}

	memset(&queue, 0, sizeof(queue));
	if (pthread_mutex_init(&queue.lock, NULL) != 0
		|| sem_init(&queue.sem, 0, 0) != 0
		|| sem_init(&queue.init_sem, 0, 0) != 0) {
		fail("Create queue");
		goto done;
	}
	queue_ready = 1;

	ntasks = task_count();
	for (t = 0; t < ntasks; t++) {
		if (pthread_create(&threads[t], NULL, copy_task, &queue) != 0)
			break;
		started++;
	}
	if (!started) {
		fail("Start task");
		goto done;
	}
	for (t = 0; t < started; t++)
		sem_wait_intr(&queue.init_sem);
	if (!queue.ready) {
		for (t = 0; t < started; t++)
			pthread_join(threads[t], NULL);
		started = 0;
		fail("Allocate buffer");
		goto done;
	}

	clock_gettime(CLOCK_MONOTONIC, &t0);
	g_flush_stop = 0;
	if (pthread_create(&flush_thread, NULL, flush_stdout, NULL) == 0)
		flush_started = 1;
	if (copy_tree(src_full, dst_root, "", &queue))
		queue.failed = 1;
	for (t = 0; t < queue.ready; t++)
		enqueue(&queue, NULL, NULL, NULL);
	for (t = 0; t < started; t++)
		pthread_join(threads[t], NULL);
	started = 0;
	clock_gettime(CLOCK_MONOTONIC, &t1);
	nsec = t1.tv_nsec - t0.tv_nsec;
	elapsed_ms = (unsigned long long)(t1.tv_sec - t0.tv_sec) * 1000ULL;
	if (nsec < 0) {
		elapsed_ms -= 1000ULL;
		nsec += 1000000000L;
	}
	elapsed_ms += (unsigned long long)nsec / 1000000ULL;
	hours = elapsed_ms / 3600000ULL;
	mins = (elapsed_ms / 60000ULL) % 60ULL;
	secs = (elapsed_ms / 1000ULL) % 60ULL;
	ms = elapsed_ms % 1000ULL;

	pthread_mutex_lock(&g_flush_lock);
	g_flush_stop = 1;
	pthread_cond_signal(&g_flush_cond);
	pthread_mutex_unlock(&g_flush_lock);
	if (flush_started) {
		pthread_join(flush_thread, NULL);
		flush_started = 0;
	}
	fflush(stdout);
	printf("\n...finished: %llu file(s), %llu bytes, took %02llu:%02llu:%02llu.%03llu\n",
		(unsigned long long)g_files,
		(unsigned long long)g_bytes,
		hours, mins, secs, ms);
	fflush(stdout);
	rc = (g_io_error || queue.failed) ? 1 : 0;

done:
	if (flush_started) {
		pthread_mutex_lock(&g_flush_lock);
		g_flush_stop = 1;
		pthread_cond_signal(&g_flush_cond);
		pthread_mutex_unlock(&g_flush_lock);
		pthread_join(flush_thread, NULL);
	}
	if (started) {
		for (t = 0; t < queue.ready; t++)
			enqueue(&queue, NULL, NULL, NULL);
		for (t = 0; t < started; t++)
			pthread_join(threads[t], NULL);
	}
	if (queue_ready) {
		free_jobs(&queue);
		sem_destroy(&queue.sem);
		sem_destroy(&queue.init_sem);
		pthread_mutex_destroy(&queue.lock);
	}
	free(dst_root);
	free(src_full);
	free(dst_full);
	return rc;
}
