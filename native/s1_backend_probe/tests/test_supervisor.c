#include "pchsi_s1/supervisor.h"

#include <assert.h>
#include <string.h>

int main(void)
{
    const struct pchsi_probe_contract contract = {
        "S1_TEST_CONTRACT",
        1U
    };
    struct pchsi_supervisor_plan plan;

    assert(
        pchsi_supervisor_plan(&contract, &plan)
        == PCHSI_STATUS_OK
    );
    assert(plan.step_count == 5U);
    assert(
        strcmp(plan.steps[0], "validate_execution_record") == 0
    );
    assert(
        strcmp(
            plan.rollback_steps[0],
            "terminate_collector_child"
        ) == 0
    );
    assert(
        pchsi_supervisor_execute(
            &plan,
            (const struct pchsi_system_ops *)1
        )
        == PCHSI_STATUS_EXECUTION_NOT_APPROVED
    );

    return 0;
}
