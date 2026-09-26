#include "pchsi_s1/mount_contract.h"

#include <stdlib.h>
#include <string.h>

static int pchsi_option_present(
    const char *options,
    const char *expected
)
{
    const char *cursor = options;
    size_t expected_size = strlen(expected);

    while (*cursor != '\0') {
        const char *end = strchr(cursor, ',');
        size_t size = end == NULL ? strlen(cursor) : (size_t)(end - cursor);

        if (size == expected_size && memcmp(cursor, expected, size) == 0) {
            return 1;
        }

        if (end == NULL) {
            break;
        }
        cursor = end + 1;
    }

    return 0;
}

static int pchsi_parse_unsigned(
    const char *token,
    unsigned int *value
)
{
    char *end = NULL;
    unsigned long parsed;

    if (token == NULL || token[0] == '\0') {
        return 0;
    }

    parsed = strtoul(token, &end, 10);

    if (end == NULL || *end != '\0' || parsed > 0xFFFFFFFFUL) {
        return 0;
    }

    *value = (unsigned int)parsed;
    return 1;
}

static int pchsi_path_is_descendant_or_equal(
    const char *path,
    const char *root
)
{
    size_t root_size = strlen(root);

    if (strcmp(path, root) == 0) {
        return 1;
    }

    return (
        strncmp(path, root, root_size) == 0
        && path[root_size] == '/'
    );
}

enum pchsi_status pchsi_mountinfo_parse(
    const char *text,
    size_t size,
    struct pchsi_mountinfo *mounts
)
{
    char *copy;
    char *line_save = NULL;
    char *line;

    if (text == NULL || mounts == NULL) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    copy = malloc(size + 1U);
    if (copy == NULL) {
        return PCHSI_STATUS_ALLOCATION_FAILED;
    }

    memcpy(copy, text, size);
    copy[size] = '\0';
    mounts->count = 0U;

    line = strtok_r(copy, "\n", &line_save);

    while (line != NULL) {
        char *field_save = NULL;
        char *fields[6] = {NULL, NULL, NULL, NULL, NULL, NULL};
        size_t field_count = 0U;
        char *token;
        char *separator;
        struct pchsi_mountinfo_entry *entry;
        size_t mount_point_size;

        if (mounts->count >= PCHSI_MOUNTINFO_MAX_ENTRIES) {
            free(copy);
            return PCHSI_STATUS_MOUNT_PARSE_FAILED;
        }

        separator = strstr(line, " - ");
        if (separator == NULL) {
            free(copy);
            return PCHSI_STATUS_MOUNT_PARSE_FAILED;
        }
        *separator = '\0';

        token = strtok_r(line, " ", &field_save);
        while (token != NULL && field_count < 6U) {
            fields[field_count] = token;
            field_count += 1U;
            token = strtok_r(NULL, " ", &field_save);
        }

        if (field_count < 6U) {
            free(copy);
            return PCHSI_STATUS_MOUNT_PARSE_FAILED;
        }

        entry = &mounts->entries[mounts->count];
        memset(entry, 0, sizeof(*entry));

        if (
            !pchsi_parse_unsigned(fields[0], &entry->mount_id)
            || !pchsi_parse_unsigned(fields[1], &entry->parent_id)
        ) {
            free(copy);
            return PCHSI_STATUS_MOUNT_PARSE_FAILED;
        }

        mount_point_size = strlen(fields[4]);
        if (
            mount_point_size == 0U
            || mount_point_size > PCHSI_MOUNTINFO_PATH_MAX_BYTES
            || strchr(fields[4], '\\') != NULL
        ) {
            free(copy);
            return PCHSI_STATUS_MOUNT_PARSE_FAILED;
        }

        memcpy(entry->mount_point, fields[4], mount_point_size + 1U);
        entry->read_only = pchsi_option_present(fields[5], "ro");
        entry->nosuid = pchsi_option_present(fields[5], "nosuid");
        entry->nodev = pchsi_option_present(fields[5], "nodev");
        entry->noexec = pchsi_option_present(fields[5], "noexec");
        mounts->count += 1U;

        line = strtok_r(NULL, "\n", &line_save);
    }

    free(copy);
    return mounts->count == 0U
        ? PCHSI_STATUS_MOUNT_PARSE_FAILED
        : PCHSI_STATUS_OK;
}

enum pchsi_status pchsi_mount_class_target(
    enum pchsi_mount_class mount_class,
    const char **target
)
{
    if (target == NULL) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    switch (mount_class) {
        case PCHSI_MOUNT_RUNTIME:
            *target = "/runtime";
            return PCHSI_STATUS_OK;
        case PCHSI_MOUNT_REPOSITORY:
            *target = "/input/repo";
            return PCHSI_STATUS_OK;
        case PCHSI_MOUNT_DATASET:
            *target = "/input/dataset";
            return PCHSI_STATUS_OK;
        default:
            *target = NULL;
            return PCHSI_STATUS_MOUNT_CLASS_INVALID;
    }
}

enum pchsi_status pchsi_verify_mount_contract(
    enum pchsi_mount_class mount_class,
    const struct pchsi_mountinfo *mounts
)
{
    const char *target = NULL;
    size_t index;
    int found = 0;
    enum pchsi_status status;

    if (mounts == NULL) {
        return PCHSI_STATUS_INVALID_ARGUMENT;
    }

    status = pchsi_mount_class_target(mount_class, &target);
    if (status != PCHSI_STATUS_OK) {
        return status;
    }

    for (index = 0U; index < mounts->count; index += 1U) {
        const struct pchsi_mountinfo_entry *entry = &mounts->entries[index];

        if (!pchsi_path_is_descendant_or_equal(entry->mount_point, target)) {
            continue;
        }

        if (strcmp(entry->mount_point, target) == 0) {
            found = 1;
        }

        if (!entry->read_only) {
            return PCHSI_STATUS_MOUNT_WRITABLE_DESCENDANT;
        }

        if (!entry->nosuid || !entry->nodev) {
            return PCHSI_STATUS_MOUNT_CONTRACT_FAILED;
        }

        if (
            mount_class != PCHSI_MOUNT_RUNTIME
            && !entry->noexec
        ) {
            return PCHSI_STATUS_MOUNT_CONTRACT_FAILED;
        }

        if (
            mount_class == PCHSI_MOUNT_RUNTIME
            && strcmp(entry->mount_point, target) == 0
            && entry->noexec
        ) {
            return PCHSI_STATUS_MOUNT_CONTRACT_FAILED;
        }
    }

    return found
        ? PCHSI_STATUS_OK
        : PCHSI_STATUS_MOUNT_CONTRACT_FAILED;
}
