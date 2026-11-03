import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SeeWrapperTests(unittest.TestCase):
    def run_wrapper(self, mode, fail=False):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "compose").mkdir()
            (repo / "bin").mkdir()
            shutil.copyfile(ROOT / "demo.sh", repo / "demo.sh")
            (repo / "compose/.env").write_text("OPERATOR_CONFIGURATION=preserve\n")
            log = repo / "commands.jsonl"
            docker = repo / "bin/docker"
            docker.write_text("""#!/usr/bin/env python3
import json, os, sys
with open(os.environ['DEMO_TEST_LOG'], 'a') as stream:
    stream.write(json.dumps({'args': sys.argv[1:], 'project': os.environ['COMPOSE_PROJECT_NAME']}) + '\\n')
if 'run' in sys.argv and os.environ.get('DEMO_TEST_FAIL') == '1':
    sys.exit(1)
""")
            docker.chmod(0o755)
            temporary_logs = set(Path('/tmp').glob('dp-see-demo.*'))
            result = subprocess.run(
                ['bash', str(repo / 'demo.sh'), mode],
                env={
                    **os.environ,
                    'PATH': str(repo / 'bin') + os.pathsep + os.environ['PATH'],
                    'COMPOSE_PROJECT_NAME': 'fixture-demo-project',
                    'DEMO_TEST_LOG': str(log),
                    'DEMO_TEST_FAIL': '1' if fail else '0',
                },
                capture_output=True, text=True,
            )
            self.assertEqual((repo / 'compose/.env').read_text(), 'OPERATOR_CONFIGURATION=preserve\n')
            self.assertEqual(set(Path('/tmp').glob('dp-see-demo.*')), temporary_logs)
            commands = [json.loads(line) for line in log.read_text().splitlines()]
        return result, commands

    def test_both_commands_use_the_existing_runner_and_preserve_operator_data(self):
        for mode, client_mode in [('demo-see-impacts', 'demo'), ('validate-see-impacts', 'validate')]:
            with self.subTest(mode=mode):
                result, commands = self.run_wrapper(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(any('ps' in item['args'] and '-q' in item['args'] for item in commands))
                runs = [item for item in commands if 'run' in item['args']]
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0]['args'][-2:], ['/usr/local/bin/see_impacts_demo.py', client_mode])
                self.assertIn('demo-runner', runs[0]['args'])
                self.assertIn('-T', runs[0]['args'])
                for item in commands:
                    self.assertEqual(item['project'], 'fixture-demo-project')
                    self.assertNotIn('--volumes', item['args'])

    def test_failed_client_still_stops_its_stack_and_propagates_failure(self):
        result, commands = self.run_wrapper('demo-see-impacts', fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('unbound variable', result.stderr)
        self.assertEqual(sum('down' in item['args'] for item in commands), 2)
        self.assertTrue(any('logs' in item['args'] for item in commands))


if __name__ == '__main__':
    unittest.main()
