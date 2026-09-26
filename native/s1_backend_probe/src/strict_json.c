#include "pchsi_s1/strict_json.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define PCHSI_JSON_MAX_DEPTH 64U

struct pchsi_json_parser {
    const unsigned char *data;
    size_t size;
    size_t position;
    size_t depth;
    struct pchsi_json_error *error;
};

struct pchsi_json_key {
    unsigned char *data;
    size_t size;
};

static enum pchsi_json_status pchsi_set_error(
    struct pchsi_json_parser *parser,
    enum pchsi_json_status status,
    size_t offset
)
{
    if (parser->error != NULL) {
        parser->error->status = status;
        parser->error->offset = offset;
    }

    return status;
}

static int pchsi_is_json_whitespace(unsigned char byte)
{
    return (
        byte == (unsigned char)' '
        || byte == (unsigned char)'\t'
        || byte == (unsigned char)'\n'
        || byte == (unsigned char)'\r'
    );
}

static void pchsi_skip_whitespace(struct pchsi_json_parser *parser)
{
    while (
        parser->position < parser->size
        && pchsi_is_json_whitespace(
            parser->data[parser->position]
        )
    ) {
        parser->position += 1U;
    }
}

static int pchsi_is_continuation(unsigned char byte)
{
    return (byte & 0xC0U) == 0x80U;
}

static enum pchsi_json_status pchsi_validate_utf8(
    const unsigned char *data,
    size_t size,
    struct pchsi_json_error *error
)
{
    size_t index = 0U;

    while (index < size) {
        unsigned char first = data[index];

        if (first <= 0x7FU) {
            index += 1U;
            continue;
        }

        if (first >= 0xC2U && first <= 0xDFU) {
            if (
                index + 1U >= size
                || !pchsi_is_continuation(data[index + 1U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 2U;
            continue;
        }

        if (first == 0xE0U) {
            if (
                index + 2U >= size
                || data[index + 1U] < 0xA0U
                || data[index + 1U] > 0xBFU
                || !pchsi_is_continuation(data[index + 2U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 3U;
            continue;
        }

        if (
            (first >= 0xE1U && first <= 0xECU)
            || (first >= 0xEEU && first <= 0xEFU)
        ) {
            if (
                index + 2U >= size
                || !pchsi_is_continuation(data[index + 1U])
                || !pchsi_is_continuation(data[index + 2U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 3U;
            continue;
        }

        if (first == 0xEDU) {
            if (
                index + 2U >= size
                || data[index + 1U] < 0x80U
                || data[index + 1U] > 0x9FU
                || !pchsi_is_continuation(data[index + 2U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 3U;
            continue;
        }

        if (first == 0xF0U) {
            if (
                index + 3U >= size
                || data[index + 1U] < 0x90U
                || data[index + 1U] > 0xBFU
                || !pchsi_is_continuation(data[index + 2U])
                || !pchsi_is_continuation(data[index + 3U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 4U;
            continue;
        }

        if (first >= 0xF1U && first <= 0xF3U) {
            if (
                index + 3U >= size
                || !pchsi_is_continuation(data[index + 1U])
                || !pchsi_is_continuation(data[index + 2U])
                || !pchsi_is_continuation(data[index + 3U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 4U;
            continue;
        }

        if (first == 0xF4U) {
            if (
                index + 3U >= size
                || data[index + 1U] < 0x80U
                || data[index + 1U] > 0x8FU
                || !pchsi_is_continuation(data[index + 2U])
                || !pchsi_is_continuation(data[index + 3U])
            ) {
                if (error != NULL) {
                    error->status = PCHSI_JSON_INVALID_UTF8;
                    error->offset = index;
                }
                return PCHSI_JSON_INVALID_UTF8;
            }

            index += 4U;
            continue;
        }

        if (error != NULL) {
            error->status = PCHSI_JSON_INVALID_UTF8;
            error->offset = index;
        }
        return PCHSI_JSON_INVALID_UTF8;
    }

    return PCHSI_JSON_OK;
}

static int pchsi_hex_value(unsigned char byte)
{
    if (byte >= (unsigned char)'0' && byte <= (unsigned char)'9') {
        return (int)(byte - (unsigned char)'0');
    }

    if (byte >= (unsigned char)'a' && byte <= (unsigned char)'f') {
        return 10 + (int)(byte - (unsigned char)'a');
    }

    if (byte >= (unsigned char)'A' && byte <= (unsigned char)'F') {
        return 10 + (int)(byte - (unsigned char)'A');
    }

    return -1;
}

static int pchsi_read_hex4(
    struct pchsi_json_parser *parser,
    uint32_t *value
)
{
    uint32_t result = 0U;
    size_t index;

    if (parser->position + 4U > parser->size) {
        return 0;
    }

    for (index = 0U; index < 4U; index += 1U) {
        int digit = pchsi_hex_value(
            parser->data[parser->position + index]
        );

        if (digit < 0) {
            return 0;
        }

        result = (result << 4U) | (uint32_t)digit;
    }

    parser->position += 4U;
    *value = result;
    return 1;
}

static size_t pchsi_utf8_encoded_size(uint32_t codepoint)
{
    if (codepoint <= 0x7FU) {
        return 1U;
    }

    if (codepoint <= 0x7FFU) {
        return 2U;
    }

    if (codepoint <= 0xFFFFU) {
        return 3U;
    }

    return 4U;
}

static void pchsi_append_codepoint(
    unsigned char *buffer,
    size_t *length,
    uint32_t codepoint
)
{
    if (codepoint <= 0x7FU) {
        buffer[*length] = (unsigned char)codepoint;
        *length += 1U;
        return;
    }

    if (codepoint <= 0x7FFU) {
        buffer[*length] = (unsigned char)(
            0xC0U | (codepoint >> 6U)
        );
        buffer[*length + 1U] = (unsigned char)(
            0x80U | (codepoint & 0x3FU)
        );
        *length += 2U;
        return;
    }

    if (codepoint <= 0xFFFFU) {
        buffer[*length] = (unsigned char)(
            0xE0U | (codepoint >> 12U)
        );
        buffer[*length + 1U] = (unsigned char)(
            0x80U | ((codepoint >> 6U) & 0x3FU)
        );
        buffer[*length + 2U] = (unsigned char)(
            0x80U | (codepoint & 0x3FU)
        );
        *length += 3U;
        return;
    }

    buffer[*length] = (unsigned char)(
        0xF0U | (codepoint >> 18U)
    );
    buffer[*length + 1U] = (unsigned char)(
        0x80U | ((codepoint >> 12U) & 0x3FU)
    );
    buffer[*length + 2U] = (unsigned char)(
        0x80U | ((codepoint >> 6U) & 0x3FU)
    );
    buffer[*length + 3U] = (unsigned char)(
        0x80U | (codepoint & 0x3FU)
    );
    *length += 4U;
}

static enum pchsi_json_status pchsi_parse_string(
    struct pchsi_json_parser *parser,
    unsigned char **decoded,
    size_t *decoded_size
)
{
    unsigned char *buffer = NULL;
    size_t length = 0U;
    size_t capacity = 0U;

    if (
        parser->position >= parser->size
        || parser->data[parser->position] != (unsigned char)'"'
    ) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_INVALID_SYNTAX,
            parser->position
        );
    }

    parser->position += 1U;

    if (decoded != NULL) {
        capacity = parser->size - parser->position + 1U;
        buffer = (unsigned char *)malloc(capacity);

        if (buffer == NULL) {
            return pchsi_set_error(
                parser,
                PCHSI_JSON_ALLOCATION_FAILED,
                parser->position
            );
        }
    }

    while (parser->position < parser->size) {
        unsigned char byte = parser->data[parser->position];

        if (byte == (unsigned char)'"') {
            parser->position += 1U;

            if (decoded != NULL) {
                *decoded = buffer;
                *decoded_size = length;
            }

            return PCHSI_JSON_OK;
        }

        if (byte < 0x20U) {
            free(buffer);
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        if (byte != (unsigned char)'\\') {
            if (decoded != NULL) {
                buffer[length] = byte;
                length += 1U;
            }
            parser->position += 1U;
            continue;
        }

        parser->position += 1U;

        if (parser->position >= parser->size) {
            free(buffer);
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        byte = parser->data[parser->position];
        parser->position += 1U;

        if (
            byte == (unsigned char)'"'
            || byte == (unsigned char)'\\'
            || byte == (unsigned char)'/'
        ) {
            if (decoded != NULL) {
                buffer[length] = byte;
                length += 1U;
            }
            continue;
        }

        if (
            byte == (unsigned char)'b'
            || byte == (unsigned char)'f'
            || byte == (unsigned char)'n'
            || byte == (unsigned char)'r'
            || byte == (unsigned char)'t'
        ) {
            unsigned char translated = 0U;

            switch (byte) {
                case (unsigned char)'b':
                    translated = 0x08U;
                    break;
                case (unsigned char)'f':
                    translated = 0x0CU;
                    break;
                case (unsigned char)'n':
                    translated = 0x0AU;
                    break;
                case (unsigned char)'r':
                    translated = 0x0DU;
                    break;
                case (unsigned char)'t':
                    translated = 0x09U;
                    break;
                default:
                    translated = 0U;
                    break;
            }

            if (decoded != NULL) {
                buffer[length] = translated;
                length += 1U;
            }
            continue;
        }

        if (byte == (unsigned char)'u') {
            uint32_t codepoint = 0U;

            if (!pchsi_read_hex4(parser, &codepoint)) {
                free(buffer);
                return pchsi_set_error(
                    parser,
                    PCHSI_JSON_INVALID_SYNTAX,
                    parser->position
                );
            }

            if (codepoint >= 0xD800U && codepoint <= 0xDBFFU) {
                uint32_t low_surrogate = 0U;

                if (
                    parser->position + 6U > parser->size
                    || parser->data[parser->position]
                        != (unsigned char)'\\'
                    || parser->data[parser->position + 1U]
                        != (unsigned char)'u'
                ) {
                    free(buffer);
                    return pchsi_set_error(
                        parser,
                        PCHSI_JSON_INVALID_SYNTAX,
                        parser->position
                    );
                }

                parser->position += 2U;

                if (
                    !pchsi_read_hex4(parser, &low_surrogate)
                    || low_surrogate < 0xDC00U
                    || low_surrogate > 0xDFFFU
                ) {
                    free(buffer);
                    return pchsi_set_error(
                        parser,
                        PCHSI_JSON_INVALID_SYNTAX,
                        parser->position
                    );
                }

                codepoint = (
                    0x10000U
                    + ((codepoint - 0xD800U) << 10U)
                    + (low_surrogate - 0xDC00U)
                );
            } else if (
                codepoint >= 0xDC00U
                && codepoint <= 0xDFFFU
            ) {
                free(buffer);
                return pchsi_set_error(
                    parser,
                    PCHSI_JSON_INVALID_SYNTAX,
                    parser->position
                );
            }

            if (decoded != NULL) {
                size_t encoded_size = pchsi_utf8_encoded_size(
                    codepoint
                );

                if (length + encoded_size > capacity) {
                    free(buffer);
                    return pchsi_set_error(
                        parser,
                        PCHSI_JSON_ALLOCATION_FAILED,
                        parser->position
                    );
                }

                pchsi_append_codepoint(
                    buffer,
                    &length,
                    codepoint
                );
            }
            continue;
        }

        free(buffer);
        return pchsi_set_error(
            parser,
            PCHSI_JSON_INVALID_SYNTAX,
            parser->position - 1U
        );
    }

    free(buffer);
    return pchsi_set_error(
        parser,
        PCHSI_JSON_INVALID_SYNTAX,
        parser->position
    );
}

static enum pchsi_json_status pchsi_parse_value(
    struct pchsi_json_parser *parser
);

static void pchsi_free_keys(
    struct pchsi_json_key *keys,
    size_t count
)
{
    size_t index;

    for (index = 0U; index < count; index += 1U) {
        free(keys[index].data);
    }

    free(keys);
}

static enum pchsi_json_status pchsi_parse_object(
    struct pchsi_json_parser *parser
)
{
    struct pchsi_json_key *keys = NULL;
    size_t key_count = 0U;
    size_t key_capacity = 0U;
    enum pchsi_json_status status = PCHSI_JSON_OK;

    if (parser->depth >= PCHSI_JSON_MAX_DEPTH) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_DEPTH_EXCEEDED,
            parser->position
        );
    }

    parser->depth += 1U;
    parser->position += 1U;
    pchsi_skip_whitespace(parser);

    if (
        parser->position < parser->size
        && parser->data[parser->position] == (unsigned char)'}'
    ) {
        parser->position += 1U;
        parser->depth -= 1U;
        return PCHSI_JSON_OK;
    }

    while (parser->position < parser->size) {
        unsigned char *key_data = NULL;
        size_t key_size = 0U;
        size_t index;

        status = pchsi_parse_string(
            parser,
            &key_data,
            &key_size
        );

        if (status != PCHSI_JSON_OK) {
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return status;
        }

        for (index = 0U; index < key_count; index += 1U) {
            if (
                keys[index].size == key_size
                && memcmp(
                    keys[index].data,
                    key_data,
                    key_size
                ) == 0
            ) {
                free(key_data);
                pchsi_free_keys(keys, key_count);
                parser->depth -= 1U;
                return pchsi_set_error(
                    parser,
                    PCHSI_JSON_DUPLICATE_MEMBER,
                    parser->position
                );
            }
        }

        if (key_count == key_capacity) {
            size_t new_capacity = (
                key_capacity == 0U
                ? 4U
                : key_capacity * 2U
            );
            struct pchsi_json_key *replacement = (
                (struct pchsi_json_key *)realloc(
                    keys,
                    new_capacity * sizeof(*replacement)
                )
            );

            if (replacement == NULL) {
                free(key_data);
                pchsi_free_keys(keys, key_count);
                parser->depth -= 1U;
                return pchsi_set_error(
                    parser,
                    PCHSI_JSON_ALLOCATION_FAILED,
                    parser->position
                );
            }

            keys = replacement;
            key_capacity = new_capacity;
        }

        keys[key_count].data = key_data;
        keys[key_count].size = key_size;
        key_count += 1U;

        pchsi_skip_whitespace(parser);

        if (
            parser->position >= parser->size
            || parser->data[parser->position]
                != (unsigned char)':'
        ) {
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        parser->position += 1U;
        pchsi_skip_whitespace(parser);
        status = pchsi_parse_value(parser);

        if (status != PCHSI_JSON_OK) {
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return status;
        }

        pchsi_skip_whitespace(parser);

        if (parser->position >= parser->size) {
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        if (
            parser->data[parser->position]
            == (unsigned char)'}'
        ) {
            parser->position += 1U;
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return PCHSI_JSON_OK;
        }

        if (
            parser->data[parser->position]
            != (unsigned char)','
        ) {
            pchsi_free_keys(keys, key_count);
            parser->depth -= 1U;
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        parser->position += 1U;
        pchsi_skip_whitespace(parser);
    }

    pchsi_free_keys(keys, key_count);
    parser->depth -= 1U;
    return pchsi_set_error(
        parser,
        PCHSI_JSON_INVALID_SYNTAX,
        parser->position
    );
}

static enum pchsi_json_status pchsi_parse_array(
    struct pchsi_json_parser *parser
)
{
    enum pchsi_json_status status;

    if (parser->depth >= PCHSI_JSON_MAX_DEPTH) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_DEPTH_EXCEEDED,
            parser->position
        );
    }

    parser->depth += 1U;
    parser->position += 1U;
    pchsi_skip_whitespace(parser);

    if (
        parser->position < parser->size
        && parser->data[parser->position] == (unsigned char)']'
    ) {
        parser->position += 1U;
        parser->depth -= 1U;
        return PCHSI_JSON_OK;
    }

    while (parser->position < parser->size) {
        status = pchsi_parse_value(parser);

        if (status != PCHSI_JSON_OK) {
            parser->depth -= 1U;
            return status;
        }

        pchsi_skip_whitespace(parser);

        if (parser->position >= parser->size) {
            parser->depth -= 1U;
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        if (
            parser->data[parser->position]
            == (unsigned char)']'
        ) {
            parser->position += 1U;
            parser->depth -= 1U;
            return PCHSI_JSON_OK;
        }

        if (
            parser->data[parser->position]
            != (unsigned char)','
        ) {
            parser->depth -= 1U;
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        parser->position += 1U;
        pchsi_skip_whitespace(parser);
    }

    parser->depth -= 1U;
    return pchsi_set_error(
        parser,
        PCHSI_JSON_INVALID_SYNTAX,
        parser->position
    );
}

static int pchsi_matches_literal(
    struct pchsi_json_parser *parser,
    const char *literal,
    size_t literal_size
)
{
    if (
        parser->position + literal_size > parser->size
        || memcmp(
            parser->data + parser->position,
            literal,
            literal_size
        ) != 0
    ) {
        return 0;
    }

    parser->position += literal_size;
    return 1;
}

static enum pchsi_json_status pchsi_parse_number(
    struct pchsi_json_parser *parser
)
{
    int negative = 0;
    uint64_t magnitude = 0U;
    uint64_t limit;
    size_t digit_start;

    if (
        parser->position < parser->size
        && parser->data[parser->position] == (unsigned char)'-'
    ) {
        negative = 1;
        parser->position += 1U;
    }

    if (
        parser->position >= parser->size
        || parser->data[parser->position] < (unsigned char)'0'
        || parser->data[parser->position] > (unsigned char)'9'
    ) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_INVALID_SYNTAX,
            parser->position
        );
    }

    digit_start = parser->position;

    if (parser->data[parser->position] == (unsigned char)'0') {
        parser->position += 1U;

        if (
            parser->position < parser->size
            && parser->data[parser->position] >= (unsigned char)'0'
            && parser->data[parser->position] <= (unsigned char)'9'
        ) {
            return pchsi_set_error(
                parser,
                PCHSI_JSON_INVALID_SYNTAX,
                parser->position
            );
        }

        if (negative) {
            return pchsi_set_error(
                parser,
                PCHSI_JSON_NEGATIVE_ZERO,
                digit_start - 1U
            );
        }
    } else {
        limit = (
            negative
            ? UINT64_C(9223372036854775808)
            : UINT64_C(9223372036854775807)
        );

        while (
            parser->position < parser->size
            && parser->data[parser->position] >= (unsigned char)'0'
            && parser->data[parser->position] <= (unsigned char)'9'
        ) {
            uint64_t digit = (uint64_t)(
                parser->data[parser->position] - (unsigned char)'0'
            );

            if (
                magnitude > limit / UINT64_C(10)
                || (
                    magnitude == limit / UINT64_C(10)
                    && digit > limit % UINT64_C(10)
                )
            ) {
                return pchsi_set_error(
                    parser,
                    PCHSI_JSON_NUMBER_OUT_OF_RANGE,
                    parser->position
                );
            }

            magnitude = magnitude * UINT64_C(10) + digit;
            parser->position += 1U;
        }
    }

    if (
        parser->position < parser->size
        && (
            parser->data[parser->position] == (unsigned char)'.'
            || parser->data[parser->position] == (unsigned char)'e'
            || parser->data[parser->position] == (unsigned char)'E'
        )
    ) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_NUMBER_NOT_INTEGER,
            parser->position
        );
    }

    return PCHSI_JSON_OK;
}

static enum pchsi_json_status pchsi_parse_value(
    struct pchsi_json_parser *parser
)
{
    if (parser->position >= parser->size) {
        return pchsi_set_error(
            parser,
            PCHSI_JSON_INVALID_SYNTAX,
            parser->position
        );
    }

    switch (parser->data[parser->position]) {
        case (unsigned char)'{':
            return pchsi_parse_object(parser);
        case (unsigned char)'[':
            return pchsi_parse_array(parser);
        case (unsigned char)'"':
            return pchsi_parse_string(parser, NULL, NULL);
        case (unsigned char)'t':
            if (pchsi_matches_literal(parser, "true", 4U)) {
                return PCHSI_JSON_OK;
            }
            break;
        case (unsigned char)'f':
            if (pchsi_matches_literal(parser, "false", 5U)) {
                return PCHSI_JSON_OK;
            }
            break;
        case (unsigned char)'n':
            if (pchsi_matches_literal(parser, "null", 4U)) {
                return PCHSI_JSON_OK;
            }
            break;
        default:
            if (
                parser->data[parser->position] == (unsigned char)'-'
                || (
                    parser->data[parser->position] >= (unsigned char)'0'
                    && parser->data[parser->position] <= (unsigned char)'9'
                )
            ) {
                return pchsi_parse_number(parser);
            }
            break;
    }

    return pchsi_set_error(
        parser,
        PCHSI_JSON_INVALID_SYNTAX,
        parser->position
    );
}

enum pchsi_json_status pchsi_json_validate_strict(
    const unsigned char *data,
    size_t size,
    struct pchsi_json_error *error
)
{
    struct pchsi_json_parser parser;
    enum pchsi_json_status status;

    if (error != NULL) {
        error->status = PCHSI_JSON_OK;
        error->offset = 0U;
    }

    if (data == NULL && size != 0U) {
        if (error != NULL) {
            error->status = PCHSI_JSON_INVALID_SYNTAX;
            error->offset = 0U;
        }
        return PCHSI_JSON_INVALID_SYNTAX;
    }

    status = pchsi_validate_utf8(data, size, error);

    if (status != PCHSI_JSON_OK) {
        return status;
    }

    parser.data = data;
    parser.size = size;
    parser.position = 0U;
    parser.depth = 0U;
    parser.error = error;

    pchsi_skip_whitespace(&parser);
    status = pchsi_parse_value(&parser);

    if (status != PCHSI_JSON_OK) {
        return status;
    }

    pchsi_skip_whitespace(&parser);

    if (parser.position != parser.size) {
        return pchsi_set_error(
            &parser,
            PCHSI_JSON_TRAILING_DATA,
            parser.position
        );
    }

    return PCHSI_JSON_OK;
}

const char *pchsi_json_status_name(
    enum pchsi_json_status status
)
{
    switch (status) {
        case PCHSI_JSON_OK:
            return "PCHSI_JSON_OK";
        case PCHSI_JSON_INVALID_UTF8:
            return "PCHSI_JSON_INVALID_UTF8";
        case PCHSI_JSON_INVALID_SYNTAX:
            return "PCHSI_JSON_INVALID_SYNTAX";
        case PCHSI_JSON_DUPLICATE_MEMBER:
            return "PCHSI_JSON_DUPLICATE_MEMBER";
        case PCHSI_JSON_NUMBER_OUT_OF_RANGE:
            return "PCHSI_JSON_NUMBER_OUT_OF_RANGE";
        case PCHSI_JSON_NUMBER_NOT_INTEGER:
            return "PCHSI_JSON_NUMBER_NOT_INTEGER";
        case PCHSI_JSON_NEGATIVE_ZERO:
            return "PCHSI_JSON_NEGATIVE_ZERO";
        case PCHSI_JSON_DEPTH_EXCEEDED:
            return "PCHSI_JSON_DEPTH_EXCEEDED";
        case PCHSI_JSON_TRAILING_DATA:
            return "PCHSI_JSON_TRAILING_DATA";
        case PCHSI_JSON_ALLOCATION_FAILED:
            return "PCHSI_JSON_ALLOCATION_FAILED";
        default:
            return "PCHSI_JSON_UNKNOWN_STATUS";
    }
}
