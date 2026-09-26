#include "pchsi_s1/security_state.h"

#include <ctype.h>
#include <limits.h>
#include <string.h>

struct pchsi_status_fields {
    int cap_inh;
    int cap_prm;
    int cap_eff;
    int cap_bnd;
    int cap_amb;
    int no_new_privs;
};

static int pchsi_hex_digit(unsigned char value)
{
    if (value >= (unsigned char)'0' && value <= (unsigned char)'9') {
        return (int)(value - (unsigned char)'0');
    }
    if (value >= (unsigned char)'a' && value <= (unsigned char)'f') {
        return (int)(value - (unsigned char)'a') + 10;
    }
    if (value >= (unsigned char)'A' && value <= (unsigned char)'F') {
        return (int)(value - (unsigned char)'A') + 10;
    }
    return -1;
}

static int pchsi_parse_hex_u64(
    const char *text,
    size_t size,
    uint64_t *result
)
{
    size_t index = 0U;
    uint64_t value = UINT64_C(0);

    if (size == 0U || size > 16U || result == NULL) {
        return 0;
    }

    for (index = 0U; index < size; index += 1U) {
        int digit = pchsi_hex_digit((unsigned char)text[index]);

        if (digit < 0) {
            return 0;
        }

        value = (value << 4U) | (uint64_t)(unsigned int)digit;
    }

    *result = value;
    return 1;
}

static int pchsi_parse_decimal_flag(
    const char *text,
    size_t size,
    int *result
)
{
    if (result == NULL || size != 1U) {
        return 0;
    }
    if (text[0] == '0') {
        *result = 0;
        return 1;
    }
    if (text[0] == '1') {
        *result = 1;
        return 1;
    }
    return 0;
}

static int pchsi_line_value(
    const char *line,
    size_t line_size,
    const char *name,
    const char **value,
    size_t *value_size
)
{
    size_t name_size = strlen(name);
    size_t offset = 0U;
    size_t end = line_size;

    if (
        line_size < name_size + 1U
        || memcmp(line, name, name_size) != 0
        || line[name_size] != ':'
    ) {
        return 0;
    }

    offset = name_size + 1U;

    while (
        offset < line_size
        && (line[offset] == ' ' || line[offset] == '\t')
    ) {
        offset += 1U;
    }

    while (
        end > offset
        && (line[end - 1U] == ' ' || line[end - 1U] == '\t')
    ) {
        end -= 1U;
    }

    *value = line + offset;
    *value_size = end - offset;
    return 1;
}

enum pchsi_security_state_status pchsi_parse_proc_status(
    const char *text,
    size_t size,
    struct pchsi_security_state *state
)
{
    size_t offset = 0U;
    struct pchsi_status_fields seen = {0, 0, 0, 0, 0, 0};
    struct pchsi_security_state parsed = {0, 0, 0, 0, 0, 0};

    if (text == NULL || state == NULL) {
        return PCHSI_SECURITY_STATE_INVALID_ARGUMENT;
    }

    while (offset < size) {
        size_t end = offset;
        const char *value = NULL;
        size_t value_size = 0U;
        uint64_t capability = UINT64_C(0);

        while (end < size && text[end] != '\n') {
            end += 1U;
        }

        if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "CapInh",
                &value,
                &value_size
            )
        ) {
            if (!pchsi_parse_hex_u64(value, value_size, &capability)) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            parsed.cap_inheritable = capability;
            seen.cap_inh = 1;
        } else if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "CapPrm",
                &value,
                &value_size
            )
        ) {
            if (!pchsi_parse_hex_u64(value, value_size, &capability)) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            parsed.cap_permitted = capability;
            seen.cap_prm = 1;
        } else if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "CapEff",
                &value,
                &value_size
            )
        ) {
            if (!pchsi_parse_hex_u64(value, value_size, &capability)) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            parsed.cap_effective = capability;
            seen.cap_eff = 1;
        } else if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "CapBnd",
                &value,
                &value_size
            )
        ) {
            if (!pchsi_parse_hex_u64(value, value_size, &capability)) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            parsed.cap_bounding = capability;
            seen.cap_bnd = 1;
        } else if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "CapAmb",
                &value,
                &value_size
            )
        ) {
            if (!pchsi_parse_hex_u64(value, value_size, &capability)) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            parsed.cap_ambient = capability;
            seen.cap_amb = 1;
        } else if (
            pchsi_line_value(
                text + offset,
                end - offset,
                "NoNewPrivs",
                &value,
                &value_size
            )
        ) {
            if (
                !pchsi_parse_decimal_flag(
                    value,
                    value_size,
                    &parsed.no_new_privs
                )
            ) {
                return PCHSI_SECURITY_STATE_MALFORMED_STATUS;
            }
            seen.no_new_privs = 1;
        }

        offset = end < size ? end + 1U : end;
    }

    if (
        !seen.cap_inh
        || !seen.cap_prm
        || !seen.cap_eff
        || !seen.cap_bnd
        || !seen.cap_amb
        || !seen.no_new_privs
    ) {
        return PCHSI_SECURITY_STATE_MISSING_FIELD;
    }

    *state = parsed;
    return PCHSI_SECURITY_STATE_OK;
}

enum pchsi_security_state_status pchsi_validate_collector_security_state(
    const struct pchsi_security_state *state
)
{
    if (state == NULL) {
        return PCHSI_SECURITY_STATE_INVALID_ARGUMENT;
    }

    if (
        state->cap_inheritable != UINT64_C(0)
        || state->cap_permitted != UINT64_C(0)
        || state->cap_effective != UINT64_C(0)
        || state->cap_bounding != UINT64_C(0)
        || state->cap_ambient != UINT64_C(0)
    ) {
        return PCHSI_SECURITY_STATE_CAPABILITY_LEAK;
    }

    if (state->no_new_privs != 1) {
        return PCHSI_SECURITY_STATE_NO_NEW_PRIVS_MISSING;
    }

    return PCHSI_SECURITY_STATE_OK;
}

static int pchsi_option_present(
    const char *options,
    const char *required
)
{
    size_t required_size = strlen(required);
    const char *cursor = options;

    while (*cursor != '\0') {
        const char *end = strchr(cursor, ',');
        size_t size = end == NULL ? strlen(cursor) : (size_t)(end - cursor);

        if (size == required_size && memcmp(cursor, required, size) == 0) {
            return 1;
        }

        if (end == NULL) {
            break;
        }
        cursor = end + 1;
    }

    return 0;
}

enum pchsi_security_state_status pchsi_validate_procfs_mount_options(
    const char *options
)
{
    if (options == NULL) {
        return PCHSI_SECURITY_STATE_INVALID_ARGUMENT;
    }

    if (
        !pchsi_option_present(options, "hidepid=4")
        || !pchsi_option_present(options, "subset=pid")
    ) {
        return PCHSI_SECURITY_STATE_PROCFS_OPTIONS_INVALID;
    }

    return PCHSI_SECURITY_STATE_OK;
}

enum pchsi_security_state_status pchsi_validate_identity_map(
    const struct pchsi_identity_map *mapping
)
{
    if (mapping == NULL) {
        return PCHSI_SECURITY_STATE_INVALID_ARGUMENT;
    }

    if (
        mapping->range_length != 1U
        || mapping->trusted_inside_id == mapping->collector_inside_id
        || mapping->trusted_outside_id == mapping->collector_outside_id
    ) {
        return PCHSI_SECURITY_STATE_ID_MAP_INVALID;
    }

    return PCHSI_SECURITY_STATE_OK;
}

const char *pchsi_security_state_status_name(
    enum pchsi_security_state_status status
)
{
    switch (status) {
        case PCHSI_SECURITY_STATE_OK:
            return "PCHSI_SECURITY_STATE_OK";
        case PCHSI_SECURITY_STATE_INVALID_ARGUMENT:
            return "PCHSI_SECURITY_STATE_INVALID_ARGUMENT";
        case PCHSI_SECURITY_STATE_MALFORMED_STATUS:
            return "PCHSI_SECURITY_STATE_MALFORMED_STATUS";
        case PCHSI_SECURITY_STATE_MISSING_FIELD:
            return "PCHSI_SECURITY_STATE_MISSING_FIELD";
        case PCHSI_SECURITY_STATE_CAPABILITY_LEAK:
            return "PCHSI_SECURITY_STATE_CAPABILITY_LEAK";
        case PCHSI_SECURITY_STATE_NO_NEW_PRIVS_MISSING:
            return "PCHSI_SECURITY_STATE_NO_NEW_PRIVS_MISSING";
        case PCHSI_SECURITY_STATE_PROCFS_OPTIONS_INVALID:
            return "PCHSI_SECURITY_STATE_PROCFS_OPTIONS_INVALID";
        case PCHSI_SECURITY_STATE_ID_MAP_INVALID:
            return "PCHSI_SECURITY_STATE_ID_MAP_INVALID";
    }

    return "PCHSI_SECURITY_STATE_UNKNOWN";
}
