#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p20(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P20",
        "cleanup",
        "S1_P20_CLEANUP_V1",
        "CLEANUP_OK",
        10U
    };

    return descriptor;
}
