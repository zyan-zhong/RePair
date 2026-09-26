#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p15_limited(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P15_LIMITED",
        "rlimit_limited",
        "S1_P15_RLIMIT_ATTRIBUTION_V1",
        "LIMIT_ENFORCED",
        10U
    };

    return descriptor;
}
