#include "pchsi_s1/strict_json.h"

#include <stdio.h>
#include <stdlib.h>

static unsigned char *read_all_stdin(size_t *size_out)
{
    unsigned char *buffer = NULL;
    size_t size = 0U;
    size_t capacity = 0U;

    for (;;) {
        int byte = fgetc(stdin);

        if (byte == EOF) {
            break;
        }

        if (size == capacity) {
            size_t new_capacity = (
                capacity == 0U
                ? 256U
                : capacity * 2U
            );
            unsigned char *replacement = (
                (unsigned char *)realloc(
                    buffer,
                    new_capacity
                )
            );

            if (replacement == NULL) {
                free(buffer);
                return NULL;
            }

            buffer = replacement;
            capacity = new_capacity;
        }

        buffer[size] = (unsigned char)byte;
        size += 1U;
    }

    *size_out = size;
    return buffer;
}

int main(void)
{
    unsigned char *payload;
    size_t payload_size = 0U;
    struct pchsi_json_error error = {
        PCHSI_JSON_OK,
        0U,
    };
    enum pchsi_json_status status;

    payload = read_all_stdin(&payload_size);

    if (payload == NULL && payload_size != 0U) {
        (void)fprintf(stderr, "allocation failed\n");
        return 2;
    }

    status = pchsi_json_validate_strict(
        payload,
        payload_size,
        &error
    );

    (void)printf(
        "%s %zu\n",
        pchsi_json_status_name(status),
        error.offset
    );

    free(payload);

    return (
        status == PCHSI_JSON_OK
        ? 0
        : 1
    );
}
