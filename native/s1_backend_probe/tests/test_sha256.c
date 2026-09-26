#include "pchsi_s1/sha256.h"

#include <assert.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void digest_to_hex(
    const unsigned char digest[PCHSI_SHA256_DIGEST_BYTES],
    char output[(PCHSI_SHA256_DIGEST_BYTES * 2U) + 1U]
)
{
    static const char HEX[] = "0123456789abcdef";
    size_t index = 0U;

    for (index = 0U; index < PCHSI_SHA256_DIGEST_BYTES; index += 1U) {
        output[index * 2U] = HEX[digest[index] >> 4U];
        output[(index * 2U) + 1U] = HEX[digest[index] & 0x0FU];
    }

    output[PCHSI_SHA256_DIGEST_BYTES * 2U] = '\0';
}

static void assert_hash(
    const unsigned char *data,
    size_t size,
    const char *expected
)
{
    struct pchsi_sha256_context context;
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES];
    char hex[(PCHSI_SHA256_DIGEST_BYTES * 2U) + 1U];

    pchsi_sha256_init(&context);
    pchsi_sha256_update(&context, data, size);
    pchsi_sha256_final(&context, digest);
    digest_to_hex(digest, hex);

    assert(strcmp(hex, expected) == 0);
}

static void test_known_answers(void)
{
    static const unsigned char EMPTY[] = "";
    static const unsigned char ABC[] = "abc";

    assert_hash(
        EMPTY,
        0U,
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855"
    );

    assert_hash(
        ABC,
        3U,
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    );
}

static void test_million_a(void)
{
    struct pchsi_sha256_context context;
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES];
    unsigned char block[1000];
    char hex[(PCHSI_SHA256_DIGEST_BYTES * 2U) + 1U];
    size_t index = 0U;

    memset(block, 'a', sizeof(block));
    pchsi_sha256_init(&context);

    for (index = 0U; index < 1000U; index += 1U) {
        pchsi_sha256_update(&context, block, sizeof(block));
    }

    pchsi_sha256_final(&context, digest);
    digest_to_hex(digest, hex);

    assert(
        strcmp(
            hex,
            "cdc76e5c9914fb9281a1c7e284d73e67"
            "f1809a48a497200e046d39ccc7112cd0"
        )
        == 0
    );
}

static void test_chunk_boundaries(void)
{
    static const unsigned char MESSAGE[] =
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789";
    struct pchsi_sha256_context single;
    struct pchsi_sha256_context chunked;
    unsigned char single_digest[PCHSI_SHA256_DIGEST_BYTES];
    unsigned char chunked_digest[PCHSI_SHA256_DIGEST_BYTES];
    size_t offset = 0U;
    size_t chunk_size = 1U;

    pchsi_sha256_init(&single);
    pchsi_sha256_update(&single, MESSAGE, sizeof(MESSAGE) - 1U);
    pchsi_sha256_final(&single, single_digest);

    pchsi_sha256_init(&chunked);

    while (offset < sizeof(MESSAGE) - 1U) {
        size_t remaining = (sizeof(MESSAGE) - 1U) - offset;
        size_t current = chunk_size < remaining ? chunk_size : remaining;

        pchsi_sha256_update(&chunked, MESSAGE + offset, current);
        offset += current;
        chunk_size = chunk_size == 67U ? 1U : chunk_size + 1U;
    }

    pchsi_sha256_final(&chunked, chunked_digest);

    assert(
        memcmp(
            single_digest,
            chunked_digest,
            PCHSI_SHA256_DIGEST_BYTES
        )
        == 0
    );
}

static void test_file_descriptor_streaming(void)
{
    static const unsigned char CONTENT[] =
        "file descriptor streaming test\n"
        "with more than one logical line\n";
    char template[] = "/tmp/pchsi-sha256-test.XXXXXX";
    int descriptor = mkstemp(template);
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES];
    char hex[(PCHSI_SHA256_DIGEST_BYTES * 2U) + 1U];
    ssize_t written;

    assert(descriptor >= 0);

    written = write(descriptor, CONTENT, sizeof(CONTENT) - 1U);
    assert(written == (ssize_t)(sizeof(CONTENT) - 1U));
    assert(lseek(descriptor, 0, SEEK_SET) == 0);

    assert(pchsi_sha256_file_descriptor(descriptor, digest) == 0);
    digest_to_hex(digest, hex);

    assert(
        strcmp(
            hex,
            "fa69936a7516781a8aa9a374c4de7580"
            "6464cf36e0617a84a85d48cca74de158"
        )
        == 0
    );

    assert(close(descriptor) == 0);
    assert(unlink(template) == 0);
}

static void test_context_zeroized_after_final(void)
{
    struct pchsi_sha256_context context;
    struct pchsi_sha256_context zero;
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES];

    memset(&zero, 0, sizeof(zero));
    pchsi_sha256_init(&context);
    pchsi_sha256_update(
        &context,
        (const unsigned char *)"sensitive",
        9U
    );
    pchsi_sha256_final(&context, digest);

    assert(memcmp(&context, &zero, sizeof(context)) == 0);
}

int main(void)
{
    test_known_answers();
    test_million_a();
    test_chunk_boundaries();
    test_file_descriptor_streaming();
    test_context_zeroized_after_final();

    (void)puts("native sha256 tests passed");
    return 0;
}
