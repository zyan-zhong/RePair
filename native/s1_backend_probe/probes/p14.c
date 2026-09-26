#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p14(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P14",
        "evidence_clobber",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
