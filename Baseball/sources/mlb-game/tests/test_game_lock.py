"""Exercise the stage lock across real Windows worker processes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "pipeline" / "game-lock.ps1"


def quoted(value):
    return "'" + str(value).replace("'", "''") + "'"


def command(root, game, hold=False):
    script = (
        "$ErrorActionPreference = 'Stop'; "
        f". {quoted(HELPER)}; "
        f"$handle = Enter-MlbGameLock -StateRoot {quoted(root)} "
        f"-GamePk {quoted(game)} -TimeoutSeconds 1; "
        "try { Write-Output 'locked'; "
        + ("[void][Console]::ReadLine(); " if hold else "")
        + "} finally { $handle.Dispose() }"
    )
    return ["powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-Command", script]


@unittest.skipUnless(os.name == "nt", "Windows stage lock")
class GameLockTests(unittest.TestCase):
    def test_same_game_excluded_other_game_runs_and_crash_releases_lock(self):
        with tempfile.TemporaryDirectory() as root:
            worker = subprocess.Popen(
                command(root, "1", hold=True), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(worker.stdout.readline().strip(), "locked")
                blocked = subprocess.run(command(root, "1"), capture_output=True,
                                         text=True, timeout=15)
                self.assertNotEqual(blocked.returncode, 0)
                self.assertIn("Timed out waiting", blocked.stderr)
                independent = subprocess.run(command(root, "2"), capture_output=True,
                                             text=True, timeout=15)
                self.assertEqual(independent.returncode, 0, independent.stderr)
                worker.kill()
                worker.communicate(timeout=10)
                resumed = subprocess.run(command(root, "1"), capture_output=True,
                                         text=True, timeout=15)
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
            finally:
                if worker.poll() is None:
                    worker.kill()
                worker.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
