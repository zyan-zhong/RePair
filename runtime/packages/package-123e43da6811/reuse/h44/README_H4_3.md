# H4.3 — Planner POST single-send settlement and autonomous safe-infrastructure disposition

This continuation consumes the exact H4.2 one-send POST evidence after native F0/F1 and the independent verifier are already VERIFIED_COMPLETE.

It never blindly resends the same logical call. Existing ACCEPTED POST is adopted with zero Provider calls. AMBIGUOUS_POST_SEND, method-invalid/refusal/schema-invalid, auth/config, runtime-adapter defects, and unknown partial states are terminal no-resend.

Only the frozen P2 transport's explicit SAFE_PRE_SEND / SAFE_PROVIDER_REJECTION evidence can authorize one new content-addressed remediation logical call. The remediation uses the identical rendered provider request body while binding a distinct remediation scientific-unit identity to the original logical call, attempt, failure class and request-body hash. It is one-shot; a failed remediation never authorizes a second remediation.

No F0/F1 rerun, environment rerun, optimizer step, promotion, round close or next-round launch occurs in this package. Scientific cardinalities remain authority-driven and round-adaptive.
