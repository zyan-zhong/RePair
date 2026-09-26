#ifndef PCHSI_S1_SECURITY_STATE_H
#define PCHSI_S1_SECURITY_STATE_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

enum pchsi_security_state_status {
    PCHSI_SECURITY_STATE_OK = 0,
    PCHSI_SECURITY_STATE_INVALID_ARGUMENT,
    PCHSI_SECURITY_STATE_MALFORMED_STATUS,
    PCHSI_SECURITY_STATE_MISSING_FIELD,
    PCHSI_SECURITY_STATE_CAPABILITY_LEAK,
    PCHSI_SECURITY_STATE_NO_NEW_PRIVS_MISSING,
    PCHSI_SECURITY_STATE_PROCFS_OPTIONS_INVALID,
    PCHSI_SECURITY_STATE_ID_MAP_INVALID
};

struct pchsi_security_state {
    uint64_t cap_inheritable;
    uint64_t cap_permitted;
    uint64_t cap_effective;
    uint64_t cap_bounding;
    uint64_t cap_ambient;
    int no_new_privs;
};

struct pchsi_identity_map {
    uid_t trusted_inside_id;
    uid_t collector_inside_id;
    uid_t trusted_outside_id;
    uid_t collector_outside_id;
    unsigned int range_length;
};

enum pchsi_security_state_status pchsi_parse_proc_status(
    const char *text,
    size_t size,
    struct pchsi_security_state *state
);

enum pchsi_security_state_status pchsi_validate_collector_security_state(
    const struct pchsi_security_state *state
);

enum pchsi_security_state_status pchsi_validate_procfs_mount_options(
    const char *options
);

enum pchsi_security_state_status pchsi_validate_identity_map(
    const struct pchsi_identity_map *mapping
);

const char *pchsi_security_state_status_name(
    enum pchsi_security_state_status status
);

#endif
