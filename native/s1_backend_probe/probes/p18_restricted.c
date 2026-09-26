#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p18_restricted(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P18_RESTRICTED",
        "landlock_restricted",
        "S1_P18_LANDLOCK_ATTRIBUTION_V1",
        "RESTRICTION_ENFORCED",
        10U
    };

    return descriptor;
}
