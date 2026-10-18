import importlib.util,json,subprocess,sys,tempfile,os
from pathlib import Path
from unittest import TestCase,mock
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('teaching_agent',ROOT/'scripts/teaching_agent.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)

class AgentCLITests(TestCase):
    def test_command_quotes_upload_name_and_uses_existing_ssh(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'a $(evil).mp4';path.write_bytes(b'data')
            with mock.patch.object(cli,'HOST','teacher@example.test'),mock.patch.object(cli,'REMOTE','/srv/english'):
                command=cli.command(upload=path)
            import shlex
            tail=command[-1].split(' && ',1)[1]
            self.assertIn('a $(evil).mp4',shlex.split(tail));self.assertIn('BatchMode=yes',command)
            self.assertEqual(command[-2],'teacher@example.test');self.assertIn('cd /srv/english',command[-1])
    def test_transport_failure_preserves_id_for_safe_retry(self):
        with mock.patch.object(cli,'HOST','teacher@example.test'),mock.patch.object(cli,'REMOTE','/srv/english'),mock.patch.object(cli.subprocess,'run',side_effect=subprocess.TimeoutExpired('ssh',240)):
            response=cli.send({'tool':'rewards.award','request_id':'same-id'})
        self.assertEqual(response['error']['code'],'transport_error');self.assertEqual(response['error']['request_id'],'same-id')
    def test_local_cli_discovers_machine_readable_tools(self):
        # tools.list does not need a database; no migration or production writes.
        env={**os.environ,'SECRET_KEY':'test-only'}
        result=subprocess.run([sys.executable,str(ROOT/'scripts/teaching_agent.py'),'--local','tools'],env=env,capture_output=True,text=True,check=True)
        self.assertTrue(json.loads(result.stdout)['ok'])
