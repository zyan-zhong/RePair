#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p15_control(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P15_CONTROL",
        "rlimit_control",
        "S1_P15_RLIMIT_ATTRIBUTION_V1",
        "CONTROL_OK",
        10U
    };

    return descriptor;
}
