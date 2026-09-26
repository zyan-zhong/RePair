#include "pchsi_s1/evidence.h"

#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

void pchsi_test_paths(void);

static const unsigned char DIGEST_X[PCHSI_EVIDENCE_DIGEST_BYTES] = {
    0x2DU, 0x71U, 0x16U, 0x42U, 0xB7U, 0x26U, 0xB0U, 0x44U,
    0x01U, 0x62U, 0x7CU, 0xA9U, 0xFBU, 0xACU, 0x32U, 0xF5U,
    0xC8U, 0x53U, 0x0FU, 0xB1U, 0x90U, 0x3CU, 0xC4U, 0xDBU,
    0x02U, 0x25U, 0x87U, 0x17U, 0x92U, 0x1AU, 0x48U, 0x81U
};

static void write_u64(unsigned char *buffer, size_t *offset, uint64_t value)
{
    size_t index = 0U;
    for (index = 0U; index < 8U; index += 1U) {
        buffer[*offset + 7U - index] = (unsigned char)(value & 0xFFU);
        value >>= 8U;
    }
    *offset += 8U;
}

static int known_digest(
    const unsigned char *content,
    size_t content_size,
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES],
    void *context
)
{
    (void)context;
    if (content_size == 1U && content[0] == (unsigned char)'x') {
        memcpy(digest, DIGEST_X, sizeof(DIGEST_X));
        return 0;
    }
    return 1;
}

static size_t build_one_entry_stream(unsigned char *buffer, int corrupt_digest)
{
    const unsigned char magic[] = "PCHSI_EVIDENCE_STREAM_V1";
    const unsigned char path[] = "a";
    size_t offset = 0U;
    size_t digest_index = 0U;
    size_t index_size = 8U + 1U + 8U + PCHSI_EVIDENCE_DIGEST_BYTES;

    memcpy(buffer + offset, magic, sizeof(magic) - 1U);
    offset += sizeof(magic) - 1U;
    write_u64(buffer, &offset, 1U);
    write_u64(buffer, &offset, index_size);
    write_u64(buffer, &offset, 1U);
    buffer[offset++] = (unsigned char)'a';
    write_u64(buffer, &offset, 1U);
    for (digest_index = 0U; digest_index < PCHSI_EVIDENCE_DIGEST_BYTES; digest_index += 1U) {
        buffer[offset + digest_index] = DIGEST_X[digest_index];
    }
    if (corrupt_digest != 0) {
        buffer[offset] ^= 0xFFU;
    }
    offset += PCHSI_EVIDENCE_DIGEST_BYTES;
    write_u64(buffer, &offset, 1U);
    buffer[offset++] = path[0];
    write_u64(buffer, &offset, 1U);
    buffer[offset++] = (unsigned char)'x';
    return offset;
}



#ifdef PCHSI_EVIDENCE_TREE_TESTS

#include "pchsi_s1/sha256.h"
#include "pchsi_s1/strict_json.h"
#include "pchsi_s1/system_ops.h"

#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static int tree_validate_json(
    void *context,
    const unsigned char *data,
    size_t size
)
{
    struct pchsi_json_error error = {0};

    (void)context;

    return (
        pchsi_json_validate_strict(
            data,
            size,
            &error
        ) == PCHSI_JSON_OK
    ) ? 0 : 1;
}

static int tree_sha256(
    void *context,
    const unsigned char *data,
    size_t size,
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES]
)
{
    struct pchsi_sha256_context sha_context;

    (void)context;

    pchsi_sha256_init(&sha_context);
    pchsi_sha256_update(&sha_context, data, size);
    pchsi_sha256_final(&sha_context, digest);
    return 0;
}

static void digest_to_hex(
    const unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES],
    char output[65]
)
{
    static const char HEX[] = "0123456789abcdef";
    size_t index = 0U;

    for (index = 0U; index < PCHSI_EVIDENCE_DIGEST_BYTES; index += 1U) {
        output[index * 2U] = HEX[digest[index] >> 4U];
        output[index * 2U + 1U] = HEX[digest[index] & 0x0FU];
    }
    output[64] = '\0';
}

static void write_file_exact(
    int directory_fd,
    const char *name,
    const unsigned char *content,
    size_t size
)
{
    int descriptor = openat(
        directory_fd,
        name,
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC,
        0600
    );
    size_t offset = 0U;

    assert(descriptor >= 0);

    while (offset < size) {
        ssize_t count = write(
            descriptor,
            content + offset,
            size - offset
        );

        assert(count > 0);
        offset += (size_t)count;
    }

    assert(close(descriptor) == 0);
}

static void create_valid_tree(
    int directory_fd
)
{
    static const unsigned char SEMANTIC[] =
        "{\"schema_version\":\"probe_evidence_v1\"}\n";
    static const unsigned char LOCAL[] =
        "{\"duration_microseconds\":10}\n";
    struct pchsi_sha256_context context;
    unsigned char digest[PCHSI_SHA256_DIGEST_BYTES];
    char hex[65];
    char sidecar[96];
    int length = 0;

    write_file_exact(
        directory_fd,
        "semantic_evidence.json",
        SEMANTIC,
        sizeof(SEMANTIC) - 1U
    );
    write_file_exact(
        directory_fd,
        "local_evidence.json",
        LOCAL,
        sizeof(LOCAL) - 1U
    );

    pchsi_sha256_init(&context);
    pchsi_sha256_update(
        &context,
        LOCAL,
        sizeof(LOCAL) - 1U
    );
    pchsi_sha256_final(&context, digest);
    digest_to_hex(digest, hex);

    length = snprintf(
        sidecar,
        sizeof(sidecar),
        "%s  local_evidence.json\n",
        hex
    );

    assert(length == 86);

    write_file_exact(
        directory_fd,
        "local_evidence.json.sha256",
        (const unsigned char *)sidecar,
        (size_t)length
    );
}

static struct pchsi_evidence_limits tree_limits(void)
{
    struct pchsi_evidence_limits limits = {
        3U,
        UINT64_C(4194304),
        UINT64_C(2097152),
        1U
    };

    return limits;
}

static void test_valid_evidence_tree(void)
{
    char template[] = "/tmp/pchsi-evidence-tree-XXXXXX";
    char *directory_path = mkdtemp(template);
    int directory_fd = -1;
    struct pchsi_evidence_index index;
    struct pchsi_evidence_limits limits = tree_limits();
    struct pchsi_evidence_content_ops content_operations = {
        NULL,
        tree_validate_json,
        tree_sha256
    };

    assert(directory_path != NULL);

    directory_fd = open(
        directory_path,
        O_RDONLY | O_DIRECTORY | O_CLOEXEC
    );
    assert(directory_fd >= 0);

    create_valid_tree(directory_fd);

    assert(
        pchsi_validate_evidence_tree(
            directory_fd,
            &limits,
            &index,
            pchsi_real_system_ops(),
            &content_operations
        ) == PCHSI_EVIDENCE_TREE_OK
    );
    assert(index.count == 3U);
    assert(
        strcmp(
            index.entries[0].path,
            "local_evidence.json"
        ) == 0
    );
    assert(
        strcmp(
            index.entries[1].path,
            "local_evidence.json.sha256"
        ) == 0
    );
    assert(
        strcmp(
            index.entries[2].path,
            "semantic_evidence.json"
        ) == 0
    );

    assert(
        unlinkat(
            directory_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );
    assert(
        unlinkat(
            directory_fd,
            "local_evidence.json",
            0
        ) == 0
    );
    assert(
        unlinkat(
            directory_fd,
            "local_evidence.json.sha256",
            0
        ) == 0
    );
    assert(close(directory_fd) == 0);
    assert(rmdir(directory_path) == 0);
}

static void test_evidence_tree_rejects_symlink_and_hardlink(void)
{
    char template[] = "/tmp/pchsi-evidence-tree-bad-XXXXXX";
    char *directory_path = mkdtemp(template);
    int directory_fd = -1;
    struct pchsi_evidence_index index;
    struct pchsi_evidence_limits limits = tree_limits();
    struct pchsi_evidence_content_ops content_operations = {
        NULL,
        tree_validate_json,
        tree_sha256
    };

    assert(directory_path != NULL);
    directory_fd = open(
        directory_path,
        O_RDONLY | O_DIRECTORY | O_CLOEXEC
    );
    assert(directory_fd >= 0);

    create_valid_tree(directory_fd);

    assert(
        symlinkat(
            "local_evidence.json",
            directory_fd,
            "unexpected"
        ) == 0
    );
    assert(
        pchsi_validate_evidence_tree(
            directory_fd,
            &limits,
            &index,
            pchsi_real_system_ops(),
            &content_operations
        ) == PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH
    );
    assert(unlinkat(directory_fd, "unexpected", 0) == 0);

    assert(
        unlinkat(
            directory_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );
    assert(
        linkat(
            directory_fd,
            "local_evidence.json",
            directory_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );
    assert(
        pchsi_validate_evidence_tree(
            directory_fd,
            &limits,
            &index,
            pchsi_real_system_ops(),
            &content_operations
        ) == PCHSI_EVIDENCE_TREE_HARDLINK_REJECTED
    );

    assert(
        unlinkat(
            directory_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );
    assert(
        unlinkat(
            directory_fd,
            "local_evidence.json",
            0
        ) == 0
    );
    assert(
        unlinkat(
            directory_fd,
            "local_evidence.json.sha256",
            0
        ) == 0
    );
    assert(close(directory_fd) == 0);
    assert(rmdir(directory_path) == 0);
}

static void test_no_clobber_publication(void)
{
    char staging_template[] = "/tmp/pchsi-staging-XXXXXX";
    char output_template[] = "/tmp/pchsi-output-XXXXXX";
    char *staging_path = mkdtemp(staging_template);
    char *output_path = mkdtemp(output_template);
    int staging_fd = -1;
    int output_fd = -1;
    static const unsigned char CONTENT[] = "{}\n";

    assert(staging_path != NULL);
    assert(output_path != NULL);

    staging_fd = open(
        staging_path,
        O_RDONLY | O_DIRECTORY | O_CLOEXEC
    );
    output_fd = open(
        output_path,
        O_RDONLY | O_DIRECTORY | O_CLOEXEC
    );

    assert(staging_fd >= 0);
    assert(output_fd >= 0);

    write_file_exact(
        staging_fd,
        "candidate",
        CONTENT,
        sizeof(CONTENT) - 1U
    );
    write_file_exact(
        output_fd,
        "semantic_evidence.json",
        CONTENT,
        sizeof(CONTENT) - 1U
    );

    assert(
        pchsi_publish_evidence_file_no_clobber(
            staging_fd,
            "candidate",
            output_fd,
            "semantic_evidence.json",
            pchsi_real_system_ops()
        ) == PCHSI_EVIDENCE_TREE_TARGET_EXISTS
    );

    assert(
        unlinkat(
            output_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );

    assert(
        pchsi_publish_evidence_file_no_clobber(
            staging_fd,
            "candidate",
            output_fd,
            "semantic_evidence.json",
            pchsi_real_system_ops()
        ) == PCHSI_EVIDENCE_TREE_OK
    );

    assert(
        faccessat(
            staging_fd,
            "candidate",
            F_OK,
            0
        ) != 0
    );
    assert(
        faccessat(
            output_fd,
            "semantic_evidence.json",
            F_OK,
            0
        ) == 0
    );

    assert(
        unlinkat(
            output_fd,
            "semantic_evidence.json",
            0
        ) == 0
    );
    assert(close(staging_fd) == 0);
    assert(close(output_fd) == 0);
    assert(rmdir(staging_path) == 0);
    assert(rmdir(output_path) == 0);
}

static void pchsi_test_evidence_tree_and_publication(void)
{
    test_valid_evidence_tree();
    test_evidence_tree_rejects_symlink_and_hardlink();
    test_no_clobber_publication();
}

#endif

int main(void)
{
    unsigned char stream[256];
    struct pchsi_evidence_error error = {0};
    size_t size = 0U;

    pchsi_test_paths();

#ifdef PCHSI_EVIDENCE_TREE_TESTS
    pchsi_test_evidence_tree_and_publication();
#endif

    size = build_one_entry_stream(stream, 0);
    assert(
        pchsi_evidence_validate(
            stream,
            size,
            known_digest,
            NULL,
            &error
        ) == PCHSI_EVIDENCE_OK
    );

    size = build_one_entry_stream(stream, 1);
    assert(
        pchsi_evidence_validate(
            stream,
            size,
            known_digest,
            NULL,
            &error
        ) == PCHSI_EVIDENCE_CONTENT_DIGEST_MISMATCH
    );

    size = build_one_entry_stream(stream, 0);
    stream[size++] = 0U;
    assert(
        pchsi_evidence_validate(
            stream,
            size,
            known_digest,
            NULL,
            &error
        ) == PCHSI_EVIDENCE_TRAILING_DATA
    );

    (void)printf("native evidence tests passed\n");
    return 0;
}
