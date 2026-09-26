#include "pchsi_s1/resource_contract.h"

#include <assert.h>
#include <stdint.h>
#include <string.h>

static void test_exact_base_limits(void)
{
    struct pchsi_resource_contract contract;

    assert(
        pchsi_resource_contract_for_profile(
            PCHSI_PROFILE_PRODUCTION,
            &contract
        )
    );
    assert(contract.rlimit_cpu_soft == UINT64_C(2));
    assert(contract.rlimit_cpu_hard == UINT64_C(3));
    assert(contract.rlimit_as_bytes == UINT64_C(268435456));
    assert(contract.rlimit_fsize_bytes == UINT64_C(4194304));
    assert(contract.rlimit_nofile_count == UINT64_C(32));
    assert(contract.rlimit_nproc_count == UINT64_C(1));
    assert(contract.rlimit_core_bytes == UINT64_C(0));
    assert(contract.wall_timeout_seconds == UINT64_C(10));
    assert(contract.evidence_tmpfs_bytes == UINT64_C(8388608));
    assert(contract.evidence_tmpfs_inodes == UINT64_C(256));
    assert(contract.temporary_tmpfs_bytes == UINT64_C(16777216));
    assert(contract.temporary_tmpfs_inodes == UINT64_C(512));
}

static void test_only_production_is_selectable(void)
{
    assert(
        pchsi_profile_is_production_selectable(
            PCHSI_PROFILE_PRODUCTION
        )
    );
    assert(
        !pchsi_profile_is_production_selectable(
            PCHSI_PROFILE_P7_SYSCALL_CASE
        )
    );
    assert(
        !pchsi_profile_is_production_selectable(
            PCHSI_PROFILE_P15_RLIMIT_ATTRIBUTION
        )
    );
    assert(
        !pchsi_profile_is_production_selectable(
            PCHSI_PROFILE_P18_LANDLOCK_ATTRIBUTION
        )
    );
    assert(
        !pchsi_profile_is_production_selectable(
            PCHSI_PROFILE_P20_CLEANUP
        )
    );
}

static void test_attribution_profiles(void)
{
    struct pchsi_resource_contract p15;
    struct pchsi_resource_contract p18;

    assert(
        pchsi_resource_contract_for_profile(
            PCHSI_PROFILE_P15_RLIMIT_ATTRIBUTION,
            &p15
        )
    );
    assert(p15.process_creation_control_enabled == 1);
    assert(p15.production_selectable == 0);

    assert(
        pchsi_resource_contract_for_profile(
            PCHSI_PROFILE_P18_LANDLOCK_ATTRIBUTION,
            &p18
        )
    );
    assert(p18.landlock_attribution_enabled == 1);
    assert(p18.landlock_tmpfs_bytes == UINT64_C(4194304));
    assert(p18.landlock_tmpfs_inodes == UINT64_C(64));
    assert(p18.production_selectable == 0);
}

static void test_p7_deadline(void)
{
    assert(pchsi_p7_aggregate_deadline_seconds(UINT64_C(0)) == UINT64_C(30));
    assert(pchsi_p7_aggregate_deadline_seconds(UINT64_C(10)) == UINT64_C(60));
    assert(
        pchsi_p7_aggregate_deadline_seconds(UINT64_MAX)
        == UINT64_MAX
    );
}

int main(void)
{
    test_exact_base_limits();
    test_only_production_is_selectable();
    test_attribution_profiles();
    test_p7_deadline();
    return 0;
}
