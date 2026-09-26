#include "pchsi_s1/system_ops.h"

#include <errno.h>
#include <string.h>

#define PCHSI_FAKE_MAX_CALLS 128U

enum pchsi_fake_operation {
    PCHSI_FAKE_OPENAT2 = 1,
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
    PCHSI_FAKE_POLL
};

struct pchsi_fake_call {
    enum pchsi_fake_operation operation;
    long argument0;
    long argument1;
    long argument2;
    long argument3;
};

struct pchsi_fake_system_ops_state {
    struct pchsi_fake_call calls[PCHSI_FAKE_MAX_CALLS];
    size_t call_count;
    long configured_return;
    int configured_errno;
};

static long pchsi_fake_record(
    struct pchsi_fake_system_ops_state *state,
    enum pchsi_fake_operation operation,
    long argument0,
    long argument1,
    long argument2,
    long argument3
)
{
    if (state->call_count < PCHSI_FAKE_MAX_CALLS) {
        struct pchsi_fake_call *call = &state->calls[state->call_count];
        call->operation = operation;
        call->argument0 = argument0;
        call->argument1 = argument1;
        call->argument2 = argument2;
        call->argument3 = argument3;
    }
    state->call_count += 1U;
    errno = state->configured_errno;
    return state->configured_return;
}

static int fake_openat2(
    void *context,
    int dirfd,
    const char *path,
    const struct pchsi_open_how *how,
    size_t size
)
{
    (void)path;
    (void)how;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_OPENAT2,
        dirfd,
        (long)size,
        0L,
        0L
    );
}

static int fake_openat(
    void *context,
    int dirfd,
    const char *path,
    int flags,
    unsigned int mode
)
{
    (void)path;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_OPENAT,
        dirfd,
        flags,
        (long)mode,
        0L
    );
}

static int fake_fstatat(
    void *context,
    int dirfd,
    const char *path,
    struct stat *status,
    int flags
)
{
    (void)path;
    (void)status;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_FSTATAT,
        dirfd,
        flags,
        0L,
        0L
    );
}

static int fake_fstat(void *context, int fd, struct stat *status)
{
    (void)status;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_FSTAT,
        fd,
        0L,
        0L,
        0L
    );
}

static ssize_t fake_read(
    void *context,
    int fd,
    void *buffer,
    size_t size
)
{
    (void)buffer;
    return (ssize_t)pchsi_fake_record(
        context,
        PCHSI_FAKE_READ,
        fd,
        (long)size,
        0L,
        0L
    );
}

static ssize_t fake_write(
    void *context,
    int fd,
    const void *buffer,
    size_t size
)
{
    (void)buffer;
    return (ssize_t)pchsi_fake_record(
        context,
        PCHSI_FAKE_WRITE,
        fd,
        (long)size,
        0L,
        0L
    );
}

static off_t fake_lseek(
    void *context,
    int fd,
    off_t offset,
    int whence
)
{
    return (off_t)pchsi_fake_record(
        context,
        PCHSI_FAKE_LSEEK,
        fd,
        (long)offset,
        whence,
        0L
    );
}

static int fake_close(void *context, int fd)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_CLOSE,
        fd,
        0L,
        0L,
        0L
    );
}

static int fake_close_range(
    void *context,
    unsigned int first,
    unsigned int last,
    int flags
)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_CLOSE_RANGE,
        (long)first,
        (long)last,
        flags,
        0L
    );
}

static int fake_mkdirat(
    void *context,
    int dirfd,
    const char *path,
    mode_t mode
)
{
    (void)path;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_MKDIRAT,
        dirfd,
        (long)mode,
        0L,
        0L
    );
}

static int fake_unlinkat(
    void *context,
    int dirfd,
    const char *path,
    int flags
)
{
    (void)path;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_UNLINKAT,
        dirfd,
        flags,
        0L,
        0L
    );
}

static int fake_renameat2(
    void *context,
    int olddirfd,
    const char *oldpath,
    int newdirfd,
    const char *newpath,
    unsigned int flags
)
{
    (void)oldpath;
    (void)newpath;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_RENAMEAT2,
        olddirfd,
        newdirfd,
        (long)flags,
        0L
    );
}

static int fake_fsync(void *context, int fd)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_FSYNC,
        fd,
        0L,
        0L,
        0L
    );
}

static long fake_clone3(
    void *context,
    const struct pchsi_clone_args *arguments,
    size_t size
)
{
    (void)arguments;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_CLONE3,
        (long)size,
        0L,
        0L,
        0L
    );
}

static int fake_unshare(void *context, int flags)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_UNSHARE,
        flags,
        0L,
        0L,
        0L
    );
}

static int fake_setns(void *context, int fd, int namespace_type)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETNS,
        fd,
        namespace_type,
        0L,
        0L
    );
}

static int fake_mount(
    void *context,
    const char *source,
    const char *target,
    const char *filesystem_type,
    unsigned long flags,
    const void *data
)
{
    (void)source;
    (void)target;
    (void)filesystem_type;
    (void)data;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_MOUNT,
        (long)flags,
        0L,
        0L,
        0L
    );
}

static int fake_umount2(void *context, const char *target, int flags)
{
    (void)target;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_UMOUNT2,
        flags,
        0L,
        0L,
        0L
    );
}

static long fake_mount_setattr(
    void *context,
    int dirfd,
    const char *path,
    unsigned int flags,
    const struct pchsi_mount_attr *attributes,
    size_t size
)
{
    (void)path;
    (void)attributes;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_MOUNT_SETATTR,
        dirfd,
        (long)flags,
        (long)size,
        0L
    );
}

static long fake_pivot_root(
    void *context,
    const char *new_root,
    const char *put_old
)
{
    (void)new_root;
    (void)put_old;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_PIVOT_ROOT,
        0L,
        0L,
        0L,
        0L
    );
}

static int fake_setgroups(
    void *context,
    size_t size,
    const gid_t *groups
)
{
    (void)groups;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETGROUPS,
        (long)size,
        0L,
        0L,
        0L
    );
}

static int fake_setresuid(
    void *context,
    uid_t real_uid,
    uid_t effective_uid,
    uid_t saved_uid
)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETRESUID,
        (long)real_uid,
        (long)effective_uid,
        (long)saved_uid,
        0L
    );
}

static int fake_setresgid(
    void *context,
    gid_t real_gid,
    gid_t effective_gid,
    gid_t saved_gid
)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETRESGID,
        (long)real_gid,
        (long)effective_gid,
        (long)saved_gid,
        0L
    );
}

static int fake_setfsuid(void *context, uid_t uid)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETFSUID,
        (long)uid,
        0L,
        0L,
        0L
    );
}

static int fake_setfsgid(void *context, gid_t gid)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETFSGID,
        (long)gid,
        0L,
        0L,
        0L
    );
}

static int fake_prctl(
    void *context,
    int option,
    unsigned long argument2,
    unsigned long argument3,
    unsigned long argument4,
    unsigned long argument5
)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_PRCTL,
        option,
        (long)argument2,
        (long)argument3,
        (long)(argument4 ^ argument5)
    );
}

static long fake_seccomp(
    void *context,
    unsigned int operation,
    unsigned int flags,
    void *arguments
)
{
    (void)arguments;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_SECCOMP,
        (long)operation,
        (long)flags,
        0L,
        0L
    );
}

static long fake_landlock_create_ruleset(
    void *context,
    const void *attributes,
    size_t size,
    unsigned int flags
)
{
    (void)attributes;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_LANDLOCK_CREATE_RULESET,
        (long)size,
        (long)flags,
        0L,
        0L
    );
}

static long fake_landlock_add_rule(
    void *context,
    int ruleset_fd,
    int rule_type,
    const void *rule_attributes,
    unsigned int flags
)
{
    (void)rule_attributes;
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_LANDLOCK_ADD_RULE,
        ruleset_fd,
        rule_type,
        (long)flags,
        0L
    );
}

static long fake_landlock_restrict_self(
    void *context,
    int ruleset_fd,
    unsigned int flags
)
{
    return pchsi_fake_record(
        context,
        PCHSI_FAKE_LANDLOCK_RESTRICT_SELF,
        ruleset_fd,
        (long)flags,
        0L,
        0L
    );
}

static int fake_setrlimit(
    void *context,
    int resource,
    const struct rlimit *limit
)
{
    (void)limit;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_SETRLIMIT,
        resource,
        0L,
        0L,
        0L
    );
}

static int fake_pipe2(void *context, int fds[2], int flags)
{
    (void)fds;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_PIPE2,
        flags,
        0L,
        0L,
        0L
    );
}

static int fake_dup2(void *context, int oldfd, int newfd)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_DUP2,
        oldfd,
        newfd,
        0L,
        0L
    );
}

static int fake_kill(void *context, pid_t pid, int signal_number)
{
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_KILL,
        (long)pid,
        signal_number,
        0L,
        0L
    );
}

static pid_t fake_waitpid(
    void *context,
    pid_t pid,
    int *status,
    int options
)
{
    (void)status;
    return (pid_t)pchsi_fake_record(
        context,
        PCHSI_FAKE_WAITPID,
        (long)pid,
        options,
        0L,
        0L
    );
}

static int fake_poll(
    void *context,
    struct pollfd *fds,
    nfds_t count,
    int timeout
)
{
    (void)fds;
    return (int)pchsi_fake_record(
        context,
        PCHSI_FAKE_POLL,
        (long)count,
        timeout,
        0L,
        0L
    );
}

static void pchsi_fake_system_ops_init(
    struct pchsi_fake_system_ops_state *state,
    struct pchsi_system_ops *operations
)
{
    memset(state, 0, sizeof(*state));
    memset(operations, 0, sizeof(*operations));

    operations->context = state;
    operations->openat2_fn = fake_openat2;
    operations->openat_fn = fake_openat;
    operations->fstatat_fn = fake_fstatat;
    operations->fstat_fn = fake_fstat;
    operations->read_fn = fake_read;
    operations->write_fn = fake_write;
    operations->lseek_fn = fake_lseek;
    operations->close_fn = fake_close;
    operations->close_range_fn = fake_close_range;
    operations->mkdirat_fn = fake_mkdirat;
    operations->unlinkat_fn = fake_unlinkat;
    operations->renameat2_fn = fake_renameat2;
    operations->fsync_fn = fake_fsync;
    operations->clone3_fn = fake_clone3;
    operations->unshare_fn = fake_unshare;
    operations->setns_fn = fake_setns;
    operations->mount_fn = fake_mount;
    operations->umount2_fn = fake_umount2;
    operations->mount_setattr_fn = fake_mount_setattr;
    operations->pivot_root_fn = fake_pivot_root;
    operations->setgroups_fn = fake_setgroups;
    operations->setresuid_fn = fake_setresuid;
    operations->setresgid_fn = fake_setresgid;
    operations->setfsuid_fn = fake_setfsuid;
    operations->setfsgid_fn = fake_setfsgid;
    operations->prctl_fn = fake_prctl;
    operations->seccomp_fn = fake_seccomp;
    operations->landlock_create_ruleset_fn = fake_landlock_create_ruleset;
    operations->landlock_add_rule_fn = fake_landlock_add_rule;
    operations->landlock_restrict_self_fn = fake_landlock_restrict_self;
    operations->setrlimit_fn = fake_setrlimit;
    operations->pipe2_fn = fake_pipe2;
    operations->dup2_fn = fake_dup2;
    operations->kill_fn = fake_kill;
    operations->waitpid_fn = fake_waitpid;
    operations->poll_fn = fake_poll;
}
