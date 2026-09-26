#ifndef PCHSI_S1_SYSTEM_OPS_H
#define PCHSI_S1_SYSTEM_OPS_H

#include "pchsi_s1/linux_compat.h"

#include <poll.h>
#include <signal.h>
#include <stddef.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>

struct pchsi_system_ops {
    void *context;

    int (*openat2_fn)(
        void *context,
        int dirfd,
        const char *path,
        const struct pchsi_open_how *how,
        size_t size
    );
    int (*openat_fn)(
        void *context,
        int dirfd,
        const char *path,
        int flags,
        unsigned int mode
    );
    int (*fstatat_fn)(
        void *context,
        int dirfd,
        const char *path,
        struct stat *status,
        int flags
    );
    int (*fstat_fn)(
        void *context,
        int file_descriptor,
        struct stat *status
    );
    ssize_t (*read_fn)(
        void *context,
        int file_descriptor,
        void *buffer,
        size_t size
    );
    ssize_t (*write_fn)(
        void *context,
        int file_descriptor,
        const void *buffer,
        size_t size
    );
    off_t (*lseek_fn)(
        void *context,
        int file_descriptor,
        off_t offset,
        int whence
    );
    int (*close_fn)(
        void *context,
        int file_descriptor
    );
    int (*close_range_fn)(
        void *context,
        unsigned int first,
        unsigned int last,
        int flags
    );
    int (*mkdirat_fn)(
        void *context,
        int dirfd,
        const char *path,
        mode_t mode
    );
    int (*unlinkat_fn)(
        void *context,
        int dirfd,
        const char *path,
        int flags
    );
    int (*renameat2_fn)(
        void *context,
        int olddirfd,
        const char *oldpath,
        int newdirfd,
        const char *newpath,
        unsigned int flags
    );
    int (*fsync_fn)(
        void *context,
        int file_descriptor
    );

    long (*clone3_fn)(
        void *context,
        const struct pchsi_clone_args *arguments,
        size_t size
    );
    int (*unshare_fn)(
        void *context,
        int flags
    );
    int (*setns_fn)(
        void *context,
        int file_descriptor,
        int namespace_type
    );
    int (*mount_fn)(
        void *context,
        const char *source,
        const char *target,
        const char *filesystem_type,
        unsigned long flags,
        const void *data
    );
    int (*umount2_fn)(
        void *context,
        const char *target,
        int flags
    );
    long (*mount_setattr_fn)(
        void *context,
        int dirfd,
        const char *path,
        unsigned int flags,
        const struct pchsi_mount_attr *attributes,
        size_t size
    );
    long (*pivot_root_fn)(
        void *context,
        const char *new_root,
        const char *put_old
    );

    int (*setgroups_fn)(
        void *context,
        size_t size,
        const gid_t *groups
    );
    int (*setresuid_fn)(
        void *context,
        uid_t real_uid,
        uid_t effective_uid,
        uid_t saved_uid
    );
    int (*setresgid_fn)(
        void *context,
        gid_t real_gid,
        gid_t effective_gid,
        gid_t saved_gid
    );
    int (*setfsuid_fn)(
        void *context,
        uid_t filesystem_uid
    );
    int (*setfsgid_fn)(
        void *context,
        gid_t filesystem_gid
    );

    int (*prctl_fn)(
        void *context,
        int option,
        unsigned long argument2,
        unsigned long argument3,
        unsigned long argument4,
        unsigned long argument5
    );
    long (*seccomp_fn)(
        void *context,
        unsigned int operation,
        unsigned int flags,
        void *arguments
    );
    long (*landlock_create_ruleset_fn)(
        void *context,
        const void *attributes,
        size_t size,
        unsigned int flags
    );
    long (*landlock_add_rule_fn)(
        void *context,
        int ruleset_fd,
        int rule_type,
        const void *rule_attributes,
        unsigned int flags
    );
    long (*landlock_restrict_self_fn)(
        void *context,
        int ruleset_fd,
        unsigned int flags
    );
    int (*setrlimit_fn)(
        void *context,
        int resource,
        const struct rlimit *limit
    );

    int (*pipe2_fn)(
        void *context,
        int file_descriptors[2],
        int flags
    );
    int (*dup2_fn)(
        void *context,
        int old_file_descriptor,
        int new_file_descriptor
    );
    int (*kill_fn)(
        void *context,
        pid_t process_id,
        int signal_number
    );
    pid_t (*waitpid_fn)(
        void *context,
        pid_t process_id,
        int *status,
        int options
    );
    int (*poll_fn)(
        void *context,
        struct pollfd *file_descriptors,
        nfds_t count,
        int timeout_milliseconds
    );
};

const struct pchsi_system_ops *pchsi_real_system_ops(void);

#endif
