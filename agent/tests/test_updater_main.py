import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# To import updater_main, we will need to create it. We can import it dynamically.
# For now, let's just write the test logic.

class TestUpdaterMain(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.staged_dir = os.path.join(self.temp_dir, "staged")
        self.dest_dir = os.path.join(self.temp_dir, "dest")
        
        os.makedirs(self.staged_dir)
        os.makedirs(self.dest_dir)
        
        # Create a dummy exe in dest to simulate running app
        self.exe_path = os.path.join(self.dest_dir, "ParentalControlAgent.exe")
        with open(self.exe_path, "w") as f:
            f.write("OLD_EXE_CONTENT")
            
        # Create a dummy new exe in staged
        self.new_exe_path = os.path.join(self.staged_dir, "ParentalControlAgent.exe")
        with open(self.new_exe_path, "w") as f:
            f.write("NEW_EXE_CONTENT")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("subprocess.Popen")
    @patch("time.sleep")
    @patch("os.kill")
    def test_run_update_healthy(self, mock_kill, mock_sleep, mock_popen):
        """When the new process stays alive (poll() is None), update succeeds without rollback."""
        mock_kill.side_effect = OSError("Process not found")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import updater_main
        
        updater_main.run_update(9999, self.staged_dir, self.dest_dir, "ParentalControlAgent.exe")
        
        # Verify backup exists
        backup_path = self.exe_path + ".bak"
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, "r") as f:
            self.assertEqual(f.read(), "OLD_EXE_CONTENT")
            
        # Verify new exe is kept
        with open(self.exe_path, "r") as f:
            self.assertEqual(f.read(), "NEW_EXE_CONTENT")
            
        # Verify new exe was started with proper arguments
        self.assertTrue(mock_popen.called)
        spawn_calls = [c for c in mock_popen.call_args_list if c[0] and c[0][0] == [self.exe_path]]
        self.assertTrue(len(spawn_calls) > 0, "Expected launch call for target exe not found")
        self.assertEqual(spawn_calls[0][1]['cwd'], self.dest_dir)

    @patch("subprocess.Popen")
    @patch("time.sleep")
    @patch("os.kill")
    def test_run_update_auto_rollback_on_crash(self, mock_kill, mock_sleep, mock_popen):
        """When the new process crashes immediately (poll() returns error code), auto-rollback restores old exe."""
        mock_kill.side_effect = OSError("Process not found")
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1  # Process crashed on startup
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import updater_main
        
        updater_main.run_update(9999, self.staged_dir, self.dest_dir, "ParentalControlAgent.exe")
        
        # Verify old exe was restored via rollback
        with open(self.exe_path, "r") as f:
            self.assertEqual(f.read(), "OLD_EXE_CONTENT")

if __name__ == '__main__':
    unittest.main()
