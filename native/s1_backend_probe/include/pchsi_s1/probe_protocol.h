#ifndef PCHSI_S1_PROBE_PROTOCOL_H
#define PCHSI_S1_PROBE_PROTOCOL_H

#define PCHSI_S1_PROBE_MANIFEST_SCHEMA_VERSION 1U
#define PCHSI_S1_PROBE_PAYLOAD_EXECUTION_STATUS "NOT_APPROVED"

struct pchsi_probe_payload_descriptor {
    const char *probe_id;
    const char *payload_id;
    const char *profile_id;
    const char *expected_normalized_outcome;
    unsigned int timeout_seconds;
};

#endif
