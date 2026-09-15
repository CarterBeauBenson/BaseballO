# Private workstation operations

`BaseballO Local Services` is an installed Windows Task Scheduler task for the
current user. It runs at logon and every five minutes while that user is signed
in, with limited privileges and no stored password. It is not a before-login
Windows service and does not make the workstation a public server.

The task invokes `scripts/infra/ensure-local-services.ps1`. Each service is
checked independently. If its loopback port is absent, the supervisor invokes
the existing guarded starter for Fuseki, NiFi or Explorer. If a port is occupied
but its health response is wrong, it records a failure and does not kill the
listener. Source acquisition, retries, rebuilds, validation and promotion remain
NiFi-owned. SQL readiness does not trigger a process restart.

The supervisor does not restart a running Explorer merely because the Git
working tree changed. Explicit web deployment still uses `launch-explorer.ps1`.
At the next recovery it uses the checkout recorded in the task action, so keep
that checkout available. This setup has not been validated after sign-out,
reboot, volume loss or a Python runtime upgrade.

## Install, remove and maintain

Run from `Baseball/`:

```powershell
.\scripts\infra\install-local-supervision.ps1
.\scripts\infra\ensure-local-services.ps1 -CheckOnly
.\scripts\infra\ensure-local-services.ps1 -Pause
.\scripts\infra\ensure-local-services.ps1 -Resume
.\scripts\infra\install-local-supervision.ps1 -Remove
```

Installation is repeatable and refuses to replace an unrelated task with the
same name. Removal unregisters this task and leaves existing processes running.
`-Pause` writes a maintenance marker and waits up to one minute for an already
active startup to finish. A timeout leaves supervision paused and fails the
operation; retry the stop after that startup finishes. The runner checks for
maintenance again before each service. Task Scheduler rejects overlapping runs,
and a named mutex also excludes concurrent manual invocations in the session.

`stop-stack.ps1` pauses supervision before stopping NiFi and Fuseki.
`start-stack.ps1` clears maintenance before the explicit startup. These scripts
retain their existing service scope; Explorer is managed separately. To keep a
deliberately stopped service down, leave supervision paused. `-Resume` clears
maintenance and immediately checks/starts missing services; `-Resume -CheckOnly`
only checks them, with automatic checks continuing on the task's next trigger.

## Evidence and failure handling

The latest atomic snapshot is
`%LOCALAPPDATA%\BaseballO\state\operations\services.json`. It records service
liveness, which processes were started, errors, and check time. The explicit
`dataReadinessChecked: false` prevents conflating uptime with usable metrics.
Check `operations/maintenance.json` too: while paused, the previous service
snapshot is historical. Startup stdout/stderr use fixed files per service in
that directory. Existing application logs stay in their owning runtime state.

The task returns a nonzero result when a service is unavailable. In Task
Scheduler, inspect its result and last run time; a stale successful snapshot is
not current health. This release does not send email, configure external alerts,
or establish a backup retention policy.

The runner waits on the starter process rather than captured output handles.
It retains the native process handle to read the exit code correctly in Windows
PowerShell, bounds each starter at eleven minutes, and applies the task's overall
fifteen-minute execution limit. A timeout is a failure, not proof that a daemon
was stopped; the next run rechecks actual listeners before any new start.

## Acceptance on 2026-09-14

The read-only check identified all three services without restarting them.
Maintenance pause and resume passed, including replacement of an existing
status file. A controlled stop of the verified Explorer Node process recovered
it from PID 30060 to PID 32116 in under eight seconds, while NiFi and Fuseki
remained running. These are runtime observations, not stable process identities.

Earlier trials exposed Windows status-file null conversion and inherited pipe
handling defects; both were fixed before installation. Task configuration was
verified as Interactive/Limited, IgnoreNew, a fifteen-minute execution limit,
and logon plus five-minute triggers. Before-login uptime, off-machine recovery
and materialized metric readiness remain separate production gates.

The installed Task Scheduler action also completed successfully: its recorded
run began at `2026-09-15T00:15:49Z`, returned result `0`, and returned to `Ready`.
Its atomic snapshot recorded all three services alive with no starts required.

Windows distinguishes interactive tasks from S4U tasks: interactive tasks require
an existing login, while S4U has network and encrypted-file access restrictions.
See [Microsoft's task logon documentation](https://learn.microsoft.com/en-us/windows/win32/taskschd/principal-logontype)
and [task settings](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasksettingsset).
