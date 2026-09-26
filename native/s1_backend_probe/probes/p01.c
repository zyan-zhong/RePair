#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p01(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P01",
        "observer",
        "S1_PRODUCTION_V1",
        "OBSERVED",
        10U
    };

    return descriptor;
}
