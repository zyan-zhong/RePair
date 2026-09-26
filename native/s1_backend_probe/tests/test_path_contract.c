#include "pchsi_s1/path_contract.h"

#include <assert.h>
#include <stddef.h>
#include <string.h>

void pchsi_test_paths(void)
{
    struct pchsi_path_parts parts = {0};
    const unsigned char valid[] = "logs/probe-P7.42.txt";
    const unsigned char absolute[] = "/absolute";
    const unsigned char double_slash[] = "a//b";
    unsigned char non_ascii[] = {'c', 'a', 'f', 0xC3U, 0xA9U};

    assert(
        pchsi_validate_evidence_path(
            valid,
            sizeof(valid) - 1U,
            &parts
        ) == PCHSI_PATH_OK
    );
    assert(parts.count == 2U);
    assert(parts.parts[0].size == 4U);
    assert(parts.parts[1].size == strlen("probe-P7.42.txt"));

    assert(
        pchsi_validate_evidence_path(
            absolute,
            sizeof(absolute) - 1U,
            NULL
        ) == PCHSI_PATH_ABSOLUTE
    );
    assert(
        pchsi_validate_evidence_path(
            double_slash,
            sizeof(double_slash) - 1U,
            NULL
        ) == PCHSI_PATH_EMPTY_SEGMENT
    );
    assert(
        pchsi_validate_evidence_path(
            non_ascii,
            sizeof(non_ascii),
            NULL
        ) == PCHSI_PATH_NON_ASCII
    );
}
