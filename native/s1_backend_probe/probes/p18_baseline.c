#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p18_baseline(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P18_BASELINE",
        "landlock_baseline",
        "S1_P18_LANDLOCK_ATTRIBUTION_V1",
        "BASELINE_OK",
        10U
    };

    return descriptor;
}
