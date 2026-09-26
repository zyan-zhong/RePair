#ifndef PCHSI_S1_SHA256_H
#define PCHSI_S1_SHA256_H

#include <stddef.h>
#include <stdint.h>

#define PCHSI_SHA256_DIGEST_BYTES 32U
#define PCHSI_SHA256_BLOCK_BYTES 64U

struct pchsi_sha256_context {
    uint32_t state[8];
    uint64_t bit_count;
    unsigned char buffer[PCHSI_SHA256_BLOCK_BYTES];
    size_t buffer_size;
};

void pchsi_sha256_init(
    struct pchsi_sha256_context *context
);

void pchsi_sha256_update(
    struct pchsi_sha256_context *context,
    const unsigned char *data,
    size_t size
);

void pchsi_sha256_final(
    struct pchsi_sha256_context *context,
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES]
);

int pchsi_sha256_file_descriptor(
    int file_descriptor,
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES]
);

#endif
