#include "pchsi_s1/source_resolution.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>

struct fake_state {
    int open_calls;
    int fstat_calls;
    int close_calls;
    int open_return;
    int open_errno;
    int fstat_return;
    struct stat status;
    struct pchsi_open_how captured_how;
    int captured_dirfd;
    char captured_path[128];
};

static int fake_openat2(
    void *context,
    int dirfd,
    const char *path,
    const struct pchsi_open_how *how,
    size_t size
)
{
    struct fake_state *state = context;
    assert(size == sizeof(*how));
    state->open_calls += 1;
    state->captured_dirfd = dirfd;
    state->captured_how = *how;
    (void)snprintf(state->captured_path, sizeof(state->captured_path), "%s", path);
    errno = state->open_errno;
    return state->open_return;
}

static int fake_fstat(void *context, int fd, struct stat *status)
{
    struct fake_state *state = context;
    assert(fd == state->open_return);
    state->fstat_calls += 1;
    *status = state->status;
    return state->fstat_return;
}

static int fake_close(void *context, int fd)
{
    struct fake_state *state = context;
    assert(fd == state->open_return);
    state->close_calls += 1;
    return 0;
}

static struct pchsi_system_ops make_operations(struct fake_state *state)
{
    struct pchsi_system_ops operations;
    memset(&operations, 0, sizeof(operations));
    operations.context = state;
    operations.openat2_fn = fake_openat2;
    operations.fstat_fn = fake_fstat;
    operations.close_fn = fake_close;
    return operations;
}

static void test_invalid_paths_fail_before_open(void)
{
    const char *invalid[] = {
        "",
        "/absolute",
        "../escape",
        "a/../b",
        "a/./b",
        "a//b",
        "a\\b",
    };
    size_t index;

    for (index = 0U; index < sizeof(invalid) / sizeof(invalid[0]); index += 1U) {
        struct fake_state state = {0};
        struct pchsi_system_ops operations = make_operations(&state);
        struct pchsi_file_identity identity;
        int source_fd = -1;
        assert(
            pchsi_open_source_beneath_repo(
                3,
                invalid[index],
                &operations,
                &source_fd,
                &identity
            ) == PCHSI_STATUS_SOURCE_PATH_INVALID
        );
        assert(state.open_calls == 0);
    }
}

static void test_safe_open_contract_is_exact(void)
{
    struct fake_state state = {0};
    struct pchsi_system_ops operations;
    struct pchsi_file_identity identity;
    int source_fd = -1;

    state.open_return = 9;
    state.status.st_mode = S_IFREG | 0444;
    state.status.st_dev = 12;
    state.status.st_ino = 34;
    state.status.st_size = 56;
    operations = make_operations(&state);

    assert(
        pchsi_open_source_beneath_repo(
            3,
            "src/collector.py",
            &operations,
            &source_fd,
            &identity
        ) == PCHSI_STATUS_OK
    );

    assert(source_fd == 9);
    assert(state.open_calls == 1);
    assert(state.fstat_calls == 1);
    assert(state.close_calls == 0);
    assert(state.captured_dirfd == 3);
    assert(strcmp(state.captured_path, "src/collector.py") == 0);
    assert(
        state.captured_how.flags
        == (uint64_t)(O_RDONLY | O_CLOEXEC | O_NOFOLLOW)
    );
    assert(state.captured_how.mode == 0U);
    assert(
        state.captured_how.resolve
        == (
            PCHSI_RESOLVE_BENEATH
            | PCHSI_RESOLVE_NO_SYMLINKS
            | PCHSI_RESOLVE_NO_MAGICLINKS
        )
    );
    assert(identity.device == 12);
    assert(identity.inode == 34);
    assert(identity.size == 56);
}

static void test_openat2_symlink_or_magic_link_failure_is_closed(void)
{
    struct fake_state state = {0};
    struct pchsi_system_ops operations;
    struct pchsi_file_identity identity;
    int source_fd = -1;

    state.open_return = -1;
    state.open_errno = ELOOP;
    operations = make_operations(&state);

    assert(
        pchsi_open_source_beneath_repo(
            3,
            "src/link.py",
            &operations,
            &source_fd,
            &identity
        ) == PCHSI_STATUS_SOURCE_OPEN_FAILED
    );
    assert(state.open_calls == 1);
    assert(state.fstat_calls == 0);
}

static void test_nonregular_source_is_closed(void)
{
    struct fake_state state = {0};
    struct pchsi_system_ops operations;
    struct pchsi_file_identity identity;
    int source_fd = -1;

    state.open_return = 9;
    state.status.st_mode = S_IFDIR | 0555;
    operations = make_operations(&state);

    assert(
        pchsi_open_source_beneath_repo(
            3,
            "src/directory",
            &operations,
            &source_fd,
            &identity
        ) == PCHSI_STATUS_SOURCE_NOT_REGULAR
    );
    assert(state.close_calls == 1);
}

int main(void)
{
    test_invalid_paths_fail_before_open();
    test_safe_open_contract_is_exact();
    test_openat2_symlink_or_magic_link_failure_is_closed();
    test_nonregular_source_is_closed();
    return 0;
}
