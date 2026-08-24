import unittest
import os
import shutil
import tempfile
import zipfile

class TestPackAgentZip(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dist_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(self.dist_dir)
        
        # Create dummy executables
        with open(os.path.join(self.dist_dir, "ParentalControlAgent.exe"), "w") as f:
            f.write("AGENT")
        with open(os.path.join(self.dist_dir, "Updater.exe"), "w") as f:
            f.write("UPDATER")
            
        self.zip_path = os.path.join(self.temp_dir, "agent-update.zip")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_pack_zip(self):
        # The logic that will be in system.py
        if not os.path.exists(self.dist_dir):
            self.fail("dist_dir does not exist")
            
        agent_exe = os.path.join(self.dist_dir, "ParentalControlAgent.exe")
        updater_exe = os.path.join(self.dist_dir, "Updater.exe")
        
        with zipfile.ZipFile(self.zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(agent_exe):
                zipf.write(agent_exe, arcname="ParentalControlAgent.exe")
            if os.path.exists(updater_exe):
                zipf.write(updater_exe, arcname="Updater.exe")
                
        self.assertTrue(os.path.exists(self.zip_path))
        with zipfile.ZipFile(self.zip_path, 'r') as zipf:
            names = zipf.namelist()
            self.assertIn("ParentalControlAgent.exe", names)
            self.assertIn("Updater.exe", names)

if __name__ == '__main__':
    unittest.main()
