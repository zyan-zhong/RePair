#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p06(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P06",
        "network_socket",
        "S1_PRODUCTION_V1",
        "DENIED",
        10U
    };

    return descriptor;
}
