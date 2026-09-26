#include "pchsi_s1/evidence.h"
#include "pchsi_s1/path_contract.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static const unsigned char PCHSI_EVIDENCE_MAGIC[] =
    "PCHSI_EVIDENCE_STREAM_V1";

struct pchsi_index_entry {
    const unsigned char *path;
    size_t path_size;
    size_t content_size;
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES];
};

static enum pchsi_evidence_status pchsi_set_error(
    struct pchsi_evidence_error *error,
    enum pchsi_evidence_status status,
    size_t offset
)
{
    if (error != NULL) {
        error->status = status;
        error->offset = offset;
    }
    return status;
}

static int pchsi_read_u64(
    const unsigned char *data,
    size_t size,
    size_t *offset,
    uint64_t *value
)
{
    uint64_t result = 0U;
    size_t index = 0U;

    if (*offset > size || size - *offset < 8U) {
        return 0;
    }

    for (index = 0U; index < 8U; index += 1U) {
        result = (result << 8U) | (uint64_t)data[*offset + index];
    }

    *offset += 8U;
    *value = result;
    return 1;
}

static int pchsi_u64_to_size(uint64_t value, size_t *result)
{
    if (value > (uint64_t)SIZE_MAX) {
        return 0;
    }
    *result = (size_t)value;
    return 1;
}

static int pchsi_compare_paths(
    const unsigned char *left,
    size_t left_size,
    const unsigned char *right,
    size_t right_size
)
{
    size_t common = left_size < right_size ? left_size : right_size;
    int comparison = memcmp(left, right, common);

    if (comparison != 0) {
        return comparison;
    }
    if (left_size < right_size) {
        return -1;
    }
    if (left_size > right_size) {
        return 1;
    }
    return 0;
}

static enum pchsi_evidence_status pchsi_parse_index(
    const unsigned char *index_data,
    size_t index_size,
    size_t entry_count,
    struct pchsi_index_entry *entries,
    struct pchsi_evidence_error *error,
    size_t stream_index_offset
)
{
    size_t offset = 0U;
    size_t entry_index = 0U;

    for (entry_index = 0U; entry_index < entry_count; entry_index += 1U) {
        uint64_t raw_path_size = 0U;
        uint64_t raw_content_size = 0U;
        size_t path_size = 0U;
        size_t content_size = 0U;
        enum pchsi_path_status path_status;

        if (!pchsi_read_u64(index_data, index_size, &offset, &raw_path_size)) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_TRUNCATED,
                stream_index_offset + offset
            );
        }
        if (!pchsi_u64_to_size(raw_path_size, &path_size)) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_INVALID_PATH,
                stream_index_offset + offset
            );
        }
        if (offset > index_size || path_size > index_size - offset) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_TRUNCATED,
                stream_index_offset + offset
            );
        }

        path_status = pchsi_validate_evidence_path(
            index_data + offset,
            path_size,
            NULL
        );
        if (path_status != PCHSI_PATH_OK) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_INVALID_PATH,
                stream_index_offset + offset
            );
        }

        entries[entry_index].path = index_data + offset;
        entries[entry_index].path_size = path_size;
        offset += path_size;

        if (!pchsi_read_u64(index_data, index_size, &offset, &raw_content_size)) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_TRUNCATED,
                stream_index_offset + offset
            );
        }
        if (!pchsi_u64_to_size(raw_content_size, &content_size)) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_CONTENT_TOO_LARGE,
                stream_index_offset + offset
            );
        }
        if (content_size > PCHSI_EVIDENCE_MAX_CONTENT_BYTES) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_CONTENT_TOO_LARGE,
                stream_index_offset + offset
            );
        }
        entries[entry_index].content_size = content_size;

        if (
            offset > index_size
            || PCHSI_EVIDENCE_DIGEST_BYTES > index_size - offset
        ) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_TRUNCATED,
                stream_index_offset + offset
            );
        }
        memcpy(
            entries[entry_index].digest,
            index_data + offset,
            PCHSI_EVIDENCE_DIGEST_BYTES
        );
        offset += PCHSI_EVIDENCE_DIGEST_BYTES;

        if (entry_index > 0U) {
            int comparison = pchsi_compare_paths(
                entries[entry_index - 1U].path,
                entries[entry_index - 1U].path_size,
                entries[entry_index].path,
                entries[entry_index].path_size
            );
            if (comparison == 0) {
                return pchsi_set_error(
                    error,
                    PCHSI_EVIDENCE_DUPLICATE_PATH,
                    stream_index_offset + offset
                );
            }
            if (comparison > 0) {
                return pchsi_set_error(
                    error,
                    PCHSI_EVIDENCE_INDEX_NOT_SORTED,
                    stream_index_offset + offset
                );
            }
        }
    }

    if (offset != index_size) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_INDEX_LENGTH_MISMATCH,
            stream_index_offset + offset
        );
    }

    return PCHSI_EVIDENCE_OK;
}

enum pchsi_evidence_status pchsi_evidence_validate(
    const unsigned char *stream,
    size_t stream_size,
    pchsi_evidence_digest_fn digest_fn,
    void *digest_context,
    struct pchsi_evidence_error *error
)
{
    size_t offset = 0U;
    size_t entry_count = 0U;
    size_t index_size = 0U;
    uint64_t raw_entry_count = 0U;
    uint64_t raw_index_size = 0U;
    size_t entry_index = 0U;
    struct pchsi_index_entry *entries = NULL;
    enum pchsi_evidence_status status;

    if (error != NULL) {
        error->status = PCHSI_EVIDENCE_OK;
        error->offset = 0U;
    }

    if (stream == NULL || stream_size > PCHSI_EVIDENCE_MAX_STREAM_BYTES) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_STREAM_TOO_LARGE,
            0U
        );
    }

    if (
        stream_size < sizeof(PCHSI_EVIDENCE_MAGIC) - 1U
        || memcmp(
            stream,
            PCHSI_EVIDENCE_MAGIC,
            sizeof(PCHSI_EVIDENCE_MAGIC) - 1U
        ) != 0
    ) {
        return pchsi_set_error(error, PCHSI_EVIDENCE_INVALID_MAGIC, 0U);
    }
    offset = sizeof(PCHSI_EVIDENCE_MAGIC) - 1U;

    if (!pchsi_read_u64(stream, stream_size, &offset, &raw_entry_count)) {
        return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
    }
    if (!pchsi_u64_to_size(raw_entry_count, &entry_count)) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_ENTRY_COUNT_EXCEEDED,
            offset
        );
    }
    if (entry_count > PCHSI_EVIDENCE_MAX_ENTRIES) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_ENTRY_COUNT_EXCEEDED,
            offset
        );
    }

    if (!pchsi_read_u64(stream, stream_size, &offset, &raw_index_size)) {
        return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
    }
    if (!pchsi_u64_to_size(raw_index_size, &index_size)) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_INDEX_TOO_LARGE,
            offset
        );
    }
    if (index_size > PCHSI_EVIDENCE_MAX_INDEX_BYTES) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_INDEX_TOO_LARGE,
            offset
        );
    }
    if (offset > stream_size || index_size > stream_size - offset) {
        return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
    }

    if (entry_count > 0U) {
        entries = calloc(entry_count, sizeof(*entries));
        if (entries == NULL) {
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_ALLOCATION_FAILED,
                offset
            );
        }
    }

    status = pchsi_parse_index(
        stream + offset,
        index_size,
        entry_count,
        entries,
        error,
        offset
    );
    if (status != PCHSI_EVIDENCE_OK) {
        free(entries);
        return status;
    }
    offset += index_size;

    if (digest_fn == NULL) {
        free(entries);
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_DIGEST_FAILED,
            offset
        );
    }

    for (entry_index = 0U; entry_index < entry_count; entry_index += 1U) {
        uint64_t raw_path_size = 0U;
        uint64_t raw_content_size = 0U;
        size_t path_size = 0U;
        size_t content_size = 0U;
        unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES];

        if (!pchsi_read_u64(stream, stream_size, &offset, &raw_path_size)) {
            free(entries);
            return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
        }
        if (!pchsi_u64_to_size(raw_path_size, &path_size)) {
            free(entries);
            return pchsi_set_error(error, PCHSI_EVIDENCE_PATH_MISMATCH, offset);
        }
        if (offset > stream_size || path_size > stream_size - offset) {
            free(entries);
            return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
        }
        if (
            path_size != entries[entry_index].path_size
            || memcmp(
                stream + offset,
                entries[entry_index].path,
                path_size
            ) != 0
        ) {
            free(entries);
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_PATH_MISMATCH,
                offset
            );
        }
        offset += path_size;

        if (!pchsi_read_u64(stream, stream_size, &offset, &raw_content_size)) {
            free(entries);
            return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
        }
        if (!pchsi_u64_to_size(raw_content_size, &content_size)) {
            free(entries);
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_CONTENT_LENGTH_MISMATCH,
                offset
            );
        }
        if (content_size != entries[entry_index].content_size) {
            free(entries);
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_CONTENT_LENGTH_MISMATCH,
                offset
            );
        }
        if (offset > stream_size || content_size > stream_size - offset) {
            free(entries);
            return pchsi_set_error(error, PCHSI_EVIDENCE_TRUNCATED, offset);
        }

        if (
            digest_fn(
                stream + offset,
                content_size,
                digest,
                digest_context
            ) != 0
        ) {
            free(entries);
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_DIGEST_FAILED,
                offset
            );
        }
        if (
            memcmp(
                digest,
                entries[entry_index].digest,
                PCHSI_EVIDENCE_DIGEST_BYTES
            ) != 0
        ) {
            free(entries);
            return pchsi_set_error(
                error,
                PCHSI_EVIDENCE_CONTENT_DIGEST_MISMATCH,
                offset
            );
        }
        offset += content_size;
    }

    free(entries);

    if (offset != stream_size) {
        return pchsi_set_error(
            error,
            PCHSI_EVIDENCE_TRAILING_DATA,
            offset
        );
    }

    return PCHSI_EVIDENCE_OK;
}

const char *pchsi_evidence_status_name(enum pchsi_evidence_status status)
{
    switch (status) {
        case PCHSI_EVIDENCE_OK:
            return "OK";
        case PCHSI_EVIDENCE_INVALID_MAGIC:
            return "INVALID_MAGIC";
        case PCHSI_EVIDENCE_TRUNCATED:
            return "TRUNCATED";
        case PCHSI_EVIDENCE_TRAILING_DATA:
            return "TRAILING_DATA";
        case PCHSI_EVIDENCE_ENTRY_COUNT_EXCEEDED:
            return "ENTRY_COUNT_EXCEEDED";
        case PCHSI_EVIDENCE_INDEX_TOO_LARGE:
            return "INDEX_TOO_LARGE";
        case PCHSI_EVIDENCE_CONTENT_TOO_LARGE:
            return "CONTENT_TOO_LARGE";
        case PCHSI_EVIDENCE_STREAM_TOO_LARGE:
            return "STREAM_TOO_LARGE";
        case PCHSI_EVIDENCE_INVALID_PATH:
            return "INVALID_PATH";
        case PCHSI_EVIDENCE_DUPLICATE_PATH:
            return "DUPLICATE_PATH";
        case PCHSI_EVIDENCE_INDEX_NOT_SORTED:
            return "INDEX_NOT_SORTED";
        case PCHSI_EVIDENCE_INDEX_LENGTH_MISMATCH:
            return "INDEX_LENGTH_MISMATCH";
        case PCHSI_EVIDENCE_PATH_MISMATCH:
            return "PATH_MISMATCH";
        case PCHSI_EVIDENCE_CONTENT_LENGTH_MISMATCH:
            return "CONTENT_LENGTH_MISMATCH";
        case PCHSI_EVIDENCE_CONTENT_DIGEST_MISMATCH:
            return "CONTENT_DIGEST_MISMATCH";
        case PCHSI_EVIDENCE_ALLOCATION_FAILED:
            return "ALLOCATION_FAILED";
        case PCHSI_EVIDENCE_DIGEST_FAILED:
            return "DIGEST_FAILED";
    }

    return "UNKNOWN";
}
static int pchsi_evidence_expected_name(const char *name)
{
    return (
        strcmp(name, "semantic_evidence.json") == 0
        || strcmp(name, "local_evidence.json") == 0
        || strcmp(name, "local_evidence.json.sha256") == 0
    );
}

static int pchsi_evidence_compare_tree_entries(
    const void *left_pointer,
    const void *right_pointer
)
{
    const struct pchsi_evidence_tree_entry *left = left_pointer;
    const struct pchsi_evidence_tree_entry *right = right_pointer;

    return strcmp(left->path, right->path);
}

static int pchsi_evidence_hex_value(unsigned char byte)
{
    if (byte >= (unsigned char)'0' && byte <= (unsigned char)'9') {
        return (int)(byte - (unsigned char)'0');
    }
    if (byte >= (unsigned char)'a' && byte <= (unsigned char)'f') {
        return (int)(byte - (unsigned char)'a') + 10;
    }
    return -1;
}

static int pchsi_evidence_parse_local_sidecar(
    const unsigned char *content,
    size_t content_size,
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES]
)
{
    static const unsigned char SUFFIX[] =
        "  local_evidence.json\n";
    size_t index = 0U;

    if (
        content == NULL
        || digest == NULL
        || content_size
            != (64U + sizeof(SUFFIX) - 1U)
        || memcmp(
            content + 64U,
            SUFFIX,
            sizeof(SUFFIX) - 1U
        ) != 0
    ) {
        return 0;
    }

    for (index = 0U; index < PCHSI_EVIDENCE_DIGEST_BYTES; index += 1U) {
        int high = pchsi_evidence_hex_value(content[index * 2U]);
        int low = pchsi_evidence_hex_value(content[index * 2U + 1U]);

        if (high < 0 || low < 0) {
            return 0;
        }

        digest[index] = (unsigned char)(
            ((unsigned int)high << 4U)
            | (unsigned int)low
        );
    }

    return 1;
}

static enum pchsi_evidence_tree_status pchsi_evidence_read_file(
    int directory_fd,
    const char *name,
    uint64_t expected_size,
    const struct pchsi_system_ops *operations,
    unsigned char **content,
    size_t *content_size
)
{
    int file_descriptor = -1;
    unsigned char *buffer = NULL;
    size_t size = 0U;
    size_t offset = 0U;

    if (
        expected_size > (uint64_t)SIZE_MAX
        || content == NULL
        || content_size == NULL
    ) {
        return PCHSI_EVIDENCE_TREE_SINGLE_FILE_TOO_LARGE;
    }

    size = (size_t)expected_size;
    buffer = malloc(size == 0U ? 1U : size);

    if (buffer == NULL) {
        return PCHSI_EVIDENCE_TREE_ALLOCATION_FAILED;
    }

    file_descriptor = operations->openat_fn(
        operations->context,
        directory_fd,
        name,
        O_RDONLY | O_CLOEXEC | O_NOFOLLOW,
        0U
    );

    if (file_descriptor < 0) {
        free(buffer);
        return PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED;
    }

    while (offset < size) {
        ssize_t count = operations->read_fn(
            operations->context,
            file_descriptor,
            buffer + offset,
            size - offset
        );

        if (count <= 0) {
            (void)operations->close_fn(
                operations->context,
                file_descriptor
            );
            free(buffer);
            return PCHSI_EVIDENCE_TREE_FILE_READ_FAILED;
        }

        offset += (size_t)count;
    }

    {
        unsigned char extra = 0U;
        ssize_t count = operations->read_fn(
            operations->context,
            file_descriptor,
            &extra,
            1U
        );

        if (count != 0) {
            (void)operations->close_fn(
                operations->context,
                file_descriptor
            );
            free(buffer);
            return PCHSI_EVIDENCE_TREE_FILE_READ_FAILED;
        }
    }

    if (
        operations->close_fn(
            operations->context,
            file_descriptor
        ) != 0
    ) {
        free(buffer);
        return PCHSI_EVIDENCE_TREE_FILE_READ_FAILED;
    }

    *content = buffer;
    *content_size = size;
    return PCHSI_EVIDENCE_TREE_OK;
}

enum pchsi_evidence_tree_status pchsi_validate_evidence_tree(
    int evidence_directory_fd,
    const struct pchsi_evidence_limits *limits,
    struct pchsi_evidence_index *index,
    const struct pchsi_system_ops *system_operations,
    const struct pchsi_evidence_content_ops *content_operations
)
{
    int duplicate_fd = -1;
    DIR *directory = NULL;
    struct dirent *entry = NULL;
    size_t count = 0U;
    uint64_t total_bytes = UINT64_C(0);
    unsigned char local_digest[PCHSI_EVIDENCE_DIGEST_BYTES];
    unsigned char sidecar_digest[PCHSI_EVIDENCE_DIGEST_BYTES];
    int have_local_digest = 0;
    int have_sidecar_digest = 0;

    if (
        evidence_directory_fd < 0
        || limits == NULL
        || index == NULL
        || system_operations == NULL
        || content_operations == NULL
        || content_operations->validate_json_fn == NULL
        || content_operations->sha256_fn == NULL
        || limits->maximum_files != PCHSI_EVIDENCE_EXPECTED_FILE_COUNT
        || limits->maximum_files > PCHSI_EVIDENCE_TREE_MAX_FILES
        || limits->maximum_directory_depth != 1U
    ) {
        return PCHSI_EVIDENCE_TREE_INVALID_ARGUMENT;
    }

    memset(index, 0, sizeof(*index));

    duplicate_fd = system_operations->openat_fn(
        system_operations->context,
        evidence_directory_fd,
        ".",
        O_RDONLY | O_DIRECTORY | O_CLOEXEC,
        0U
    );

    if (duplicate_fd < 0) {
        return PCHSI_EVIDENCE_TREE_DIRECTORY_OPEN_FAILED;
    }

    directory = fdopendir(duplicate_fd);

    if (directory == NULL) {
        (void)system_operations->close_fn(
            system_operations->context,
            duplicate_fd
        );
        return PCHSI_EVIDENCE_TREE_DIRECTORY_OPEN_FAILED;
    }

    errno = 0;

    while ((entry = readdir(directory)) != NULL) {
        struct stat status;
        struct pchsi_evidence_tree_entry *tree_entry = NULL;
        unsigned char *content = NULL;
        size_t content_size = 0U;
        enum pchsi_evidence_tree_status read_status;
        size_t name_size = 0U;

        if (
            strcmp(entry->d_name, ".") == 0
            || strcmp(entry->d_name, "..") == 0
        ) {
            continue;
        }

        if (!pchsi_evidence_expected_name(entry->d_name)) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH;
        }

        if (count >= limits->maximum_files) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_TOO_MANY_FILES;
        }

        if (
            system_operations->fstatat_fn(
                system_operations->context,
                evidence_directory_fd,
                entry->d_name,
                &status,
                AT_SYMLINK_NOFOLLOW
            ) != 0
        ) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED;
        }

        if (!S_ISREG(status.st_mode)) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_NON_REGULAR_FILE;
        }

        if (status.st_nlink != (nlink_t)1) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_HARDLINK_REJECTED;
        }

        if (
            status.st_size < (off_t)0
            || (uint64_t)status.st_size
                > limits->maximum_single_file_bytes
        ) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_SINGLE_FILE_TOO_LARGE;
        }

        if (
            (uint64_t)status.st_size
                > limits->maximum_total_bytes
            || total_bytes
                > limits->maximum_total_bytes
                    - (uint64_t)status.st_size
        ) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_TOTAL_TOO_LARGE;
        }

        tree_entry = &index->entries[count];
        name_size = strlen(entry->d_name);

        if (name_size > PCHSI_EVIDENCE_TREE_PATH_BYTES) {
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH;
        }

        memcpy(tree_entry->path, entry->d_name, name_size + 1U);
        tree_entry->path_size = name_size;
        tree_entry->content_size = (uint64_t)status.st_size;

        read_status = pchsi_evidence_read_file(
            evidence_directory_fd,
            entry->d_name,
            tree_entry->content_size,
            system_operations,
            &content,
            &content_size
        );

        if (read_status != PCHSI_EVIDENCE_TREE_OK) {
            (void)closedir(directory);
            return read_status;
        }

        if (
            content_operations->sha256_fn(
                content_operations->context,
                content,
                content_size,
                tree_entry->digest
            ) != 0
        ) {
            free(content);
            (void)closedir(directory);
            return PCHSI_EVIDENCE_TREE_DIGEST_MISMATCH;
        }

        if (
            strcmp(entry->d_name, "semantic_evidence.json") == 0
            || strcmp(entry->d_name, "local_evidence.json") == 0
        ) {
            if (
                content_operations->validate_json_fn(
                    content_operations->context,
                    content,
                    content_size
                ) != 0
            ) {
                free(content);
                (void)closedir(directory);
                return PCHSI_EVIDENCE_TREE_JSON_INVALID;
            }
        }

        if (strcmp(entry->d_name, "local_evidence.json") == 0) {
            memcpy(
                local_digest,
                tree_entry->digest,
                sizeof(local_digest)
            );
            have_local_digest = 1;
        }

        if (
            strcmp(
                entry->d_name,
                "local_evidence.json.sha256"
            ) == 0
        ) {
            if (
                !pchsi_evidence_parse_local_sidecar(
                    content,
                    content_size,
                    sidecar_digest
                )
            ) {
                free(content);
                (void)closedir(directory);
                return PCHSI_EVIDENCE_TREE_SIDECAR_INVALID;
            }
            have_sidecar_digest = 1;
        }

        free(content);
        total_bytes += tree_entry->content_size;
        count += 1U;
        errno = 0;
    }

    if (errno != 0) {
        (void)closedir(directory);
        return PCHSI_EVIDENCE_TREE_DIRECTORY_READ_FAILED;
    }

    if (closedir(directory) != 0) {
        return PCHSI_EVIDENCE_TREE_DIRECTORY_READ_FAILED;
    }

    if (count != PCHSI_EVIDENCE_EXPECTED_FILE_COUNT) {
        return PCHSI_EVIDENCE_TREE_TOO_MANY_FILES;
    }

    qsort(
        index->entries,
        count,
        sizeof(index->entries[0]),
        pchsi_evidence_compare_tree_entries
    );

    if (
        strcmp(
            index->entries[0].path,
            "local_evidence.json"
        ) != 0
        || strcmp(
            index->entries[1].path,
            "local_evidence.json.sha256"
        ) != 0
        || strcmp(
            index->entries[2].path,
            "semantic_evidence.json"
        ) != 0
    ) {
        return PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH;
    }

    if (
        !have_local_digest
        || !have_sidecar_digest
        || memcmp(
            local_digest,
            sidecar_digest,
            sizeof(local_digest)
        ) != 0
    ) {
        return PCHSI_EVIDENCE_TREE_DIGEST_MISMATCH;
    }

    index->count = count;
    index->total_bytes = total_bytes;
    return PCHSI_EVIDENCE_TREE_OK;
}

enum pchsi_evidence_tree_status
pchsi_publish_evidence_file_no_clobber(
    int staging_directory_fd,
    const char *staging_name,
    int output_directory_fd,
    const char *final_name,
    const struct pchsi_system_ops *system_operations
)
{
    int staging_file_descriptor = -1;

    if (
        staging_directory_fd < 0
        || output_directory_fd < 0
        || staging_name == NULL
        || final_name == NULL
        || system_operations == NULL
        || !pchsi_evidence_expected_name(final_name)
    ) {
        return PCHSI_EVIDENCE_TREE_INVALID_ARGUMENT;
    }

    staging_file_descriptor = system_operations->openat_fn(
        system_operations->context,
        staging_directory_fd,
        staging_name,
        O_RDONLY | O_CLOEXEC | O_NOFOLLOW,
        0U
    );

    if (staging_file_descriptor < 0) {
        return PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED;
    }

    if (
        system_operations->fsync_fn(
            system_operations->context,
            staging_file_descriptor
        ) != 0
    ) {
        (void)system_operations->close_fn(
            system_operations->context,
            staging_file_descriptor
        );
        return PCHSI_EVIDENCE_TREE_FSYNC_FAILED;
    }

    if (
        system_operations->close_fn(
            system_operations->context,
            staging_file_descriptor
        ) != 0
    ) {
        return PCHSI_EVIDENCE_TREE_FSYNC_FAILED;
    }

    if (
        system_operations->renameat2_fn(
            system_operations->context,
            staging_directory_fd,
            staging_name,
            output_directory_fd,
            final_name,
            RENAME_NOREPLACE
        ) != 0
    ) {
        if (errno == EEXIST) {
            return PCHSI_EVIDENCE_TREE_TARGET_EXISTS;
        }
        return PCHSI_EVIDENCE_TREE_PUBLICATION_FAILED;
    }

    if (
        system_operations->fsync_fn(
            system_operations->context,
            output_directory_fd
        ) != 0
    ) {
        return PCHSI_EVIDENCE_TREE_FSYNC_FAILED;
    }

    return PCHSI_EVIDENCE_TREE_OK;
}

const char *pchsi_evidence_tree_status_name(
    enum pchsi_evidence_tree_status status
)
{
    switch (status) {
        case PCHSI_EVIDENCE_TREE_OK:
            return "PCHSI_EVIDENCE_TREE_OK";
        case PCHSI_EVIDENCE_TREE_INVALID_ARGUMENT:
            return "PCHSI_EVIDENCE_TREE_INVALID_ARGUMENT";
        case PCHSI_EVIDENCE_TREE_DIRECTORY_OPEN_FAILED:
            return "PCHSI_EVIDENCE_TREE_DIRECTORY_OPEN_FAILED";
        case PCHSI_EVIDENCE_TREE_DIRECTORY_READ_FAILED:
            return "PCHSI_EVIDENCE_TREE_DIRECTORY_READ_FAILED";
        case PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH:
            return "PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH";
        case PCHSI_EVIDENCE_TREE_DUPLICATE_PATH:
            return "PCHSI_EVIDENCE_TREE_DUPLICATE_PATH";
        case PCHSI_EVIDENCE_TREE_NON_REGULAR_FILE:
            return "PCHSI_EVIDENCE_TREE_NON_REGULAR_FILE";
        case PCHSI_EVIDENCE_TREE_HARDLINK_REJECTED:
            return "PCHSI_EVIDENCE_TREE_HARDLINK_REJECTED";
        case PCHSI_EVIDENCE_TREE_TOO_MANY_FILES:
            return "PCHSI_EVIDENCE_TREE_TOO_MANY_FILES";
        case PCHSI_EVIDENCE_TREE_SINGLE_FILE_TOO_LARGE:
            return "PCHSI_EVIDENCE_TREE_SINGLE_FILE_TOO_LARGE";
        case PCHSI_EVIDENCE_TREE_TOTAL_TOO_LARGE:
            return "PCHSI_EVIDENCE_TREE_TOTAL_TOO_LARGE";
        case PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED:
            return "PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED";
        case PCHSI_EVIDENCE_TREE_FILE_READ_FAILED:
            return "PCHSI_EVIDENCE_TREE_FILE_READ_FAILED";
        case PCHSI_EVIDENCE_TREE_JSON_INVALID:
            return "PCHSI_EVIDENCE_TREE_JSON_INVALID";
        case PCHSI_EVIDENCE_TREE_SIDECAR_INVALID:
            return "PCHSI_EVIDENCE_TREE_SIDECAR_INVALID";
        case PCHSI_EVIDENCE_TREE_DIGEST_MISMATCH:
            return "PCHSI_EVIDENCE_TREE_DIGEST_MISMATCH";
        case PCHSI_EVIDENCE_TREE_ALLOCATION_FAILED:
            return "PCHSI_EVIDENCE_TREE_ALLOCATION_FAILED";
        case PCHSI_EVIDENCE_TREE_PUBLICATION_FAILED:
            return "PCHSI_EVIDENCE_TREE_PUBLICATION_FAILED";
        case PCHSI_EVIDENCE_TREE_TARGET_EXISTS:
            return "PCHSI_EVIDENCE_TREE_TARGET_EXISTS";
        case PCHSI_EVIDENCE_TREE_FSYNC_FAILED:
            return "PCHSI_EVIDENCE_TREE_FSYNC_FAILED";
    }

    return "PCHSI_EVIDENCE_TREE_UNKNOWN";
}
