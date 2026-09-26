#ifndef PCHSI_S1_SOURCE_COPY_H
#define PCHSI_S1_SOURCE_COPY_H

#include "pchsi_s1/source_resolution.h"

#include <stddef.h>

#define PCHSI_SOURCE_COPY_BUFFER_BYTES 4096U
#define PCHSI_SOURCE_DIGEST_BYTES 32U

enum pchsi_status pchsi_copy_and_seal_source(
    int source_fd,
    const struct pchsi_file_identity *expected_identity,
    int destination_directory_fd,
    const char *destination_name,
    const unsigned char expected_sha256[PCHSI_SOURCE_DIGEST_BYTES],
    const struct pchsi_system_ops *operations
);

#endif
