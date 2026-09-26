#ifndef PCHSI_S1_EVIDENCE_H
#define PCHSI_S1_EVIDENCE_H

#include "pchsi_s1/system_ops.h"

#include <stddef.h>
#include <stdint.h>

#define PCHSI_EVIDENCE_DIGEST_BYTES 32U
#define PCHSI_EVIDENCE_MAX_ENTRIES 1024U
#define PCHSI_EVIDENCE_MAX_INDEX_BYTES (16U * 1024U * 1024U)
#define PCHSI_EVIDENCE_MAX_CONTENT_BYTES (16U * 1024U * 1024U)
#define PCHSI_EVIDENCE_MAX_STREAM_BYTES (64U * 1024U * 1024U)

enum pchsi_evidence_status {
    PCHSI_EVIDENCE_OK = 0,
    PCHSI_EVIDENCE_INVALID_MAGIC,
    PCHSI_EVIDENCE_TRUNCATED,
    PCHSI_EVIDENCE_TRAILING_DATA,
    PCHSI_EVIDENCE_ENTRY_COUNT_EXCEEDED,
    PCHSI_EVIDENCE_INDEX_TOO_LARGE,
    PCHSI_EVIDENCE_CONTENT_TOO_LARGE,
    PCHSI_EVIDENCE_STREAM_TOO_LARGE,
    PCHSI_EVIDENCE_INVALID_PATH,
    PCHSI_EVIDENCE_DUPLICATE_PATH,
    PCHSI_EVIDENCE_INDEX_NOT_SORTED,
    PCHSI_EVIDENCE_INDEX_LENGTH_MISMATCH,
    PCHSI_EVIDENCE_PATH_MISMATCH,
    PCHSI_EVIDENCE_CONTENT_LENGTH_MISMATCH,
    PCHSI_EVIDENCE_CONTENT_DIGEST_MISMATCH,
    PCHSI_EVIDENCE_ALLOCATION_FAILED,
    PCHSI_EVIDENCE_DIGEST_FAILED
};

struct pchsi_evidence_error {
    enum pchsi_evidence_status status;
    size_t offset;
};

typedef int (*pchsi_evidence_digest_fn)(
    const unsigned char *content,
    size_t content_size,
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES],
    void *context
);

enum pchsi_evidence_status pchsi_evidence_validate(
    const unsigned char *stream,
    size_t stream_size,
    pchsi_evidence_digest_fn digest_fn,
    void *digest_context,
    struct pchsi_evidence_error *error
);

const char *pchsi_evidence_status_name(enum pchsi_evidence_status status);
#define PCHSI_EVIDENCE_TREE_MAX_FILES 16U
#define PCHSI_EVIDENCE_TREE_PATH_BYTES 512U
#define PCHSI_EVIDENCE_EXPECTED_FILE_COUNT 3U

enum pchsi_evidence_tree_status {
    PCHSI_EVIDENCE_TREE_OK = 0,
    PCHSI_EVIDENCE_TREE_INVALID_ARGUMENT,
    PCHSI_EVIDENCE_TREE_DIRECTORY_OPEN_FAILED,
    PCHSI_EVIDENCE_TREE_DIRECTORY_READ_FAILED,
    PCHSI_EVIDENCE_TREE_UNEXPECTED_PATH,
    PCHSI_EVIDENCE_TREE_DUPLICATE_PATH,
    PCHSI_EVIDENCE_TREE_NON_REGULAR_FILE,
    PCHSI_EVIDENCE_TREE_HARDLINK_REJECTED,
    PCHSI_EVIDENCE_TREE_TOO_MANY_FILES,
    PCHSI_EVIDENCE_TREE_SINGLE_FILE_TOO_LARGE,
    PCHSI_EVIDENCE_TREE_TOTAL_TOO_LARGE,
    PCHSI_EVIDENCE_TREE_FILE_OPEN_FAILED,
    PCHSI_EVIDENCE_TREE_FILE_READ_FAILED,
    PCHSI_EVIDENCE_TREE_JSON_INVALID,
    PCHSI_EVIDENCE_TREE_SIDECAR_INVALID,
    PCHSI_EVIDENCE_TREE_DIGEST_MISMATCH,
    PCHSI_EVIDENCE_TREE_ALLOCATION_FAILED,
    PCHSI_EVIDENCE_TREE_PUBLICATION_FAILED,
    PCHSI_EVIDENCE_TREE_TARGET_EXISTS,
    PCHSI_EVIDENCE_TREE_FSYNC_FAILED
};

struct pchsi_evidence_limits {
    size_t maximum_files;
    uint64_t maximum_total_bytes;
    uint64_t maximum_single_file_bytes;
    size_t maximum_directory_depth;
};

struct pchsi_evidence_tree_entry {
    char path[PCHSI_EVIDENCE_TREE_PATH_BYTES + 1U];
    size_t path_size;
    uint64_t content_size;
    unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES];
};

struct pchsi_evidence_index {
    size_t count;
    uint64_t total_bytes;
    struct pchsi_evidence_tree_entry
        entries[PCHSI_EVIDENCE_TREE_MAX_FILES];
};

struct pchsi_evidence_content_ops {
    void *context;
    int (*validate_json_fn)(
        void *context,
        const unsigned char *data,
        size_t size
    );
    int (*sha256_fn)(
        void *context,
        const unsigned char *data,
        size_t size,
        unsigned char digest[PCHSI_EVIDENCE_DIGEST_BYTES]
    );
};

enum pchsi_evidence_tree_status pchsi_validate_evidence_tree(
    int evidence_directory_fd,
    const struct pchsi_evidence_limits *limits,
    struct pchsi_evidence_index *index,
    const struct pchsi_system_ops *system_operations,
    const struct pchsi_evidence_content_ops *content_operations
);

enum pchsi_evidence_tree_status
pchsi_publish_evidence_file_no_clobber(
    int staging_directory_fd,
    const char *staging_name,
    int output_directory_fd,
    const char *final_name,
    const struct pchsi_system_ops *system_operations
);

const char *pchsi_evidence_tree_status_name(
    enum pchsi_evidence_tree_status status
);

#endif
