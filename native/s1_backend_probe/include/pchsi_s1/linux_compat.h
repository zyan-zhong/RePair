#ifndef PCHSI_S1_LINUX_COMPAT_H
#define PCHSI_S1_LINUX_COMPAT_H

#include <stddef.h>
#include <stdint.h>

#define PCHSI_RESOLVE_NO_XDEV UINT64_C(0x01)
#define PCHSI_RESOLVE_NO_MAGICLINKS UINT64_C(0x02)
#define PCHSI_RESOLVE_NO_SYMLINKS UINT64_C(0x04)
#define PCHSI_RESOLVE_BENEATH UINT64_C(0x08)
#define PCHSI_RESOLVE_IN_ROOT UINT64_C(0x10)
#define PCHSI_RESOLVE_CACHED UINT64_C(0x20)

#define PCHSI_MOUNT_ATTR_RDONLY UINT64_C(0x00000001)
#define PCHSI_MOUNT_ATTR_NOSUID UINT64_C(0x00000002)
#define PCHSI_MOUNT_ATTR_NODEV UINT64_C(0x00000004)
#define PCHSI_MOUNT_ATTR_NOEXEC UINT64_C(0x00000008)

struct pchsi_open_how {
    uint64_t flags;
    uint64_t mode;
    uint64_t resolve;
};

struct pchsi_mount_attr {
    uint64_t attr_set;
    uint64_t attr_clr;
    uint64_t propagation;
    uint64_t userns_fd;
};

struct pchsi_clone_args {
    uint64_t flags;
    uint64_t pidfd;
    uint64_t child_tid;
    uint64_t parent_tid;
    uint64_t exit_signal;
    uint64_t stack;
    uint64_t stack_size;
    uint64_t tls;
    uint64_t set_tid;
    uint64_t set_tid_size;
    uint64_t cgroup;
};

long pchsi_linux_mount_setattr(
    int dirfd,
    const char *path,
    unsigned int flags,
    const struct pchsi_mount_attr *attributes,
    size_t size
);

long pchsi_linux_openat2(
    int dirfd,
    const char *path,
    const struct pchsi_open_how *how,
    size_t size
);

int pchsi_linux_compatibility_compile_check(void);

#endif
