#include "pchsi_s1/source_copy.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <string.h>

struct copy_fake_state {
    const unsigned char *source;
    size_t source_size;
    size_t source_offset;
    unsigned char destination[64];
    size_t destination_size;
    struct stat source_stat;
    int mutate_identity_on_second_fstat;
    int fstat_calls;
    int lseek_calls;
    int read_calls;
    int write_calls;
    int openat_calls;
    int fsync_calls;
    int close_source_calls;
    int close_destination_calls;
    int unlink_calls;
    int destination_fd;
    int captured_open_flags;
    unsigned int captured_open_mode;
};

static int fake_fstat(void *context, int fd, struct stat *status)
{
    struct copy_fake_state *state = context;
    assert(fd == 5);
    state->fstat_calls += 1;
    *status = state->source_stat;
    if (state->mutate_identity_on_second_fstat && state->fstat_calls >= 2) {
        status->st_ino += 1;
    }
    return 0;
}

static off_t fake_lseek(void *context, int fd, off_t offset, int whence)
{
    struct copy_fake_state *state = context;
    assert(fd == 5);
    assert(offset == 0);
    assert(whence == SEEK_SET);
    state->lseek_calls += 1;
    state->source_offset = 0U;
    return 0;
}

static ssize_t fake_read(void *context, int fd, void *buffer, size_t size)
{
    struct copy_fake_state *state = context;
    size_t remaining;
    size_t copied;

    assert(fd == 5);
    state->read_calls += 1;
    remaining = state->source_size - state->source_offset;
    if (remaining == 0U) {
        return 0;
    }
    copied = remaining < size ? remaining : size;
    memcpy(buffer, state->source + state->source_offset, copied);
    state->source_offset += copied;
    return (ssize_t)copied;
}

static ssize_t fake_write(
    void *context,
    int fd,
    const void *buffer,
    size_t size
)
{
    struct copy_fake_state *state = context;
    assert(fd == state->destination_fd);
    assert(state->destination_size + size <= sizeof(state->destination));
    memcpy(state->destination + state->destination_size, buffer, size);
    state->destination_size += size;
    state->write_calls += 1;
    return (ssize_t)size;
}

static int fake_openat(
    void *context,
    int dirfd,
    const char *path,
    int flags,
    unsigned int mode
)
{
    struct copy_fake_state *state = context;
    assert(dirfd == 7);
    assert(strcmp(path, "collector.py") == 0);
    state->openat_calls += 1;
    state->captured_open_flags = flags;
    state->captured_open_mode = mode;
    return state->destination_fd;
}

static int fake_fsync(void *context, int fd)
{
    struct copy_fake_state *state = context;
    assert(fd == state->destination_fd);
    state->fsync_calls += 1;
    return 0;
}

static int fake_close(void *context, int fd)
{
    struct copy_fake_state *state = context;
    if (fd == 5) {
        state->close_source_calls += 1;
    } else {
        assert(fd == state->destination_fd);
        state->close_destination_calls += 1;
    }
    return 0;
}

static int fake_unlinkat(
    void *context,
    int dirfd,
    const char *path,
    int flags
)
{
    struct copy_fake_state *state = context;
    assert(dirfd == 7);
    assert(strcmp(path, "collector.py") == 0);
    assert(flags == 0);
    state->unlink_calls += 1;
    return 0;
}

static struct pchsi_system_ops make_operations(
    struct copy_fake_state *state
)
{
    struct pchsi_system_ops operations;
    memset(&operations, 0, sizeof(operations));
    operations.context = state;
    operations.fstat_fn = fake_fstat;
    operations.lseek_fn = fake_lseek;
    operations.read_fn = fake_read;
    operations.write_fn = fake_write;
    operations.openat_fn = fake_openat;
    operations.fsync_fn = fake_fsync;
    operations.close_fn = fake_close;
    operations.unlinkat_fn = fake_unlinkat;
    return operations;
}

static struct copy_fake_state make_state(void)
{
    static const unsigned char source[] = "abc";
    struct copy_fake_state state;
    memset(&state, 0, sizeof(state));
    state.source = source;
    state.source_size = sizeof(source) - 1U;
    state.source_stat.st_dev = 10;
    state.source_stat.st_ino = 20;
    state.source_stat.st_size = 3;
    state.source_stat.st_mode = S_IFREG | 0444;
    state.destination_fd = 9;
    return state;
}

static struct pchsi_file_identity expected_identity(void)
{
    struct pchsi_file_identity identity;
    identity.device = 10;
    identity.inode = 20;
    identity.size = 3;
    identity.mode = S_IFREG | 0444;
    return identity;
}

static void test_same_fd_hash_copy_and_seal(void)
{
    static const unsigned char digest[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
    };
    struct copy_fake_state state = make_state();
    struct pchsi_system_ops operations = make_operations(&state);
    struct pchsi_file_identity identity = expected_identity();

    assert(
        pchsi_copy_and_seal_source(
            5,
            &identity,
            7,
            "collector.py",
            digest,
            &operations
        ) == PCHSI_STATUS_OK
    );
    assert(state.fstat_calls == 2);
    assert(state.lseek_calls == 2);
    assert(state.openat_calls == 1);
    assert(state.fsync_calls == 1);
    assert(state.close_destination_calls == 1);
    assert(state.close_source_calls == 1);
    assert(state.unlink_calls == 0);
    assert(state.destination_size == 3U);
    assert(memcmp(state.destination, "abc", 3U) == 0);
    assert(
        state.captured_open_flags
        == (
            O_WRONLY
            | O_CREAT
            | O_EXCL
            | O_CLOEXEC
            | O_NOFOLLOW
        )
    );
    assert(state.captured_open_mode == 0444U);
}

static void test_hash_mismatch_fails_and_closes_source(void)
{
    unsigned char wrong_digest[32] = {0};
    struct copy_fake_state state = make_state();
    struct pchsi_system_ops operations = make_operations(&state);
    struct pchsi_file_identity identity = expected_identity();

    assert(
        pchsi_copy_and_seal_source(
            5,
            &identity,
            7,
            "collector.py",
            wrong_digest,
            &operations
        ) == PCHSI_STATUS_SOURCE_HASH_MISMATCH
    );
    assert(state.openat_calls == 0);
    assert(state.close_source_calls == 1);
    assert(state.unlink_calls == 0);
}

static void test_identity_change_after_copy_fails_closed(void)
{
    static const unsigned char digest[32] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
    };
    struct copy_fake_state state = make_state();
    struct pchsi_system_ops operations = make_operations(&state);
    struct pchsi_file_identity identity = expected_identity();
    state.mutate_identity_on_second_fstat = 1;

    assert(
        pchsi_copy_and_seal_source(
            5,
            &identity,
            7,
            "collector.py",
            digest,
            &operations
        ) == PCHSI_STATUS_SOURCE_IDENTITY_CHANGED
    );
    assert(state.unlink_calls == 1);
    assert(state.close_source_calls == 1);
}

static void test_destination_name_cannot_escape(void)
{
    unsigned char digest[32] = {0};
    struct copy_fake_state state = make_state();
    struct pchsi_system_ops operations = make_operations(&state);
    struct pchsi_file_identity identity = expected_identity();

    assert(
        pchsi_copy_and_seal_source(
            5,
            &identity,
            7,
            "../collector.py",
            digest,
            &operations
        ) == PCHSI_STATUS_INVALID_ARGUMENT
    );
    assert(state.close_source_calls == 0);
}

int main(void)
{
    test_same_fd_hash_copy_and_seal();
    test_hash_mismatch_fails_and_closes_source();
    test_identity_change_after_copy_fails_closed();
    test_destination_name_cannot_escape();
    return 0;
}
