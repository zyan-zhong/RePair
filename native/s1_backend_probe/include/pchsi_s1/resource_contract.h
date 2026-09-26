#ifndef PCHSI_S1_RESOURCE_CONTRACT_H
#define PCHSI_S1_RESOURCE_CONTRACT_H

#include <stdint.h>

#define PCHSI_MIB UINT64_C(1048576)

#define PCHSI_EVIDENCE_TMPFS_BYTES (UINT64_C(8) * PCHSI_MIB)
#define PCHSI_EVIDENCE_TMPFS_INODES UINT64_C(256)
#define PCHSI_TEMP_TMPFS_BYTES (UINT64_C(16) * PCHSI_MIB)
#define PCHSI_TEMP_TMPFS_INODES UINT64_C(512)
#define PCHSI_BOOTSTRAP_TMPFS_BYTES (UINT64_C(4) * PCHSI_MIB)
#define PCHSI_BOOTSTRAP_TMPFS_INODES UINT64_C(32)
#define PCHSI_COLLECTOR_TMPFS_BYTES (UINT64_C(4) * PCHSI_MIB)
#define PCHSI_COLLECTOR_TMPFS_INODES UINT64_C(32)
#define PCHSI_LANDLOCK_TMPFS_BYTES (UINT64_C(4) * PCHSI_MIB)
#define PCHSI_LANDLOCK_TMPFS_INODES UINT64_C(64)

#define PCHSI_MAX_EVIDENCE_FILES UINT64_C(16)
#define PCHSI_MAX_EVIDENCE_TOTAL_BYTES UINT64_C(4194304)
#define PCHSI_MAX_EVIDENCE_SINGLE_FILE_BYTES UINT64_C(2097152)
#define PCHSI_MAX_STDOUT_BYTES UINT64_C(1048576)
#define PCHSI_MAX_STDERR_BYTES UINT64_C(1048576)
#define PCHSI_MAX_EVIDENCE_DIRECTORY_DEPTH UINT64_C(1)

#define PCHSI_RLIMIT_CPU_SOFT UINT64_C(2)
#define PCHSI_RLIMIT_CPU_HARD UINT64_C(3)
#define PCHSI_RLIMIT_AS_BYTES UINT64_C(268435456)
#define PCHSI_RLIMIT_FSIZE_BYTES UINT64_C(4194304)
#define PCHSI_RLIMIT_NOFILE_COUNT UINT64_C(32)
#define PCHSI_RLIMIT_NPROC_COUNT UINT64_C(1)
#define PCHSI_RLIMIT_CORE_BYTES UINT64_C(0)

#define PCHSI_PROBE_WALL_TIMEOUT_SECONDS UINT64_C(10)
#define PCHSI_P7_CASE_TIMEOUT_SECONDS UINT64_C(2)
#define PCHSI_P7_AGGREGATE_BASE_SECONDS UINT64_C(30)
#define PCHSI_P7_AGGREGATE_PER_CASE_SECONDS UINT64_C(3)

enum pchsi_probe_profile_id {
    PCHSI_PROFILE_PRODUCTION = 0,
    PCHSI_PROFILE_P7_SYSCALL_CASE,
    PCHSI_PROFILE_P15_RLIMIT_ATTRIBUTION,
    PCHSI_PROFILE_P18_LANDLOCK_ATTRIBUTION,
    PCHSI_PROFILE_P20_CLEANUP,
    PCHSI_PROFILE_COUNT
};

struct pchsi_resource_contract {
    enum pchsi_probe_profile_id profile_id;
    const char *profile_name;
    uint64_t rlimit_cpu_soft;
    uint64_t rlimit_cpu_hard;
    uint64_t rlimit_as_bytes;
    uint64_t rlimit_fsize_bytes;
    uint64_t rlimit_nofile_count;
    uint64_t rlimit_nproc_count;
    uint64_t rlimit_core_bytes;
    uint64_t wall_timeout_seconds;
    uint64_t evidence_tmpfs_bytes;
    uint64_t evidence_tmpfs_inodes;
    uint64_t temporary_tmpfs_bytes;
    uint64_t temporary_tmpfs_inodes;
    uint64_t landlock_tmpfs_bytes;
    uint64_t landlock_tmpfs_inodes;
    int production_selectable;
    int process_creation_control_enabled;
    int landlock_attribution_enabled;
};

int pchsi_resource_contract_for_profile(
    enum pchsi_probe_profile_id profile_id,
    struct pchsi_resource_contract *contract
);

int pchsi_profile_is_production_selectable(
    enum pchsi_probe_profile_id profile_id
);

uint64_t pchsi_p7_aggregate_deadline_seconds(
    uint64_t case_count
);

const char *pchsi_probe_profile_name(
    enum pchsi_probe_profile_id profile_id
);

#endif
