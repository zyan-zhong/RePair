#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p19(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P19",
        "timeout",
        "S1_PRODUCTION_V1",
        "TIMEOUT_ENFORCED",
        10U
    };

    return descriptor;
}
