#ifndef PCHSI_S1_PATH_CONTRACT_H
#define PCHSI_S1_PATH_CONTRACT_H

#include <stddef.h>

#define PCHSI_EVIDENCE_PATH_MAX_BYTES 512U
#define PCHSI_EVIDENCE_SEGMENT_MAX_BYTES 128U
#define PCHSI_EVIDENCE_SEGMENT_MAX_COUNT 2U

enum pchsi_path_status {
    PCHSI_PATH_OK = 0,
    PCHSI_PATH_EMPTY,
    PCHSI_PATH_TOO_LONG,
    PCHSI_PATH_NON_ASCII,
    PCHSI_PATH_ABSOLUTE,
    PCHSI_PATH_TOO_MANY_SEGMENTS,
    PCHSI_PATH_EMPTY_SEGMENT,
    PCHSI_PATH_SEGMENT_TOO_LONG,
    PCHSI_PATH_INVALID_INITIAL_BYTE,
    PCHSI_PATH_INVALID_SEGMENT_BYTE
};

struct pchsi_path_part {
    size_t offset;
    size_t size;
};

struct pchsi_path_parts {
    size_t count;
    struct pchsi_path_part parts[PCHSI_EVIDENCE_SEGMENT_MAX_COUNT];
};

enum pchsi_path_status pchsi_validate_evidence_path(
    const unsigned char *path,
    size_t path_size,
    struct pchsi_path_parts *parts
);

const char *pchsi_path_status_name(enum pchsi_path_status status);

#endif
