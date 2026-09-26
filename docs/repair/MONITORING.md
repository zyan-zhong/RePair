# Observe a registered run

The existing V212 window covers Rollout, Analyzer L/G/C/P/X, PRE source reviews,
PRE decision, F0/F1, POST, training, parent/candidate evaluation, acceptance,
memory closure and paper export. The source package is selected by the
`progress_window` role in `runtime/COMPONENT_INDEX.json`.

With the registered interpreter and monitor authority available:

```bash
python "$MONITOR_PACKAGE/WATCH.py" --authority "$MONITOR_AUTHORITY" --watch
python "$MONITOR_PACKAGE/WATCH.py" --authority "$MONITOR_AUTHORITY" --json
```

`MONITOR_PACKAGE` is the exact indexed source package; `MONITOR_AUTHORITY` is the
verified local deployment binding. These are not inferred by scanning directories.
On the original server, the existing unified status wrapper selects them.

Use `--formal` or `--validation` to select the registered run type, `--details`
for evidence locations, `--color never` for log output and `--interval 5` for a
five-second refresh. Green marks running/completed stages, yellow waiting or
unknown state, red errors, cyan reuse, and gray pending stages. Unknown totals
remain unknown; a one-call PRE/POST request is shown as 0/1 while waiting.

Closing the window does not stop the resident or scheduler jobs. A full progress
bar means the stage's counted items closed; successful scientific acceptance still
requires its own receipt. `QUERY_UNAVAILABLE` and observer read failures describe
missing observations, not proof that training stopped. The window is read-only.
