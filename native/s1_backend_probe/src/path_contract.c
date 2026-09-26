#include "pchsi_s1/path_contract.h"

static int pchsi_is_ascii_alnum(unsigned char byte)
{
    return (
        (byte >= (unsigned char)'0' && byte <= (unsigned char)'9')
        || (byte >= (unsigned char)'A' && byte <= (unsigned char)'Z')
        || (byte >= (unsigned char)'a' && byte <= (unsigned char)'z')
    );
}

static int pchsi_is_segment_tail_byte(unsigned char byte)
{
    return (
        pchsi_is_ascii_alnum(byte)
        || byte == (unsigned char)'.'
        || byte == (unsigned char)'_'
        || byte == (unsigned char)'-'
    );
}

enum pchsi_path_status pchsi_validate_evidence_path(
    const unsigned char *path,
    size_t path_size,
    struct pchsi_path_parts *parts
)
{
    size_t index = 0U;
    size_t segment_start = 0U;
    size_t segment_count = 0U;

    if (parts != NULL) {
        parts->count = 0U;
    }

    if (path == NULL || path_size == 0U) {
        return PCHSI_PATH_EMPTY;
    }

    if (path_size > PCHSI_EVIDENCE_PATH_MAX_BYTES) {
        return PCHSI_PATH_TOO_LONG;
    }

    if (path[0] == (unsigned char)'/') {
        return PCHSI_PATH_ABSOLUTE;
    }

    for (index = 0U; index <= path_size; index += 1U) {
        int is_end = index == path_size;
        int is_separator = !is_end && path[index] == (unsigned char)'/';

        if (!is_end && path[index] >= 0x80U) {
            return PCHSI_PATH_NON_ASCII;
        }

        if (is_end || is_separator) {
            size_t segment_size = index - segment_start;

            if (segment_size == 0U) {
                return PCHSI_PATH_EMPTY_SEGMENT;
            }

            if (segment_count >= PCHSI_EVIDENCE_SEGMENT_MAX_COUNT) {
                return PCHSI_PATH_TOO_MANY_SEGMENTS;
            }

            if (segment_size > PCHSI_EVIDENCE_SEGMENT_MAX_BYTES) {
                return PCHSI_PATH_SEGMENT_TOO_LONG;
            }

            if (!pchsi_is_ascii_alnum(path[segment_start])) {
                return PCHSI_PATH_INVALID_INITIAL_BYTE;
            }

            if (parts != NULL) {
                parts->parts[segment_count].offset = segment_start;
                parts->parts[segment_count].size = segment_size;
            }

            segment_count += 1U;
            segment_start = index + 1U;
            continue;
        }

        if (
            index > segment_start
            && !pchsi_is_segment_tail_byte(path[index])
        ) {
            return PCHSI_PATH_INVALID_SEGMENT_BYTE;
        }
    }

    if (parts != NULL) {
        parts->count = segment_count;
    }

    return PCHSI_PATH_OK;
}

const char *pchsi_path_status_name(enum pchsi_path_status status)
{
    switch (status) {
        case PCHSI_PATH_OK:
            return "OK";
        case PCHSI_PATH_EMPTY:
            return "EMPTY";
        case PCHSI_PATH_TOO_LONG:
            return "TOO_LONG";
        case PCHSI_PATH_NON_ASCII:
            return "NON_ASCII";
        case PCHSI_PATH_ABSOLUTE:
            return "ABSOLUTE";
        case PCHSI_PATH_TOO_MANY_SEGMENTS:
            return "TOO_MANY_SEGMENTS";
        case PCHSI_PATH_EMPTY_SEGMENT:
            return "EMPTY_SEGMENT";
        case PCHSI_PATH_SEGMENT_TOO_LONG:
            return "SEGMENT_TOO_LONG";
        case PCHSI_PATH_INVALID_INITIAL_BYTE:
            return "INVALID_INITIAL_BYTE";
        case PCHSI_PATH_INVALID_SEGMENT_BYTE:
            return "INVALID_SEGMENT_BYTE";
    }

    return "UNKNOWN";
}
