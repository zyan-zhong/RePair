#include "pchsi_s1/security_state.h"

#include <assert.h>
#include <string.h>

static const char SECURE_STATUS[] =
    "Name:\tpython\n"
    "CapInh:\t0000000000000000\n"
    "CapPrm:\t0000000000000000\n"
    "CapEff:\t0000000000000000\n"
    "CapBnd:\t0000000000000000\n"
    "CapAmb:\t0000000000000000\n"
    "NoNewPrivs:\t1\n";

static const char LEAKED_STATUS[] =
    "Name:\tpython\n"
    "CapInh:\t0000000000000000\n"
    "CapPrm:\t0000000000000000\n"
    "CapEff:\t0000000000000001\n"
    "CapBnd:\t0000000000000000\n"
    "CapAmb:\t0000000000000000\n"
    "NoNewPrivs:\t1\n";

static void test_secure_status(void)
{
    struct pchsi_security_state state;

    assert(
        pchsi_parse_proc_status(
            SECURE_STATUS,
            strlen(SECURE_STATUS),
            &state
        )
        == PCHSI_SECURITY_STATE_OK
    );
    assert(
        pchsi_validate_collector_security_state(&state)
        == PCHSI_SECURITY_STATE_OK
    );
}

static void test_capability_leak(void)
{
    struct pchsi_security_state state;

    assert(
        pchsi_parse_proc_status(
            LEAKED_STATUS,
            strlen(LEAKED_STATUS),
            &state
        )
        == PCHSI_SECURITY_STATE_OK
    );
    assert(
        pchsi_validate_collector_security_state(&state)
        == PCHSI_SECURITY_STATE_CAPABILITY_LEAK
    );
}

static void test_no_new_privs_required(void)
{
    struct pchsi_security_state state = {
        UINT64_C(0),
        UINT64_C(0),
        UINT64_C(0),
        UINT64_C(0),
        UINT64_C(0),
        0
    };

    assert(
        pchsi_validate_collector_security_state(&state)
        == PCHSI_SECURITY_STATE_NO_NEW_PRIVS_MISSING
    );
}

static void test_procfs_options(void)
{
    assert(
        pchsi_validate_procfs_mount_options(
            "rw,nosuid,nodev,noexec,relatime,hidepid=4,subset=pid"
        )
        == PCHSI_SECURITY_STATE_OK
    );
    assert(
        pchsi_validate_procfs_mount_options(
            "rw,nosuid,nodev,noexec,relatime,hidepid=2,subset=pid"
        )
        == PCHSI_SECURITY_STATE_PROCFS_OPTIONS_INVALID
    );
}

static void test_identity_map(void)
{
    struct pchsi_identity_map mapping = {
        (uid_t)0,
        (uid_t)1,
        (uid_t)100000,
        (uid_t)100001,
        1U
    };

    assert(
        pchsi_validate_identity_map(&mapping)
        == PCHSI_SECURITY_STATE_OK
    );

    mapping.collector_inside_id = mapping.trusted_inside_id;
    assert(
        pchsi_validate_identity_map(&mapping)
        == PCHSI_SECURITY_STATE_ID_MAP_INVALID
    );
}

int main(void)
{
    test_secure_status();
    test_capability_leak();
    test_no_new_privs_required();
    test_procfs_options();
    test_identity_map();
    return 0;
}
