#ifndef PCHSI_S1_MOUNT_CONTRACT_H
#define PCHSI_S1_MOUNT_CONTRACT_H

#include "pchsi_s1/source_resolution.h"

#include <stddef.h>

#define PCHSI_MOUNTINFO_MAX_ENTRIES 128U
#define PCHSI_MOUNTINFO_PATH_MAX_BYTES 512U

enum pchsi_mount_class {
    PCHSI_MOUNT_RUNTIME = 0,
    PCHSI_MOUNT_REPOSITORY = 1,
    PCHSI_MOUNT_DATASET = 2
};

struct pchsi_mountinfo_entry {
    unsigned int mount_id;
    unsigned int parent_id;
    char mount_point[PCHSI_MOUNTINFO_PATH_MAX_BYTES + 1U];
    int read_only;
    int nosuid;
    int nodev;
    int noexec;
};

struct pchsi_mountinfo {
    struct pchsi_mountinfo_entry entries[PCHSI_MOUNTINFO_MAX_ENTRIES];
    size_t count;
};

enum pchsi_status pchsi_mountinfo_parse(
    const char *text,
    size_t size,
    struct pchsi_mountinfo *mounts
);

enum pchsi_status pchsi_mount_class_target(
    enum pchsi_mount_class mount_class,
    const char **target
);

enum pchsi_status pchsi_verify_mount_contract(
    enum pchsi_mount_class mount_class,
    const struct pchsi_mountinfo *mounts
);

#endif
