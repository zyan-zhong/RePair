#ifndef PCHSI_S1_STRICT_JSON_H
#define PCHSI_S1_STRICT_JSON_H

#include <stddef.h>

enum pchsi_json_status {
    PCHSI_JSON_OK = 0,
    PCHSI_JSON_INVALID_UTF8,
    PCHSI_JSON_INVALID_SYNTAX,
    PCHSI_JSON_DUPLICATE_MEMBER,
    PCHSI_JSON_NUMBER_OUT_OF_RANGE,
    PCHSI_JSON_NUMBER_NOT_INTEGER,
    PCHSI_JSON_NEGATIVE_ZERO,
    PCHSI_JSON_DEPTH_EXCEEDED,
    PCHSI_JSON_TRAILING_DATA,
    PCHSI_JSON_ALLOCATION_FAILED
};

struct pchsi_json_error {
    enum pchsi_json_status status;
    size_t offset;
};

enum pchsi_json_status pchsi_json_validate_strict(
    const unsigned char *data,
    size_t size,
    struct pchsi_json_error *error
);

const char *pchsi_json_status_name(
    enum pchsi_json_status status
);

#endif
