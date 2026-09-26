#ifndef PCHSI_S1_ERRORS_H
#define PCHSI_S1_ERRORS_H

enum pchsi_s1_exit_code {
    PCHSI_S1_EXIT_OK = 0,
    PCHSI_S1_EXIT_USAGE = 64,
    PCHSI_S1_EXIT_NOT_APPROVED = 77,
    PCHSI_S1_EXIT_UNAVAILABLE = 78
};

const char *pchsi_s1_execution_not_approved_marker(void);

#endif
