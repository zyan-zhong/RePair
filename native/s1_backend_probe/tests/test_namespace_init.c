#include "pchsi_s1/namespace_init.h"

#include <assert.h>
#include <string.h>

int main(void)
{
    const struct pchsi_probe_contract contract = {
        "S1_TEST_CONTRACT",
        1U
    };
    struct pchsi_namespace_init_plan plan;

    assert(
        pchsi_namespace_init_plan(&contract, &plan)
        == PCHSI_STATUS_OK
    );
    assert(plan.step_count == 11U);
    assert(
        strcmp(plan.steps[0], "close_inherited_fds") == 0
    );
    assert(
        strcmp(plan.steps[6], "detach_old_root") == 0
    );
    assert(
        strcmp(plan.steps[10], "install_collector_seccomp") == 0
    );
    assert(
        pchsi_namespace_init_execute(
            &plan,
            (const struct pchsi_system_ops *)1
        )
        == PCHSI_STATUS_EXECUTION_NOT_APPROVED
    );

    return 0;
}
