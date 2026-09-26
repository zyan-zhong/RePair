#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p09(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P09",
        "mount_operation",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
