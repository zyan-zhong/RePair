#include "pchsi_s1/sha256.h"

#include <errno.h>
#include <string.h>
#include <unistd.h>

static const uint32_t PCHSI_SHA256_CONSTANTS[64] = {
    UINT32_C(0x428a2f98), UINT32_C(0x71374491),
    UINT32_C(0xb5c0fbcf), UINT32_C(0xe9b5dba5),
    UINT32_C(0x3956c25b), UINT32_C(0x59f111f1),
    UINT32_C(0x923f82a4), UINT32_C(0xab1c5ed5),
    UINT32_C(0xd807aa98), UINT32_C(0x12835b01),
    UINT32_C(0x243185be), UINT32_C(0x550c7dc3),
    UINT32_C(0x72be5d74), UINT32_C(0x80deb1fe),
    UINT32_C(0x9bdc06a7), UINT32_C(0xc19bf174),
    UINT32_C(0xe49b69c1), UINT32_C(0xefbe4786),
    UINT32_C(0x0fc19dc6), UINT32_C(0x240ca1cc),
    UINT32_C(0x2de92c6f), UINT32_C(0x4a7484aa),
    UINT32_C(0x5cb0a9dc), UINT32_C(0x76f988da),
    UINT32_C(0x983e5152), UINT32_C(0xa831c66d),
    UINT32_C(0xb00327c8), UINT32_C(0xbf597fc7),
    UINT32_C(0xc6e00bf3), UINT32_C(0xd5a79147),
    UINT32_C(0x06ca6351), UINT32_C(0x14292967),
    UINT32_C(0x27b70a85), UINT32_C(0x2e1b2138),
    UINT32_C(0x4d2c6dfc), UINT32_C(0x53380d13),
    UINT32_C(0x650a7354), UINT32_C(0x766a0abb),
    UINT32_C(0x81c2c92e), UINT32_C(0x92722c85),
    UINT32_C(0xa2bfe8a1), UINT32_C(0xa81a664b),
    UINT32_C(0xc24b8b70), UINT32_C(0xc76c51a3),
    UINT32_C(0xd192e819), UINT32_C(0xd6990624),
    UINT32_C(0xf40e3585), UINT32_C(0x106aa070),
    UINT32_C(0x19a4c116), UINT32_C(0x1e376c08),
    UINT32_C(0x2748774c), UINT32_C(0x34b0bcb5),
    UINT32_C(0x391c0cb3), UINT32_C(0x4ed8aa4a),
    UINT32_C(0x5b9cca4f), UINT32_C(0x682e6ff3),
    UINT32_C(0x748f82ee), UINT32_C(0x78a5636f),
    UINT32_C(0x84c87814), UINT32_C(0x8cc70208),
    UINT32_C(0x90befffa), UINT32_C(0xa4506ceb),
    UINT32_C(0xbef9a3f7), UINT32_C(0xc67178f2)
};

static uint32_t pchsi_rotate_right(uint32_t value, unsigned int amount)
{
    return (value >> amount) | (value << (32U - amount));
}

static uint32_t pchsi_choose(uint32_t x, uint32_t y, uint32_t z)
{
    return (x & y) ^ ((~x) & z);
}

static uint32_t pchsi_majority(uint32_t x, uint32_t y, uint32_t z)
{
    return (x & y) ^ (x & z) ^ (y & z);
}

static uint32_t pchsi_big_sigma_zero(uint32_t value)
{
    return (
        pchsi_rotate_right(value, 2U)
        ^ pchsi_rotate_right(value, 13U)
        ^ pchsi_rotate_right(value, 22U)
    );
}

static uint32_t pchsi_big_sigma_one(uint32_t value)
{
    return (
        pchsi_rotate_right(value, 6U)
        ^ pchsi_rotate_right(value, 11U)
        ^ pchsi_rotate_right(value, 25U)
    );
}

static uint32_t pchsi_small_sigma_zero(uint32_t value)
{
    return (
        pchsi_rotate_right(value, 7U)
        ^ pchsi_rotate_right(value, 18U)
        ^ (value >> 3U)
    );
}

static uint32_t pchsi_small_sigma_one(uint32_t value)
{
    return (
        pchsi_rotate_right(value, 17U)
        ^ pchsi_rotate_right(value, 19U)
        ^ (value >> 10U)
    );
}

static uint32_t pchsi_load_u32_be(const unsigned char *input)
{
    return (
        ((uint32_t)input[0] << 24U)
        | ((uint32_t)input[1] << 16U)
        | ((uint32_t)input[2] << 8U)
        | (uint32_t)input[3]
    );
}

static void pchsi_store_u32_be(uint32_t value, unsigned char *output)
{
    output[0] = (unsigned char)(value >> 24U);
    output[1] = (unsigned char)(value >> 16U);
    output[2] = (unsigned char)(value >> 8U);
    output[3] = (unsigned char)value;
}

static void pchsi_store_u64_be(uint64_t value, unsigned char *output)
{
    size_t index = 0U;

    for (index = 0U; index < 8U; index += 1U) {
        output[7U - index] = (unsigned char)(value >> (index * 8U));
    }
}

static void pchsi_sha256_transform(
    struct pchsi_sha256_context *context,
    const unsigned char block[PCHSI_SHA256_BLOCK_BYTES]
)
{
    uint32_t schedule[64];
    uint32_t a;
    uint32_t b;
    uint32_t c;
    uint32_t d;
    uint32_t e;
    uint32_t f;
    uint32_t g;
    uint32_t h;
    size_t index = 0U;

    for (index = 0U; index < 16U; index += 1U) {
        schedule[index] = pchsi_load_u32_be(block + (index * 4U));
    }

    for (index = 16U; index < 64U; index += 1U) {
        schedule[index] = (
            pchsi_small_sigma_one(schedule[index - 2U])
            + schedule[index - 7U]
            + pchsi_small_sigma_zero(schedule[index - 15U])
            + schedule[index - 16U]
        );
    }

    a = context->state[0];
    b = context->state[1];
    c = context->state[2];
    d = context->state[3];
    e = context->state[4];
    f = context->state[5];
    g = context->state[6];
    h = context->state[7];

    for (index = 0U; index < 64U; index += 1U) {
        uint32_t temporary_one = (
            h
            + pchsi_big_sigma_one(e)
            + pchsi_choose(e, f, g)
            + PCHSI_SHA256_CONSTANTS[index]
            + schedule[index]
        );
        uint32_t temporary_two = (
            pchsi_big_sigma_zero(a)
            + pchsi_majority(a, b, c)
        );

        h = g;
        g = f;
        f = e;
        e = d + temporary_one;
        d = c;
        c = b;
        b = a;
        a = temporary_one + temporary_two;
    }

    context->state[0] += a;
    context->state[1] += b;
    context->state[2] += c;
    context->state[3] += d;
    context->state[4] += e;
    context->state[5] += f;
    context->state[6] += g;
    context->state[7] += h;

    memset(schedule, 0, sizeof(schedule));
}

static void pchsi_secure_zero(void *memory, size_t size)
{
    volatile unsigned char *cursor = memory;

    while (size > 0U) {
        *cursor = 0U;
        cursor += 1;
        size -= 1U;
    }
}

void pchsi_sha256_init(struct pchsi_sha256_context *context)
{
    if (context == NULL) {
        return;
    }

    context->state[0] = UINT32_C(0x6a09e667);
    context->state[1] = UINT32_C(0xbb67ae85);
    context->state[2] = UINT32_C(0x3c6ef372);
    context->state[3] = UINT32_C(0xa54ff53a);
    context->state[4] = UINT32_C(0x510e527f);
    context->state[5] = UINT32_C(0x9b05688c);
    context->state[6] = UINT32_C(0x1f83d9ab);
    context->state[7] = UINT32_C(0x5be0cd19);
    context->bit_count = UINT64_C(0);
    context->buffer_size = 0U;
    memset(context->buffer, 0, sizeof(context->buffer));
}

void pchsi_sha256_update(
    struct pchsi_sha256_context *context,
    const unsigned char *data,
    size_t size
)
{
    size_t offset = 0U;

    if (context == NULL || (data == NULL && size != 0U)) {
        return;
    }

    context->bit_count += (uint64_t)size * UINT64_C(8);

    if (context->buffer_size > 0U) {
        size_t needed = PCHSI_SHA256_BLOCK_BYTES - context->buffer_size;
        size_t copied = size < needed ? size : needed;

        memcpy(
            context->buffer + context->buffer_size,
            data,
            copied
        );
        context->buffer_size += copied;
        offset += copied;

        if (context->buffer_size == PCHSI_SHA256_BLOCK_BYTES) {
            pchsi_sha256_transform(context, context->buffer);
            context->buffer_size = 0U;
            memset(context->buffer, 0, sizeof(context->buffer));
        }
    }

    while (offset < size && size - offset >= PCHSI_SHA256_BLOCK_BYTES) {
        pchsi_sha256_transform(context, data + offset);
        offset += PCHSI_SHA256_BLOCK_BYTES;
    }

    if (offset < size) {
        context->buffer_size = size - offset;
        memcpy(
            context->buffer,
            data + offset,
            context->buffer_size
        );
    }
}

void pchsi_sha256_final(
    struct pchsi_sha256_context *context,
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES]
)
{
    uint64_t original_bit_count;
    size_t index = 0U;

    if (context == NULL || digest == NULL) {
        return;
    }

    original_bit_count = context->bit_count;

    context->buffer[context->buffer_size] = 0x80U;
    context->buffer_size += 1U;

    if (context->buffer_size > 56U) {
        memset(
            context->buffer + context->buffer_size,
            0,
            PCHSI_SHA256_BLOCK_BYTES - context->buffer_size
        );
        pchsi_sha256_transform(context, context->buffer);
        context->buffer_size = 0U;
    }

    memset(
        context->buffer + context->buffer_size,
        0,
        56U - context->buffer_size
    );
    pchsi_store_u64_be(original_bit_count, context->buffer + 56U);
    pchsi_sha256_transform(context, context->buffer);

    for (index = 0U; index < 8U; index += 1U) {
        pchsi_store_u32_be(
            context->state[index],
            digest + (index * 4U)
        );
    }

    pchsi_secure_zero(context, sizeof(*context));
}

int pchsi_sha256_file_descriptor(
    int file_descriptor,
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES]
)
{
    struct pchsi_sha256_context context;
    unsigned char buffer[32768];

    if (file_descriptor < 0 || digest == NULL) {
        errno = EINVAL;
        return -1;
    }

    pchsi_sha256_init(&context);

    for (;;) {
        ssize_t count = read(file_descriptor, buffer, sizeof(buffer));

        if (count > 0) {
            pchsi_sha256_update(
                &context,
                buffer,
                (size_t)count
            );
            continue;
        }

        if (count == 0) {
            break;
        }

        if (errno == EINTR) {
            continue;
        }

        pchsi_secure_zero(&context, sizeof(context));
        pchsi_secure_zero(buffer, sizeof(buffer));
        return -1;
    }

    pchsi_sha256_final(&context, digest);
    pchsi_secure_zero(buffer, sizeof(buffer));
    return 0;
}
