#ifndef PCHSI_S1_SOURCE_RESOLUTION_H
#define PCHSI_S1_SOURCE_RESOLUTION_H

#include "pchsi_s1/system_ops.h"

#include <stddef.h>

#define PCHSI_SOURCE_PATH_MAX_BYTES 512U

enum pchsi_status {
    PCHSI_STATUS_OK = 0,
    PCHSI_STATUS_INVALID_ARGUMENT,
    PCHSI_STATUS_SOURCE_PATH_INVALID,
    PCHSI_STATUS_SOURCE_OPEN_FAILED,
    PCHSI_STATUS_SOURCE_NOT_REGULAR,
    PCHSI_STATUS_SOURCE_IDENTITY_CHANGED,
    PCHSI_STATUS_SOURCE_HASH_MISMATCH,
    PCHSI_STATUS_SOURCE_COPY_FAILED,
    PCHSI_STATUS_SOURCE_SEAL_FAILED,
    PCHSI_STATUS_MOUNT_PARSE_FAILED,
    PCHSI_STATUS_MOUNT_CLASS_INVALID,
    PCHSI_STATUS_MOUNT_CONTRACT_FAILED,
    PCHSI_STATUS_MOUNT_WRITABLE_DESCENDANT,
    PCHSI_STATUS_ALLOCATION_FAILED
};

struct pchsi_file_identity {
    dev_t device;
    ino_t inode;
    off_t size;
    mode_t mode;
};

enum pchsi_status pchsi_validate_relative_source_path(
    const char *relative_path
);

enum pchsi_status pchsi_open_source_beneath_repo(
    int repo_dirfd,
    const char *relative_path,
    const struct pchsi_system_ops *operations,
    int *source_fd,
    struct pchsi_file_identity *identity
);

const char *pchsi_status_name(enum pchsi_status status);

#endif
