# Full Repository Regression Native-Build Prerequisite

The pre-push full repository regression initially reported four failures.
All four required the ignored native test artifact:

`native/s1_backend_probe/build/pchsi-s1-backend-probe`

The source tree was not failing its security contracts; the build artifact
had not been materialized in the fresh linked worktree. The final push
driver therefore runs `/usr/bin/make -C native/s1_backend_probe clean all`
before targeted security tests and the full repository suite. The default
Makefile `all` target compiles the closed describe/version binary only; it
does not run real probe payloads. The ignored `build/` directory is never
added to Git.
