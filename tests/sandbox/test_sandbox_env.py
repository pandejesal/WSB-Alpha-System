import unittest
from src.sandbox.sandbox_env import PythonSandbox, SandboxError

class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.sandbox = PythonSandbox()

    def test_safe_execution(self):
        code = "x = 1 + 1\ny = x * 2"
        success, _ = self.sandbox.execute(code)
        self.assertTrue(success)

    def test_unsafe_import(self):
        code = "import os\nos.system('echo hi')"
        with self.assertRaises(SandboxError):
            self.sandbox.execute(code)

if __name__ == '__main__':
    unittest.main()
