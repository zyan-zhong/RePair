#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p10(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P10",
        "proc_escape",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
