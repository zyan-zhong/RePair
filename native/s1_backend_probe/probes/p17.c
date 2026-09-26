#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p17(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P17",
        "hardlink_evidence",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
