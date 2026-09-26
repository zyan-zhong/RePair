#include "pchsi_s1/namespace_init.h"
#include "pchsi_s1/system_ops.h"

#include <string.h>

enum pchsi_status pchsi_namespace_init_plan(
    const struct pchsi_probe_contract *contract,
    struct pchsi_namespace_init_plan *plan
)
{
    if (
        contract == NULL
        || contract->contract_id == NULL
        || contract->contract_id[0] == '\0'
        || plan == NULL
    ) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    memset(plan, 0, sizeof(*plan));

    plan->steps[0] = "close_inherited_fds";
    plan->steps[1] = "verify_fd_allowlist";
    plan->steps[2] = "make_mounts_private";
    plan->steps[3] = "construct_restricted_root";
    plan->steps[4] = "bind_read_only_inputs";
    plan->steps[5] = "pivot_root";
    plan->steps[6] = "detach_old_root";
    plan->steps[7] = "mount_restricted_proc";
    plan->steps[8] = "drop_credentials";
    plan->steps[9] = "install_landlock";
    plan->steps[10] = "install_collector_seccomp";
    plan->step_count = 11U;

    plan->rollback_steps[0] = "terminate_namespace_child";
    plan->rollback_steps[1] = "detach_old_root";
    plan->rollback_steps[2] = "unmount_restricted_proc";
    plan->rollback_steps[3] = "remove_restricted_root";
    plan->rollback_step_count = 4U;

    return PCHSI_STATUS_OK;
}

enum pchsi_status pchsi_namespace_init_execute(
    const struct pchsi_namespace_init_plan *plan,
    const struct pchsi_system_ops *operations
)
{
    if (
        plan == NULL
        || plan->step_count == 0U
        || operations == NULL
    ) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    return PCHSI_STATUS_EXECUTION_NOT_APPROVED;
}
