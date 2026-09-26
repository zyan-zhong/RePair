#include "pchsi_s1/system_ops.h"

#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "fake_system_ops.c"

static void test_all_operation_families_record_in_order(void)
{
    struct pchsi_fake_system_ops_state state;
    struct pchsi_system_ops operations;
    struct pchsi_open_how open_how = {0};
    struct pchsi_mount_attr mount_attr = {0};
    struct pchsi_clone_args clone_args = {0};
    struct stat status = {0};
    struct rlimit limit = {0};
    struct pollfd poll_descriptor = {0};
    gid_t groups[1] = {0};
    int pipe_descriptors[2] = {-1, -1};
    int child_status = 0;
    char byte = 0;
    size_t index;
    const enum pchsi_fake_operation expected[] = {
        PCHSI_FAKE_OPENAT2,
        PCHSI_FAKE_OPENAT,
        PCHSI_FAKE_FSTATAT,
        PCHSI_FAKE_FSTAT,
        PCHSI_FAKE_READ,
        PCHSI_FAKE_WRITE,
        PCHSI_FAKE_LSEEK,
        PCHSI_FAKE_CLOSE,
        PCHSI_FAKE_CLOSE_RANGE,
        PCHSI_FAKE_MKDIRAT,
        PCHSI_FAKE_UNLINKAT,
        PCHSI_FAKE_RENAMEAT2,
        PCHSI_FAKE_FSYNC,
        PCHSI_FAKE_CLONE3,
        PCHSI_FAKE_UNSHARE,
        PCHSI_FAKE_SETNS,
        PCHSI_FAKE_MOUNT,
        PCHSI_FAKE_UMOUNT2,
        PCHSI_FAKE_MOUNT_SETATTR,
        PCHSI_FAKE_PIVOT_ROOT,
        PCHSI_FAKE_SETGROUPS,
        PCHSI_FAKE_SETRESUID,
        PCHSI_FAKE_SETRESGID,
        PCHSI_FAKE_SETFSUID,
        PCHSI_FAKE_SETFSGID,
        PCHSI_FAKE_PRCTL,
        PCHSI_FAKE_SECCOMP,
        PCHSI_FAKE_LANDLOCK_CREATE_RULESET,
        PCHSI_FAKE_LANDLOCK_ADD_RULE,
        PCHSI_FAKE_LANDLOCK_RESTRICT_SELF,
        PCHSI_FAKE_SETRLIMIT,
        PCHSI_FAKE_PIPE2,
        PCHSI_FAKE_DUP2,
        PCHSI_FAKE_KILL,
        PCHSI_FAKE_WAITPID,
        PCHSI_FAKE_POLL,
    };

    pchsi_fake_system_ops_init(&state, &operations);
    state.configured_return = 0L;

    assert(operations.openat2_fn(operations.context, 3, "x", &open_how, sizeof(open_how)) == 0);
    assert(operations.openat_fn(operations.context, 3, "x", O_RDONLY, 0U) == 0);
    assert(operations.fstatat_fn(operations.context, 3, "x", &status, 0) == 0);
    assert(operations.fstat_fn(operations.context, 4, &status) == 0);
    assert(operations.read_fn(operations.context, 4, &byte, 1U) == 0);
    assert(operations.write_fn(operations.context, 4, &byte, 1U) == 0);
    assert(operations.lseek_fn(operations.context, 4, 0, SEEK_SET) == 0);
    assert(operations.close_fn(operations.context, 4) == 0);
    assert(operations.close_range_fn(operations.context, 3U, UINT_MAX, 0) == 0);
    assert(operations.mkdirat_fn(operations.context, 3, "x", 0700) == 0);
    assert(operations.unlinkat_fn(operations.context, 3, "x", 0) == 0);
    assert(operations.renameat2_fn(operations.context, 3, "a", 4, "b", 0U) == 0);
    assert(operations.fsync_fn(operations.context, 4) == 0);
    assert(operations.clone3_fn(operations.context, &clone_args, sizeof(clone_args)) == 0L);
    assert(operations.unshare_fn(operations.context, 0) == 0);
    assert(operations.setns_fn(operations.context, 4, 0) == 0);
    assert(operations.mount_fn(operations.context, NULL, "/x", "tmpfs", 0UL, NULL) == 0);
    assert(operations.umount2_fn(operations.context, "/x", 0) == 0);
    assert(operations.mount_setattr_fn(operations.context, 3, "x", 0U, &mount_attr, sizeof(mount_attr)) == 0L);
    assert(operations.pivot_root_fn(operations.context, "/new", "/old") == 0L);
    assert(operations.setgroups_fn(operations.context, 1U, groups) == 0);
    assert(operations.setresuid_fn(operations.context, 1U, 2U, 3U) == 0);
    assert(operations.setresgid_fn(operations.context, 1U, 2U, 3U) == 0);
    assert(operations.setfsuid_fn(operations.context, 1U) == 0);
    assert(operations.setfsgid_fn(operations.context, 1U) == 0);
    assert(operations.prctl_fn(operations.context, 1, 2UL, 3UL, 4UL, 5UL) == 0);
    assert(operations.seccomp_fn(operations.context, 1U, 2U, NULL) == 0L);
    assert(operations.landlock_create_ruleset_fn(operations.context, NULL, 0U, 0U) == 0L);
    assert(operations.landlock_add_rule_fn(operations.context, 3, 1, NULL, 0U) == 0L);
    assert(operations.landlock_restrict_self_fn(operations.context, 3, 0U) == 0L);
    assert(operations.setrlimit_fn(operations.context, RLIMIT_NOFILE, &limit) == 0);
    assert(operations.pipe2_fn(operations.context, pipe_descriptors, 0) == 0);
    assert(operations.dup2_fn(operations.context, 3, 4) == 0);
    assert(operations.kill_fn(operations.context, 123, SIGKILL) == 0);
    assert(operations.waitpid_fn(operations.context, 123, &child_status, 0) == 0);
    assert(operations.poll_fn(operations.context, &poll_descriptor, 1U, 10) == 0);

    assert(state.call_count == sizeof(expected) / sizeof(expected[0]));

    for (index = 0U; index < state.call_count; index += 1U) {
        assert(state.calls[index].operation == expected[index]);
    }
}

static void test_errno_and_return_are_propagated_exactly(void)
{
    struct pchsi_fake_system_ops_state state;
    struct pchsi_system_ops operations;
    struct pchsi_open_how how = {0};

    pchsi_fake_system_ops_init(&state, &operations);
    state.configured_return = -1L;
    state.configured_errno = EACCES;

    errno = 0;
    assert(operations.openat2_fn(operations.context, 9, "denied", &how, sizeof(how)) == -1);
    assert(errno == EACCES);
    assert(state.call_count == 1U);
    assert(state.calls[0].operation == PCHSI_FAKE_OPENAT2);
    assert(state.calls[0].argument0 == 9L);
}

static void test_real_operation_table_is_complete(void)
{
    const struct pchsi_system_ops *operations = pchsi_real_system_ops();

    assert(operations != NULL);
    assert(operations->openat2_fn != NULL);
    assert(operations->openat_fn != NULL);
    assert(operations->fstatat_fn != NULL);
    assert(operations->fstat_fn != NULL);
    assert(operations->read_fn != NULL);
    assert(operations->write_fn != NULL);
    assert(operations->lseek_fn != NULL);
    assert(operations->close_fn != NULL);
    assert(operations->close_range_fn != NULL);
    assert(operations->mkdirat_fn != NULL);
    assert(operations->unlinkat_fn != NULL);
    assert(operations->renameat2_fn != NULL);
    assert(operations->fsync_fn != NULL);
    assert(operations->clone3_fn != NULL);
    assert(operations->unshare_fn != NULL);
    assert(operations->setns_fn != NULL);
    assert(operations->mount_fn != NULL);
    assert(operations->umount2_fn != NULL);
    assert(operations->mount_setattr_fn != NULL);
    assert(operations->pivot_root_fn != NULL);
    assert(operations->setgroups_fn != NULL);
    assert(operations->setresuid_fn != NULL);
    assert(operations->setresgid_fn != NULL);
    assert(operations->setfsuid_fn != NULL);
    assert(operations->setfsgid_fn != NULL);
    assert(operations->prctl_fn != NULL);
    assert(operations->seccomp_fn != NULL);
    assert(operations->landlock_create_ruleset_fn != NULL);
    assert(operations->landlock_add_rule_fn != NULL);
    assert(operations->landlock_restrict_self_fn != NULL);
    assert(operations->setrlimit_fn != NULL);
    assert(operations->pipe2_fn != NULL);
    assert(operations->dup2_fn != NULL);
    assert(operations->kill_fn != NULL);
    assert(operations->waitpid_fn != NULL);
    assert(operations->poll_fn != NULL);
    assert(pchsi_linux_compatibility_compile_check() == 1);
}

int main(void)
{
    test_all_operation_families_record_in_order();
    test_errno_and_return_are_propagated_exactly();
    test_real_operation_table_is_complete();
    return 0;
}
