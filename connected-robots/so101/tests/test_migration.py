"""Verify migration preserves working configuration and calibration identities."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
BASH = 'C:/Program Files/Git/bin/bash.exe' if sys.platform == 'win32' else shutil.which('bash')


class MigrationTests(unittest.TestCase):
    @unittest.skipUnless(BASH, 'Bash required')
    def test_setup_and_launcher_reuse_existing_test_config(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            runtime = repo / 'connected-robots/so101'
            runtime.mkdir(parents=True)
            legacy = repo / 'test-code/so101-config.env'
            legacy.parent.mkdir()
            legacy.write_text('SO101_ROLE=follower\nSO101_CAMERA_INDEX=6\n', encoding='utf-8')
            before = legacy.read_bytes()
            for name in ['setup-so101-device.sh','start-so101-control.sh','SO-101-Control-and-Camera.desktop','so101-config.env.example']:
                shutil.copyfile(ROOT / name, runtime / name)
            env = dict(os.environ, XDG_DESKTOP_DIR=(repo / 'Desktop').as_posix())
            env.pop('SO101_CONFIG_FILE', None)
            setup = subprocess.run([BASH, str(runtime / 'setup-so101-device.sh')], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(setup.returncode, 0, setup.stderr)
            check = subprocess.run([BASH, str(runtime / 'start-so101-control.sh'), '--check-config'], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn('6 / 2 / 4', check.stdout)
            self.assertEqual(legacy.read_bytes(), before)
            self.assertFalse((runtime / 'so101-config.env').exists())

    def test_bridge_leader_uses_working_ids_and_allows_previous_ids(self):
        for extra, expected in [([], ['lead_r','lead_l']), (['--left-id','lead_l','--right-id','lead_r'], ['lead_l','lead_r'])]:
            with self.subTest(extra=extra):
                configs = []
                def config(**kwargs):
                    configs.append(kwargs)
                    return SimpleNamespace(**kwargs)
                left, right = Mock(is_connected=True), Mock(is_connected=True)
                left.get_action.side_effect = KeyboardInterrupt
                modules = {'zmq':Mock(),
                           'lerobot.teleoperators.so_leader.config_so_leader':SimpleNamespace(SOLeaderTeleopConfig=config),
                           'lerobot.teleoperators.so_leader.so_leader':SimpleNamespace(SOLeader=Mock(side_effect=[left,right]))}
                spec = importlib.util.spec_from_file_location('migration_leader', ROOT / 'leader_teleop.py')
                module = importlib.util.module_from_spec(spec)
                with patch.dict(sys.modules, modules), patch.object(sys, 'argv', ['leader','--follower-host','localhost',*extra]):
                    spec.loader.exec_module(module)
                    module.main()
                self.assertEqual([c['id'] for c in configs], expected)
                self.assertEqual([c['port'] for c in configs], ['/dev/ttyACM1','/dev/ttyACM0'])


if __name__ == '__main__':
    unittest.main()
