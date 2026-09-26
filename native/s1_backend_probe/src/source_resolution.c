#include "pchsi_s1/source_resolution.h"

#include <fcntl.h>
#include <string.h>

static int pchsi_path_segment_is_dot_or_dotdot(
    const char *start,
    size_t size
)
{
    return (
        (size == 1U && start[0] == '.')
        || (
            size == 2U
            && start[0] == '.'
            && start[1] == '.'
        )
    );
}

enum pchsi_status pchsi_validate_relative_source_path(
    const char *relative_path
)
{
    size_t length;
    size_t index = 0U;
    size_t segment_start = 0U;

    if (relative_path == NULL || relative_path[0] == '\0') {
        return PCHSI_STATUS_SOURCE_PATH_INVALID;
    }

    length = strlen(relative_path);

    if (
        length == 0U
        || length > PCHSI_SOURCE_PATH_MAX_BYTES
        || relative_path[0] == '/'
    ) {
        return PCHSI_STATUS_SOURCE_PATH_INVALID;
    }

    for (index = 0U; index <= length; index += 1U) {
        unsigned char byte = (unsigned char)relative_path[index];

        if (byte == '\\') {
            return PCHSI_STATUS_SOURCE_PATH_INVALID;
        }

        if (byte == '/' || byte == '\0') {
            size_t segment_size = index - segment_start;

            if (
                segment_size == 0U
                || pchsi_path_segment_is_dot_or_dotdot(
                    relative_path + segment_start,
                    segment_size
                )
            ) {
                return PCHSI_STATUS_SOURCE_PATH_INVALID;
            }

            segment_start = index + 1U;
            continue;
        }

        if (byte < 0x20U || byte == 0x7FU) {
            return PCHSI_STATUS_SOURCE_PATH_INVALID;
        }
    }

    return PCHSI_STATUS_OK;
}

static void pchsi_identity_from_stat(
    const struct stat *status,
    struct pchsi_file_identity *identity
)
{
    identity->device = status->st_dev;
    identity->inode = status->st_ino;
    identity->size = status->st_size;
    identity->mode = status->st_mode;
}

enum pchsi_status pchsi_open_source_beneath_repo(
    int repo_dirfd,
    const char *relative_path,
    const struct pchsi_system_ops *operations,
    int *source_fd,
    struct pchsi_file_identity *identity
)
{
    struct pchsi_open_how how = {0};
    struct stat status = {0};
    int opened_fd;

    if (
        repo_dirfd < 0
        || operations == NULL
        || operations->openat2_fn == NULL
        || operations->fstat_fn == NULL
        || operations->close_fn == NULL
        || source_fd == NULL
        || identity == NULL
    ) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    if (
        pchsi_validate_relative_source_path(relative_path)
        != PCHSI_STATUS_OK
    ) {
        return PCHSI_STATUS_SOURCE_PATH_INVALID;
    }

    how.flags = (uint64_t)(
        O_RDONLY
        | O_CLOEXEC
        | O_NOFOLLOW
    );
    how.mode = UINT64_C(0);
    how.resolve = (
        PCHSI_RESOLVE_BENEATH
        | PCHSI_RESOLVE_NO_SYMLINKS
        | PCHSI_RESOLVE_NO_MAGICLINKS
    );

    opened_fd = operations->openat2_fn(
        operations->context,
        repo_dirfd,
        relative_path,
        &how,
        sizeof(how)
    );

    if (opened_fd < 0) {
        return PCHSI_STATUS_SOURCE_OPEN_FAILED;
    }

    if (
        operations->fstat_fn(
            operations->context,
            opened_fd,
            &status
        ) != 0
    ) {
        (void)operations->close_fn(
            operations->context,
            opened_fd
        );
        return PCHSI_STATUS_SOURCE_OPEN_FAILED;
    }

    if (!S_ISREG(status.st_mode)) {
        (void)operations->close_fn(
            operations->context,
            opened_fd
        );
        return PCHSI_STATUS_SOURCE_NOT_REGULAR;
    }

    pchsi_identity_from_stat(&status, identity);
    *source_fd = opened_fd;
    return PCHSI_STATUS_OK;
}

const char *pchsi_status_name(enum pchsi_status status)
{
    switch (status) {
        case PCHSI_STATUS_OK:
            return "ok";
        case PCHSI_STATUS_INVALID_ARGUMENT:
            return "invalid_argument";
        case PCHSI_STATUS_SOURCE_PATH_INVALID:
            return "source_path_invalid";
        case PCHSI_STATUS_SOURCE_OPEN_FAILED:
            return "source_open_failed";
        case PCHSI_STATUS_SOURCE_NOT_REGULAR:
            return "source_not_regular";
        case PCHSI_STATUS_SOURCE_IDENTITY_CHANGED:
            return "source_identity_changed";
        case PCHSI_STATUS_SOURCE_HASH_MISMATCH:
            return "source_hash_mismatch";
        case PCHSI_STATUS_SOURCE_COPY_FAILED:
            return "source_copy_failed";
        case PCHSI_STATUS_SOURCE_SEAL_FAILED:
            return "source_seal_failed";
        case PCHSI_STATUS_MOUNT_PARSE_FAILED:
            return "mount_parse_failed";
        case PCHSI_STATUS_MOUNT_CLASS_INVALID:
            return "mount_class_invalid";
        case PCHSI_STATUS_MOUNT_CONTRACT_FAILED:
            return "mount_contract_failed";
        case PCHSI_STATUS_MOUNT_WRITABLE_DESCENDANT:
            return "mount_writable_descendant";
        case PCHSI_STATUS_ALLOCATION_FAILED:
            return "allocation_failed";
        default:
            return "unknown";
    }
}
