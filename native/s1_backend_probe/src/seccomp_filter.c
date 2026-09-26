#include "pchsi_s1/seccomp_filter.h"

#include <linux/audit.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <string.h>

#define PCHSI_X32_SYSCALL_BIT UINT32_C(0x40000000)

static void pchsi_set_statement(
    struct sock_filter *instruction,
    unsigned short code,
    uint32_t value
)
{
    instruction->code = code;
    instruction->jt = 0U;
    instruction->jf = 0U;
    instruction->k = value;
}

static void pchsi_set_jump(
    struct sock_filter *instruction,
    unsigned short code,
    uint32_t value,
    unsigned char jump_true,
    unsigned char jump_false
)
{
    instruction->code = code;
    instruction->jt = jump_true;
    instruction->jf = jump_false;
    instruction->k = value;
}

static enum pchsi_seccomp_status pchsi_validate_policy(
    const struct pchsi_seccomp_policy *policy
)
{
    size_t index = 0U;

    if (policy == NULL) {
        return PCHSI_SECCOMP_INVALID_ARGUMENT;
    }

    if (policy->audit_architecture != (uint32_t)AUDIT_ARCH_X86_64) {
        return PCHSI_SECCOMP_ARCHITECTURE_INVALID;
    }

    if (policy->default_action != (uint32_t)SECCOMP_RET_KILL_PROCESS) {
        return PCHSI_SECCOMP_DEFAULT_ACTION_INVALID;
    }

    if (policy->allowed_syscall_count > PCHSI_SECCOMP_MAX_ALLOWLIST) {
        return PCHSI_SECCOMP_ALLOWLIST_TOO_LARGE;
    }

    if (
        policy->allowed_syscall_count > 0U
        && policy->allowed_syscalls == NULL
    ) {
        return PCHSI_SECCOMP_INVALID_ARGUMENT;
    }

    for (index = 0U; index < policy->allowed_syscall_count; index += 1U) {
        int syscall_number = policy->allowed_syscalls[index];

        if (
            syscall_number < 0
            || ((uint32_t)syscall_number & PCHSI_X32_SYSCALL_BIT) != 0U
        ) {
            return PCHSI_SECCOMP_SYSCALL_INVALID;
        }

        if (
            index > 0U
            && policy->allowed_syscalls[index - 1U] >= syscall_number
        ) {
            return PCHSI_SECCOMP_ALLOWLIST_NOT_SORTED;
        }
    }

    return PCHSI_SECCOMP_OK;
}

enum pchsi_seccomp_status pchsi_build_seccomp_program(
    const struct pchsi_seccomp_policy *policy,
    struct pchsi_bpf_program *program
)
{
    size_t index = 0U;
    size_t cursor = 0U;
    enum pchsi_seccomp_status status = pchsi_validate_policy(policy);

    if (status != PCHSI_SECCOMP_OK) {
        return status;
    }

    if (program == NULL) {
        return PCHSI_SECCOMP_INVALID_ARGUMENT;
    }

    memset(program, 0, sizeof(*program));

    pchsi_set_statement(
        &program->instructions[cursor++],
        (unsigned short)(BPF_LD | BPF_W | BPF_ABS),
        (uint32_t)offsetof(struct seccomp_data, arch)
    );
    pchsi_set_jump(
        &program->instructions[cursor++],
        (unsigned short)(BPF_JMP | BPF_JEQ | BPF_K),
        (uint32_t)AUDIT_ARCH_X86_64,
        1U,
        0U
    );
    pchsi_set_statement(
        &program->instructions[cursor++],
        (unsigned short)(BPF_RET | BPF_K),
        (uint32_t)SECCOMP_RET_KILL_PROCESS
    );
    pchsi_set_statement(
        &program->instructions[cursor++],
        (unsigned short)(BPF_LD | BPF_W | BPF_ABS),
        (uint32_t)offsetof(struct seccomp_data, nr)
    );
    pchsi_set_jump(
        &program->instructions[cursor++],
        (unsigned short)(BPF_JMP | BPF_JSET | BPF_K),
        PCHSI_X32_SYSCALL_BIT,
        0U,
        1U
    );
    pchsi_set_statement(
        &program->instructions[cursor++],
        (unsigned short)(BPF_RET | BPF_K),
        (uint32_t)SECCOMP_RET_KILL_PROCESS
    );

    for (index = 0U; index < policy->allowed_syscall_count; index += 1U) {
        pchsi_set_jump(
            &program->instructions[cursor++],
            (unsigned short)(BPF_JMP | BPF_JEQ | BPF_K),
            (uint32_t)policy->allowed_syscalls[index],
            0U,
            1U
        );
        pchsi_set_statement(
            &program->instructions[cursor++],
            (unsigned short)(BPF_RET | BPF_K),
            (uint32_t)SECCOMP_RET_ALLOW
        );
    }

    pchsi_set_statement(
        &program->instructions[cursor++],
        (unsigned short)(BPF_RET | BPF_K),
        policy->default_action
    );

    program->instruction_count = cursor;
    return PCHSI_SECCOMP_OK;
}

static int pchsi_instruction_equal(
    const struct sock_filter *left,
    const struct sock_filter *right
)
{
    return (
        left->code == right->code
        && left->jt == right->jt
        && left->jf == right->jf
        && left->k == right->k
    );
}

enum pchsi_seccomp_status pchsi_verify_seccomp_program(
    const struct pchsi_seccomp_policy *policy,
    const struct pchsi_bpf_program *program
)
{
    struct pchsi_bpf_program expected;
    size_t index = 0U;
    enum pchsi_seccomp_status status;

    if (program == NULL) {
        return PCHSI_SECCOMP_INVALID_ARGUMENT;
    }

    status = pchsi_build_seccomp_program(policy, &expected);
    if (status != PCHSI_SECCOMP_OK) {
        return status;
    }

    if (program->instruction_count != expected.instruction_count) {
        return PCHSI_SECCOMP_PROGRAM_LENGTH_INVALID;
    }

    for (index = 0U; index < expected.instruction_count; index += 1U) {
        if (
            !pchsi_instruction_equal(
                &program->instructions[index],
                &expected.instructions[index]
            )
        ) {
            return PCHSI_SECCOMP_PROGRAM_MISMATCH;
        }
    }

    return PCHSI_SECCOMP_OK;
}

const char *pchsi_seccomp_status_name(
    enum pchsi_seccomp_status status
)
{
    switch (status) {
        case PCHSI_SECCOMP_OK:
            return "PCHSI_SECCOMP_OK";
        case PCHSI_SECCOMP_INVALID_ARGUMENT:
            return "PCHSI_SECCOMP_INVALID_ARGUMENT";
        case PCHSI_SECCOMP_ARCHITECTURE_INVALID:
            return "PCHSI_SECCOMP_ARCHITECTURE_INVALID";
        case PCHSI_SECCOMP_DEFAULT_ACTION_INVALID:
            return "PCHSI_SECCOMP_DEFAULT_ACTION_INVALID";
        case PCHSI_SECCOMP_ALLOWLIST_TOO_LARGE:
            return "PCHSI_SECCOMP_ALLOWLIST_TOO_LARGE";
        case PCHSI_SECCOMP_ALLOWLIST_NOT_SORTED:
            return "PCHSI_SECCOMP_ALLOWLIST_NOT_SORTED";
        case PCHSI_SECCOMP_SYSCALL_INVALID:
            return "PCHSI_SECCOMP_SYSCALL_INVALID";
        case PCHSI_SECCOMP_PROGRAM_LENGTH_INVALID:
            return "PCHSI_SECCOMP_PROGRAM_LENGTH_INVALID";
        case PCHSI_SECCOMP_PROGRAM_MISMATCH:
            return "PCHSI_SECCOMP_PROGRAM_MISMATCH";
    }

    return "PCHSI_SECCOMP_UNKNOWN";
}
