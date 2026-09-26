#include "pchsi_s1/linux_compat.h"

#include <errno.h>
#include <linux/mount.h>
#include <sys/syscall.h>
#include <unistd.h>

#ifndef SYS_mount_setattr
#error SYS_mount_setattr is required
#endif

_Static_assert(
    sizeof(struct mount_attr) == sizeof(struct pchsi_mount_attr),
    "project mount_attr must match Linux UAPI"
);

long pchsi_linux_mount_setattr(
    int dirfd,
    const char *path,
    unsigned int flags,
    const struct pchsi_mount_attr *attributes,
    size_t size
)
{
    struct mount_attr linux_attributes;

    if (attributes == NULL || size != sizeof(*attributes)) {
        errno = EINVAL;
        return -1L;
    }

    linux_attributes.attr_set = attributes->attr_set;
    linux_attributes.attr_clr = attributes->attr_clr;
    linux_attributes.propagation = attributes->propagation;
    linux_attributes.userns_fd = attributes->userns_fd;

    return syscall(
        SYS_mount_setattr,
        dirfd,
        path,
        flags,
        &linux_attributes,
        sizeof(linux_attributes)
    );
}
