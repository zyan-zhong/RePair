#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p03(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P03",
        "old_root_access",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
