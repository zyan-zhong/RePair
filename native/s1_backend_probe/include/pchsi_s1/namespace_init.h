#ifndef PCHSI_S1_NAMESPACE_INIT_H
#define PCHSI_S1_NAMESPACE_INIT_H

#include "pchsi_s1/supervisor.h"

struct pchsi_namespace_init_plan {
    const char *steps[12];
    size_t step_count;
    const char *rollback_steps[12];
    size_t rollback_step_count;
};

enum pchsi_status pchsi_namespace_init_plan(
    const struct pchsi_probe_contract *contract,
    struct pchsi_namespace_init_plan *plan
);

enum pchsi_status pchsi_namespace_init_execute(
    const struct pchsi_namespace_init_plan *plan,
    const struct pchsi_system_ops *operations
);

#endif
