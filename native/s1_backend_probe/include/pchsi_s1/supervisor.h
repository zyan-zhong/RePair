#ifndef PCHSI_S1_SUPERVISOR_H
#define PCHSI_S1_SUPERVISOR_H

#include <stddef.h>

struct pchsi_system_ops;

enum pchsi_status {
    PCHSI_STATUS_OK = 0,
    PCHSI_STATUS_INVALID_ARGUMENT = 1,
    PCHSI_STATUS_EXECUTION_NOT_APPROVED = 2
};

struct pchsi_probe_contract {
    const char *contract_id;
    unsigned int profile_id;
};

struct pchsi_supervisor_plan {
    const char *steps[8];
    size_t step_count;
    const char *rollback_steps[8];
    size_t rollback_step_count;
};

enum pchsi_status pchsi_supervisor_plan(
    const struct pchsi_probe_contract *contract,
    struct pchsi_supervisor_plan *plan
);

enum pchsi_status pchsi_supervisor_execute(
    const struct pchsi_supervisor_plan *plan,
    const struct pchsi_system_ops *operations
);

#endif
