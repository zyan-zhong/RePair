#include "pchsi_s1/supervisor.h"
#include "pchsi_s1/system_ops.h"

#include <string.h>

enum pchsi_status pchsi_supervisor_plan(
    const struct pchsi_probe_contract *contract,
    struct pchsi_supervisor_plan *plan
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

    plan->steps[0] = "validate_execution_record";
    plan->steps[1] = "validate_payload_manifest";
    plan->steps[2] = "prepare_namespace_plan";
    plan->steps[3] = "prepare_evidence_staging";
    plan->steps[4] = "dispatch_injected_executor";
    plan->step_count = 5U;

    plan->rollback_steps[0] = "terminate_collector_child";
    plan->rollback_steps[1] = "detach_old_root";
    plan->rollback_steps[2] = "remove_staging_tree";
    plan->rollback_step_count = 3U;

    return PCHSI_STATUS_OK;
}

enum pchsi_status pchsi_supervisor_execute(
    const struct pchsi_supervisor_plan *plan,
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
