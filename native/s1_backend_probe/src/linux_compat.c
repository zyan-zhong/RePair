#include "pchsi_s1/linux_compat.h"

#include <limits.h>

_Static_assert(sizeof(struct pchsi_open_how) == 24U, "open_how size");
_Static_assert(sizeof(struct pchsi_mount_attr) == 32U, "mount_attr size");
_Static_assert(sizeof(struct pchsi_clone_args) == 88U, "clone_args size");
_Static_assert(CHAR_BIT == 8, "eight-bit bytes required");

int pchsi_linux_compatibility_compile_check(void)
{
    return 1;
}
