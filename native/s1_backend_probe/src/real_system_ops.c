#include "pchsi_s1/system_ops.h"

#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <linux/landlock.h>
#include <linux/seccomp.h>
#include <sched.h>
#include <stdarg.h>
#include <stdio.h>
#include <sys/fsuid.h>
#include <sys/mount.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef CLOSE_RANGE_UNSHARE
#include <linux/close_range.h>
#endif

static int pchsi_real_openat2(
    void *context,
    int dirfd,
    const char *path,
    const struct pchsi_open_how *how,
    size_t size
)
{
    (void)context;
    return (int)pchsi_linux_openat2(dirfd, path, how, size);
}

static int pchsi_real_openat(
    void *context,
    int dirfd,
    const char *path,
    int flags,
    unsigned int mode
)
{
    (void)context;
    return openat(dirfd, path, flags, (mode_t)mode);
}

static int pchsi_real_fstatat(
    void *context,
    int dirfd,
    const char *path,
    struct stat *status,
    int flags
)
{
    (void)context;
    return fstatat(dirfd, path, status, flags);
}

static int pchsi_real_fstat(
    void *context,
    int file_descriptor,
    struct stat *status
)
{
    (void)context;
    return fstat(file_descriptor, status);
}

static ssize_t pchsi_real_read(
    void *context,
    int file_descriptor,
    void *buffer,
    size_t size
)
{
    (void)context;
    return read(file_descriptor, buffer, size);
}

static ssize_t pchsi_real_write(
    void *context,
    int file_descriptor,
    const void *buffer,
    size_t size
)
{
    (void)context;
    return write(file_descriptor, buffer, size);
}

static off_t pchsi_real_lseek(
    void *context,
    int file_descriptor,
    off_t offset,
    int whence
)
{
    (void)context;
    return lseek(file_descriptor, offset, whence);
}

static int pchsi_real_close(void *context, int file_descriptor)
{
    (void)context;
    return close(file_descriptor);
}

static int pchsi_real_close_range(
    void *context,
    unsigned int first,
    unsigned int last,
    int flags
)
{
    (void)context;
    return close_range(first, last, flags);
}

static int pchsi_real_mkdirat(
    void *context,
    int dirfd,
    const char *path,
    mode_t mode
)
{
    (void)context;
    return mkdirat(dirfd, path, mode);
}

static int pchsi_real_unlinkat(
    void *context,
    int dirfd,
    const char *path,
    int flags
)
{
    (void)context;
    return unlinkat(dirfd, path, flags);
}

static int pchsi_real_renameat2(
    void *context,
    int olddirfd,
    const char *oldpath,
    int newdirfd,
    const char *newpath,
    unsigned int flags
)
{
    (void)context;
    return renameat2(
        olddirfd,
        oldpath,
        newdirfd,
        newpath,
        flags
    );
}

static int pchsi_real_fsync(void *context, int file_descriptor)
{
    (void)context;
    return fsync(file_descriptor);
}

static long pchsi_real_clone3(
    void *context,
    const struct pchsi_clone_args *arguments,
    size_t size
)
{
    (void)context;
#ifdef SYS_clone3
    return syscall(SYS_clone3, arguments, size);
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static int pchsi_real_unshare(void *context, int flags)
{
    (void)context;
    return unshare(flags);
}

static int pchsi_real_setns(
    void *context,
    int file_descriptor,
    int namespace_type
)
{
    (void)context;
    return setns(file_descriptor, namespace_type);
}

static int pchsi_real_mount(
    void *context,
    const char *source,
    const char *target,
    const char *filesystem_type,
    unsigned long flags,
    const void *data
)
{
    (void)context;
    return mount(source, target, filesystem_type, flags, data);
}

static int pchsi_real_umount2(
    void *context,
    const char *target,
    int flags
)
{
    (void)context;
    return umount2(target, flags);
}

static long pchsi_real_mount_setattr(
    void *context,
    int dirfd,
    const char *path,
    unsigned int flags,
    const struct pchsi_mount_attr *attributes,
    size_t size
)
{
    (void)context;
    return pchsi_linux_mount_setattr(
        dirfd,
        path,
        flags,
        attributes,
        size
    );
}

static long pchsi_real_pivot_root(
    void *context,
    const char *new_root,
    const char *put_old
)
{
    (void)context;
#ifdef SYS_pivot_root
    return syscall(SYS_pivot_root, new_root, put_old);
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static int pchsi_real_setgroups(
    void *context,
    size_t size,
    const gid_t *groups
)
{
    (void)context;
    return setgroups(size, groups);
}

static int pchsi_real_setresuid(
    void *context,
    uid_t real_uid,
    uid_t effective_uid,
    uid_t saved_uid
)
{
    (void)context;
    return setresuid(real_uid, effective_uid, saved_uid);
}

static int pchsi_real_setresgid(
    void *context,
    gid_t real_gid,
    gid_t effective_gid,
    gid_t saved_gid
)
{
    (void)context;
    return setresgid(real_gid, effective_gid, saved_gid);
}

static int pchsi_real_setfsuid(void *context, uid_t filesystem_uid)
{
    (void)context;
    return setfsuid(filesystem_uid);
}

static int pchsi_real_setfsgid(void *context, gid_t filesystem_gid)
{
    (void)context;
    return setfsgid(filesystem_gid);
}

static int pchsi_real_prctl(
    void *context,
    int option,
    unsigned long argument2,
    unsigned long argument3,
    unsigned long argument4,
    unsigned long argument5
)
{
    (void)context;
    return prctl(
        option,
        argument2,
        argument3,
        argument4,
        argument5
    );
}

static long pchsi_real_seccomp(
    void *context,
    unsigned int operation,
    unsigned int flags,
    void *arguments
)
{
    (void)context;
#ifdef SYS_seccomp
    return syscall(SYS_seccomp, operation, flags, arguments);
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static long pchsi_real_landlock_create_ruleset(
    void *context,
    const void *attributes,
    size_t size,
    unsigned int flags
)
{
    (void)context;
#ifdef SYS_landlock_create_ruleset
    return syscall(
        SYS_landlock_create_ruleset,
        attributes,
        size,
        flags
    );
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static long pchsi_real_landlock_add_rule(
    void *context,
    int ruleset_fd,
    int rule_type,
    const void *rule_attributes,
    unsigned int flags
)
{
    (void)context;
#ifdef SYS_landlock_add_rule
    return syscall(
        SYS_landlock_add_rule,
        ruleset_fd,
        rule_type,
        rule_attributes,
        flags
    );
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static long pchsi_real_landlock_restrict_self(
    void *context,
    int ruleset_fd,
    unsigned int flags
)
{
    (void)context;
#ifdef SYS_landlock_restrict_self
    return syscall(
        SYS_landlock_restrict_self,
        ruleset_fd,
        flags
    );
#else
    errno = ENOSYS;
    return -1L;
#endif
}

static int pchsi_real_setrlimit(
    void *context,
    int resource,
    const struct rlimit *limit
)
{
    (void)context;
    return setrlimit(resource, limit);
}

static int pchsi_real_pipe2(
    void *context,
    int file_descriptors[2],
    int flags
)
{
    (void)context;
    return pipe2(file_descriptors, flags);
}

static int pchsi_real_dup2(
    void *context,
    int old_file_descriptor,
    int new_file_descriptor
)
{
    (void)context;
    return dup2(old_file_descriptor, new_file_descriptor);
}

static int pchsi_real_kill(
    void *context,
    pid_t process_id,
    int signal_number
)
{
    (void)context;
    return kill(process_id, signal_number);
}

static pid_t pchsi_real_waitpid(
    void *context,
    pid_t process_id,
    int *status,
    int options
)
{
    (void)context;
    return waitpid(process_id, status, options);
}

static int pchsi_real_poll(
    void *context,
    struct pollfd *file_descriptors,
    nfds_t count,
    int timeout_milliseconds
)
{
    (void)context;
    return poll(file_descriptors, count, timeout_milliseconds);
}

const struct pchsi_system_ops *pchsi_real_system_ops(void)
{
    static const struct pchsi_system_ops operations = {
        .context = NULL,
        .openat2_fn = pchsi_real_openat2,
        .openat_fn = pchsi_real_openat,
        .fstatat_fn = pchsi_real_fstatat,
        .fstat_fn = pchsi_real_fstat,
        .read_fn = pchsi_real_read,
        .write_fn = pchsi_real_write,
        .lseek_fn = pchsi_real_lseek,
        .close_fn = pchsi_real_close,
        .close_range_fn = pchsi_real_close_range,
        .mkdirat_fn = pchsi_real_mkdirat,
        .unlinkat_fn = pchsi_real_unlinkat,
        .renameat2_fn = pchsi_real_renameat2,
        .fsync_fn = pchsi_real_fsync,
        .clone3_fn = pchsi_real_clone3,
        .unshare_fn = pchsi_real_unshare,
        .setns_fn = pchsi_real_setns,
        .mount_fn = pchsi_real_mount,
        .umount2_fn = pchsi_real_umount2,
        .mount_setattr_fn = pchsi_real_mount_setattr,
        .pivot_root_fn = pchsi_real_pivot_root,
        .setgroups_fn = pchsi_real_setgroups,
        .setresuid_fn = pchsi_real_setresuid,
        .setresgid_fn = pchsi_real_setresgid,
        .setfsuid_fn = pchsi_real_setfsuid,
        .setfsgid_fn = pchsi_real_setfsgid,
        .prctl_fn = pchsi_real_prctl,
        .seccomp_fn = pchsi_real_seccomp,
        .landlock_create_ruleset_fn = pchsi_real_landlock_create_ruleset,
        .landlock_add_rule_fn = pchsi_real_landlock_add_rule,
        .landlock_restrict_self_fn = pchsi_real_landlock_restrict_self,
        .setrlimit_fn = pchsi_real_setrlimit,
        .pipe2_fn = pchsi_real_pipe2,
        .dup2_fn = pchsi_real_dup2,
        .kill_fn = pchsi_real_kill,
        .waitpid_fn = pchsi_real_waitpid,
        .poll_fn = pchsi_real_poll,
    };

    return &operations;
}
