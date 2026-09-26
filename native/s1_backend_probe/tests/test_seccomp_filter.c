#include "pchsi_s1/seccomp_filter.h"

#include <assert.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdint.h>

static void test_build_and_verify(void)
{
    static const int ALLOWLIST[] = {0, 1, 3, 60};
    struct pchsi_seccomp_policy policy = {
        (uint32_t)AUDIT_ARCH_X86_64,
        (uint32_t)SECCOMP_RET_KILL_PROCESS,
        ALLOWLIST,
        sizeof(ALLOWLIST) / sizeof(ALLOWLIST[0])
    };
    struct pchsi_bpf_program program;

    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_OK
    );
    assert(program.instruction_count == 15U);
    assert(program.instructions[0].code == (BPF_LD | BPF_W | BPF_ABS));
    assert(program.instructions[1].code == (BPF_JMP | BPF_JEQ | BPF_K));
    assert(program.instructions[1].k == (uint32_t)AUDIT_ARCH_X86_64);
    assert(program.instructions[2].k == (uint32_t)SECCOMP_RET_KILL_PROCESS);
    assert(program.instructions[4].code == (BPF_JMP | BPF_JSET | BPF_K));
    assert(program.instructions[4].k == UINT32_C(0x40000000));
    assert(program.instructions[5].k == (uint32_t)SECCOMP_RET_KILL_PROCESS);
    assert(
        program.instructions[program.instruction_count - 1U].k
        == (uint32_t)SECCOMP_RET_KILL_PROCESS
    );
    assert(
        pchsi_verify_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_OK
    );
}

static void test_policy_rejections(void)
{
    static const int UNSORTED[] = {1, 0};
    static const int X32[] = {0x40000000};
    struct pchsi_bpf_program program;
    struct pchsi_seccomp_policy policy = {
        (uint32_t)AUDIT_ARCH_X86_64,
        (uint32_t)SECCOMP_RET_KILL_PROCESS,
        UNSORTED,
        2U
    };

    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_ALLOWLIST_NOT_SORTED
    );

    policy.allowed_syscalls = X32;
    policy.allowed_syscall_count = 1U;
    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_SYSCALL_INVALID
    );

    policy.allowed_syscalls = NULL;
    policy.allowed_syscall_count = 0U;
    policy.audit_architecture = UINT32_C(0);
    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_ARCHITECTURE_INVALID
    );

    policy.audit_architecture = (uint32_t)AUDIT_ARCH_X86_64;
    policy.default_action = (uint32_t)SECCOMP_RET_ERRNO;
    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_DEFAULT_ACTION_INVALID
    );
}

static void test_verifier_detects_mutation(void)
{
    static const int ALLOWLIST[] = {0, 1};
    struct pchsi_seccomp_policy policy = {
        (uint32_t)AUDIT_ARCH_X86_64,
        (uint32_t)SECCOMP_RET_KILL_PROCESS,
        ALLOWLIST,
        2U
    };
    struct pchsi_bpf_program program;

    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_OK
    );

    program.instructions[1].k = UINT32_C(0);
    assert(
        pchsi_verify_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_PROGRAM_MISMATCH
    );

    assert(
        pchsi_build_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_OK
    );
    program.instruction_count -= 1U;
    assert(
        pchsi_verify_seccomp_program(&policy, &program)
        == PCHSI_SECCOMP_PROGRAM_LENGTH_INVALID
    );
}

int main(void)
{
    test_build_and_verify();
    test_policy_rejections();
    test_verifier_detects_mutation();
    return 0;
}
