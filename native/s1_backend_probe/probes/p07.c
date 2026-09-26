#include "pchsi_s1/probe_protocol.h"

struct pchsi_probe_payload_descriptor
pchsi_probe_payload_p07(void)
{
    static const struct pchsi_probe_payload_descriptor descriptor = {
        "P07",
        "syscall_case",
        "S1_P7_SYSCALL_CASE_V1",
        "KILLED",
        2U
    };

    return descriptor;
}
