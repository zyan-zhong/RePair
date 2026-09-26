#ifndef PCHSI_S1_SECCOMP_FILTER_H
#define PCHSI_S1_SECCOMP_FILTER_H

#include <linux/filter.h>
#include <stddef.h>
#include <stdint.h>

#define PCHSI_SECCOMP_MAX_ALLOWLIST 128U
#define PCHSI_SECCOMP_MAX_INSTRUCTIONS \
    (7U + (2U * PCHSI_SECCOMP_MAX_ALLOWLIST))

enum pchsi_seccomp_status {
    PCHSI_SECCOMP_OK = 0,
    PCHSI_SECCOMP_INVALID_ARGUMENT,
    PCHSI_SECCOMP_ARCHITECTURE_INVALID,
    PCHSI_SECCOMP_DEFAULT_ACTION_INVALID,
    PCHSI_SECCOMP_ALLOWLIST_TOO_LARGE,
    PCHSI_SECCOMP_ALLOWLIST_NOT_SORTED,
    PCHSI_SECCOMP_SYSCALL_INVALID,
    PCHSI_SECCOMP_PROGRAM_LENGTH_INVALID,
    PCHSI_SECCOMP_PROGRAM_MISMATCH
};

struct pchsi_seccomp_policy {
    uint32_t audit_architecture;
    uint32_t default_action;
    const int *allowed_syscalls;
    size_t allowed_syscall_count;
};

struct pchsi_bpf_program {
    struct sock_filter instructions[PCHSI_SECCOMP_MAX_INSTRUCTIONS];
    size_t instruction_count;
};

enum pchsi_seccomp_status pchsi_build_seccomp_program(
    const struct pchsi_seccomp_policy *policy,
    struct pchsi_bpf_program *program
);

enum pchsi_seccomp_status pchsi_verify_seccomp_program(
    const struct pchsi_seccomp_policy *policy,
    const struct pchsi_bpf_program *program
);

const char *pchsi_seccomp_status_name(
    enum pchsi_seccomp_status status
);

#endif
