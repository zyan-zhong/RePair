#include "pchsi_s1/mount_contract.h"

#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_file(const char *path, size_t *size)
{
    FILE *stream = fopen(path, "rb");
    long length;
    char *buffer;

    assert(stream != NULL);
    assert(fseek(stream, 0L, SEEK_END) == 0);
    length = ftell(stream);
    assert(length >= 0L);
    assert(fseek(stream, 0L, SEEK_SET) == 0);

    buffer = malloc((size_t)length + 1U);
    assert(buffer != NULL);
    assert(fread(buffer, 1U, (size_t)length, stream) == (size_t)length);
    buffer[length] = '\0';
    assert(fclose(stream) == 0);
    *size = (size_t)length;
    return buffer;
}

static void test_valid_three_class_contract(void)
{
    struct pchsi_mountinfo mounts;
    size_t size = 0U;
    char *text = read_file(
        "tests/security/fixtures/mountinfo_valid.txt",
        &size
    );

    assert(pchsi_mountinfo_parse(text, size, &mounts) == PCHSI_STATUS_OK);
    assert(mounts.count == 5U);
    assert(
        pchsi_verify_mount_contract(PCHSI_MOUNT_RUNTIME, &mounts)
        == PCHSI_STATUS_OK
    );
    assert(
        pchsi_verify_mount_contract(PCHSI_MOUNT_REPOSITORY, &mounts)
        == PCHSI_STATUS_OK
    );
    assert(
        pchsi_verify_mount_contract(PCHSI_MOUNT_DATASET, &mounts)
        == PCHSI_STATUS_OK
    );
    free(text);
}

static void test_writable_nested_mount_fails_closed(void)
{
    struct pchsi_mountinfo mounts;
    size_t size = 0U;
    char *text = read_file(
        "tests/security/fixtures/mountinfo_writable_nested.txt",
        &size
    );

    assert(pchsi_mountinfo_parse(text, size, &mounts) == PCHSI_STATUS_OK);
    assert(
        pchsi_verify_mount_contract(PCHSI_MOUNT_REPOSITORY, &mounts)
        == PCHSI_STATUS_MOUNT_WRITABLE_DESCENDANT
    );
    free(text);
}

static void test_fourth_host_backed_class_is_invalid(void)
{
    const char *target = (const char *)1;
    assert(
        pchsi_mount_class_target(
            (enum pchsi_mount_class)3,
            &target
        ) == PCHSI_STATUS_MOUNT_CLASS_INVALID
    );
    assert(target == NULL);
}

static void test_bootstrap_and_collector_are_not_mount_classes(void)
{
    const char *target = NULL;
    assert(
        pchsi_mount_class_target(PCHSI_MOUNT_RUNTIME, &target)
        == PCHSI_STATUS_OK
    );
    assert(strcmp(target, "/bootstrap") != 0);
    assert(strcmp(target, "/collector") != 0);
}

static void test_malformed_mountinfo_is_rejected(void)
{
    struct pchsi_mountinfo mounts;
    const char malformed[] = "100 1 missing separator\n";

    assert(
        pchsi_mountinfo_parse(
            malformed,
            sizeof(malformed) - 1U,
            &mounts
        ) == PCHSI_STATUS_MOUNT_PARSE_FAILED
    );
}

int main(void)
{
    test_valid_three_class_contract();
    test_writable_nested_mount_fails_closed();
    test_fourth_host_backed_class_is_invalid();
    test_bootstrap_and_collector_are_not_mount_classes();
    test_malformed_mountinfo_is_rejected();
    return 0;
}
