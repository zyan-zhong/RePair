#include "pchsi_s1/linux_compat.h"

#include <errno.h>
#include <linux/openat2.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef SYS_openat2
#error SYS_openat2 is required
#endif

_Static_assert(
    sizeof(struct open_how) == sizeof(struct pchsi_open_how),
    "project open_how must match Linux UAPI"
);

long pchsi_linux_openat2(
    int dirfd,
    const char *path,
    const struct pchsi_open_how *how,
    size_t size
)
{
    struct open_how linux_how;

    if (how == NULL || size != sizeof(*how)) {
        errno = EINVAL;
        return -1L;
    }

    linux_how.flags = how->flags;
    linux_how.mode = how->mode;
    linux_how.resolve = how->resolve;

    return syscall(
        SYS_openat2,
        dirfd,
        path,
        &linux_how,
        sizeof(linux_how)
    );
}
