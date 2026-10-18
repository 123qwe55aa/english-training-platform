import unittest
from unittest.mock import patch

from scripts import teaching_agent


class TeachingAgentConfigTests(unittest.TestCase):
    def test_remote_mode_requires_explicit_target_and_directory(self):
        with patch.object(teaching_agent, 'HOST', None), patch.object(teaching_agent, 'REMOTE', None):
            with self.assertRaisesRegex(RuntimeError, 'ENGLISH_PLATFORM_SSH_TARGET'):
                teaching_agent.command()

    def test_remote_command_uses_configured_target_and_directory(self):
        with patch.object(teaching_agent, 'HOST', 'teacher@example.test'), patch.object(teaching_agent, 'REMOTE', '/srv/english'):
            cmd = teaching_agent.command()
        self.assertEqual(cmd[6], 'teacher@example.test')
        self.assertIn("cd /srv/english", cmd[7])


if __name__ == '__main__':
    unittest.main()
