#include "pchsi_s1/common.h"
#include "pchsi_s1/errors.h"

#include <stdio.h>
#include <string.h>

static int describe_backend(void)
{
    (void)printf(
        "design_id=%s\n"
        "backend_id=%s\n"
        "design_commit=%s\n"
        "BACKEND_PROBE_EXECUTION=%s\n",
        PCHSI_S1_DESIGN_ID,
        PCHSI_S1_BACKEND_ID,
        PCHSI_S1_DESIGN_COMMIT,
        PCHSI_S1_EXECUTION_STATUS
    );

    return PCHSI_S1_EXIT_OK;
}

static int print_version(void)
{
    (void)printf(
        "version=%s\n"
        "design_commit=%s\n",
        PCHSI_S1_VERSION,
        PCHSI_S1_DESIGN_COMMIT
    );

    return PCHSI_S1_EXIT_OK;
}

static int reject_execution(void)
{
    (void)fprintf(
        stderr,
        "%s: backend probe execution requires a separately "
        "bound external execution record\n",
        pchsi_s1_execution_not_approved_marker()
    );

    return PCHSI_S1_EXIT_NOT_APPROVED;
}

static int validate_manifest_unavailable(void)
{
    (void)fprintf(
        stderr,
        "PCHSI_MANIFEST_VALIDATION_UNAVAILABLE\n"
    );

    return PCHSI_S1_EXIT_UNAVAILABLE;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        (void)fprintf(
            stderr,
            "usage: %s "
            "{--describe|--version|--validate-manifest|--execute}\n",
            argv[0]
        );
        return PCHSI_S1_EXIT_USAGE;
    }

    if (strcmp(argv[1], "--describe") == 0) {
        return describe_backend();
    }

    if (strcmp(argv[1], "--version") == 0) {
        return print_version();
    }

    if (strcmp(argv[1], "--validate-manifest") == 0) {
        return validate_manifest_unavailable();
    }

    if (strcmp(argv[1], "--execute") == 0) {
        return reject_execution();
    }

    (void)fprintf(stderr, "unknown command: %s\n", argv[1]);
    return PCHSI_S1_EXIT_USAGE;
}
/*
 * Task 13 review marker. Runtime dispatch remains closed until an
 * externally bound execution record is separately approved.
 */
int pchsi_s1_supervisor_execution_is_closed(void)
{
    return 1;
}
