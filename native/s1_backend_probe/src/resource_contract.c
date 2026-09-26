#include "pchsi_s1/resource_contract.h"

#include <limits.h>
#include <stddef.h>

static const struct pchsi_resource_contract PCHSI_CONTRACTS[] = {
    {
        PCHSI_PROFILE_PRODUCTION,
        "production",
        PCHSI_RLIMIT_CPU_SOFT,
        PCHSI_RLIMIT_CPU_HARD,
        PCHSI_RLIMIT_AS_BYTES,
        PCHSI_RLIMIT_FSIZE_BYTES,
        PCHSI_RLIMIT_NOFILE_COUNT,
        PCHSI_RLIMIT_NPROC_COUNT,
        PCHSI_RLIMIT_CORE_BYTES,
        PCHSI_PROBE_WALL_TIMEOUT_SECONDS,
        PCHSI_EVIDENCE_TMPFS_BYTES,
        PCHSI_EVIDENCE_TMPFS_INODES,
        PCHSI_TEMP_TMPFS_BYTES,
        PCHSI_TEMP_TMPFS_INODES,
        UINT64_C(0),
        UINT64_C(0),
        1,
        0,
        0
    },
    {
        PCHSI_PROFILE_P7_SYSCALL_CASE,
        "p7_syscall_case",
        PCHSI_RLIMIT_CPU_SOFT,
        PCHSI_RLIMIT_CPU_HARD,
        PCHSI_RLIMIT_AS_BYTES,
        PCHSI_RLIMIT_FSIZE_BYTES,
        PCHSI_RLIMIT_NOFILE_COUNT,
        PCHSI_RLIMIT_NPROC_COUNT,
        PCHSI_RLIMIT_CORE_BYTES,
        PCHSI_P7_CASE_TIMEOUT_SECONDS,
        PCHSI_EVIDENCE_TMPFS_BYTES,
        PCHSI_EVIDENCE_TMPFS_INODES,
        PCHSI_TEMP_TMPFS_BYTES,
        PCHSI_TEMP_TMPFS_INODES,
        UINT64_C(0),
        UINT64_C(0),
        0,
        0,
        0
    },
    {
        PCHSI_PROFILE_P15_RLIMIT_ATTRIBUTION,
        "p15_rlimit_attribution",
        PCHSI_RLIMIT_CPU_SOFT,
        PCHSI_RLIMIT_CPU_HARD,
        PCHSI_RLIMIT_AS_BYTES,
        PCHSI_RLIMIT_FSIZE_BYTES,
        PCHSI_RLIMIT_NOFILE_COUNT,
        PCHSI_RLIMIT_NPROC_COUNT,
        PCHSI_RLIMIT_CORE_BYTES,
        PCHSI_PROBE_WALL_TIMEOUT_SECONDS,
        PCHSI_EVIDENCE_TMPFS_BYTES,
        PCHSI_EVIDENCE_TMPFS_INODES,
        PCHSI_TEMP_TMPFS_BYTES,
        PCHSI_TEMP_TMPFS_INODES,
        UINT64_C(0),
        UINT64_C(0),
        0,
        1,
        0
    },
    {
        PCHSI_PROFILE_P18_LANDLOCK_ATTRIBUTION,
        "p18_landlock_attribution",
        PCHSI_RLIMIT_CPU_SOFT,
        PCHSI_RLIMIT_CPU_HARD,
        PCHSI_RLIMIT_AS_BYTES,
        PCHSI_RLIMIT_FSIZE_BYTES,
        PCHSI_RLIMIT_NOFILE_COUNT,
        PCHSI_RLIMIT_NPROC_COUNT,
        PCHSI_RLIMIT_CORE_BYTES,
        PCHSI_PROBE_WALL_TIMEOUT_SECONDS,
        PCHSI_EVIDENCE_TMPFS_BYTES,
        PCHSI_EVIDENCE_TMPFS_INODES,
        PCHSI_TEMP_TMPFS_BYTES,
        PCHSI_TEMP_TMPFS_INODES,
        PCHSI_LANDLOCK_TMPFS_BYTES,
        PCHSI_LANDLOCK_TMPFS_INODES,
        0,
        0,
        1
    },
    {
        PCHSI_PROFILE_P20_CLEANUP,
        "p20_cleanup",
        PCHSI_RLIMIT_CPU_SOFT,
        PCHSI_RLIMIT_CPU_HARD,
        PCHSI_RLIMIT_AS_BYTES,
        PCHSI_RLIMIT_FSIZE_BYTES,
        PCHSI_RLIMIT_NOFILE_COUNT,
        PCHSI_RLIMIT_NPROC_COUNT,
        PCHSI_RLIMIT_CORE_BYTES,
        PCHSI_PROBE_WALL_TIMEOUT_SECONDS,
        PCHSI_EVIDENCE_TMPFS_BYTES,
        PCHSI_EVIDENCE_TMPFS_INODES,
        PCHSI_TEMP_TMPFS_BYTES,
        PCHSI_TEMP_TMPFS_INODES,
        UINT64_C(0),
        UINT64_C(0),
        0,
        0,
        0
    }
};

int pchsi_resource_contract_for_profile(
    enum pchsi_probe_profile_id profile_id,
    struct pchsi_resource_contract *contract
)
{
    size_t index = (size_t)profile_id;

    if (
        contract == NULL
        || profile_id < PCHSI_PROFILE_PRODUCTION
        || profile_id >= PCHSI_PROFILE_COUNT
        || index >= sizeof(PCHSI_CONTRACTS) / sizeof(PCHSI_CONTRACTS[0])
    ) {
        return 0;
    }

    *contract = PCHSI_CONTRACTS[index];
    return 1;
}

int pchsi_profile_is_production_selectable(
    enum pchsi_probe_profile_id profile_id
)
{
    struct pchsi_resource_contract contract;

    if (!pchsi_resource_contract_for_profile(profile_id, &contract)) {
        return 0;
    }

    return contract.production_selectable;
}

uint64_t pchsi_p7_aggregate_deadline_seconds(
    uint64_t case_count
)
{
    if (
        case_count
        > (UINT64_MAX - PCHSI_P7_AGGREGATE_BASE_SECONDS)
            / PCHSI_P7_AGGREGATE_PER_CASE_SECONDS
    ) {
        return UINT64_MAX;
    }

    return (
        PCHSI_P7_AGGREGATE_BASE_SECONDS
        + PCHSI_P7_AGGREGATE_PER_CASE_SECONDS * case_count
    );
}

const char *pchsi_probe_profile_name(
    enum pchsi_probe_profile_id profile_id
)
{
    struct pchsi_resource_contract contract;

    if (!pchsi_resource_contract_for_profile(profile_id, &contract)) {
        return NULL;
    }

    return contract.profile_name;
}
