#include "pchsi_s1/source_copy.h"
#include "pchsi_s1/sha256.h"

#include <fcntl.h>
#include <string.h>
#include <unistd.h>

static int pchsi_identity_matches(
    const struct pchsi_file_identity *expected,
    const struct stat *observed
)
{
    return (
        expected->device == observed->st_dev
        && expected->inode == observed->st_ino
        && expected->size == observed->st_size
        && expected->mode == observed->st_mode
    );
}

static int pchsi_hash_with_operations(
    int source_fd,
    const struct pchsi_system_ops *operations,
    unsigned char digest[PCHSI_SOURCE_DIGEST_BYTES]
)
{
    struct pchsi_sha256_context context;
    unsigned char buffer[PCHSI_SOURCE_COPY_BUFFER_BYTES];

    if (
        operations->lseek_fn(
            operations->context,
            source_fd,
            0,
            SEEK_SET
        ) < 0
    ) {
        return 0;
    }

    pchsi_sha256_init(&context);

    for (;;) {
        ssize_t count = operations->read_fn(
            operations->context,
            source_fd,
            buffer,
            sizeof(buffer)
        );

        if (count < 0) {
            memset(&context, 0, sizeof(context));
            memset(buffer, 0, sizeof(buffer));
            return 0;
        }

        if (count == 0) {
            break;
        }

        pchsi_sha256_update(
            &context,
            buffer,
            (size_t)count
        );
    }

    pchsi_sha256_final(&context, digest);
    memset(buffer, 0, sizeof(buffer));
    return 1;
}

static int pchsi_write_all(
    int destination_fd,
    const unsigned char *buffer,
    size_t size,
    const struct pchsi_system_ops *operations
)
{
    size_t offset = 0U;

    while (offset < size) {
        ssize_t written = operations->write_fn(
            operations->context,
            destination_fd,
            buffer + offset,
            size - offset
        );

        if (written <= 0) {
            return 0;
        }

        offset += (size_t)written;
    }

    return 1;
}

enum pchsi_status pchsi_copy_and_seal_source(
    int source_fd,
    const struct pchsi_file_identity *expected_identity,
    int destination_directory_fd,
    const char *destination_name,
    const unsigned char expected_sha256[PCHSI_SOURCE_DIGEST_BYTES],
    const struct pchsi_system_ops *operations
)
{
    struct stat before = {0};
    struct stat after = {0};
    unsigned char observed_sha256[PCHSI_SOURCE_DIGEST_BYTES];
    unsigned char buffer[PCHSI_SOURCE_COPY_BUFFER_BYTES];
    int destination_fd = -1;
    int destination_created = 0;
    enum pchsi_status result = PCHSI_STATUS_SOURCE_COPY_FAILED;

    if (
        source_fd < 0
        || expected_identity == NULL
        || destination_directory_fd < 0
        || destination_name == NULL
        || destination_name[0] == '\0'
        || strchr(destination_name, '/') != NULL
        || expected_sha256 == NULL
        || operations == NULL
        || operations->fstat_fn == NULL
        || operations->lseek_fn == NULL
        || operations->read_fn == NULL
        || operations->write_fn == NULL
        || operations->openat_fn == NULL
        || operations->fsync_fn == NULL
        || operations->close_fn == NULL
        || operations->unlinkat_fn == NULL
    ) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    if (
        operations->fstat_fn(
            operations->context,
            source_fd,
            &before
        ) != 0
        || !pchsi_identity_matches(expected_identity, &before)
    ) {
        result = PCHSI_STATUS_SOURCE_IDENTITY_CHANGED;
        goto cleanup;
    }

    if (
        !pchsi_hash_with_operations(
            source_fd,
            operations,
            observed_sha256
        )
    ) {
        result = PCHSI_STATUS_SOURCE_COPY_FAILED;
        goto cleanup;
    }

    if (
        memcmp(
            observed_sha256,
            expected_sha256,
            PCHSI_SOURCE_DIGEST_BYTES
        ) != 0
    ) {
        result = PCHSI_STATUS_SOURCE_HASH_MISMATCH;
        goto cleanup;
    }

    if (
        operations->lseek_fn(
            operations->context,
            source_fd,
            0,
            SEEK_SET
        ) < 0
    ) {
        goto cleanup;
    }

    destination_fd = operations->openat_fn(
        operations->context,
        destination_directory_fd,
        destination_name,
        O_WRONLY
            | O_CREAT
            | O_EXCL
            | O_CLOEXEC
            | O_NOFOLLOW,
        0444U
    );

    if (destination_fd < 0) {
        goto cleanup;
    }
    destination_created = 1;

    for (;;) {
        ssize_t count = operations->read_fn(
            operations->context,
            source_fd,
            buffer,
            sizeof(buffer)
        );

        if (count < 0) {
            goto cleanup;
        }

        if (count == 0) {
            break;
        }

        if (
            !pchsi_write_all(
                destination_fd,
                buffer,
                (size_t)count,
                operations
            )
        ) {
            goto cleanup;
        }
    }

    if (
        operations->fsync_fn(
            operations->context,
            destination_fd
        ) != 0
    ) {
        result = PCHSI_STATUS_SOURCE_SEAL_FAILED;
        goto cleanup;
    }

    if (
        operations->fstat_fn(
            operations->context,
            source_fd,
            &after
        ) != 0
        || !pchsi_identity_matches(expected_identity, &after)
    ) {
        result = PCHSI_STATUS_SOURCE_IDENTITY_CHANGED;
        goto cleanup;
    }

    result = PCHSI_STATUS_OK;

cleanup:
    memset(observed_sha256, 0, sizeof(observed_sha256));
    memset(buffer, 0, sizeof(buffer));

    if (destination_fd >= 0) {
        (void)operations->close_fn(
            operations->context,
            destination_fd
        );
    }

    if (result != PCHSI_STATUS_OK && destination_created) {
        (void)operations->unlinkat_fn(
            operations->context,
            destination_directory_fd,
            destination_name,
            0
        );
    }

    (void)operations->close_fn(
        operations->context,
        source_fd
    );

    return result;
}
