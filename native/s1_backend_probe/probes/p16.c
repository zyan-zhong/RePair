#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p16(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P16",
        "oversize_evidence",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
