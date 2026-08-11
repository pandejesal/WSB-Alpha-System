from src.sandbox.sandbox_env import PythonSandbox, SandboxError


def test_sandbox_safe():
    sb = PythonSandbox()
    code = "import pandas as pd\nx = len([1, 2, 3])"
    success, msg = sb.execute(code)
    print(f"Safe code execution: success={success}, msg={msg}")
    assert success is True

def test_sandbox_unsafe_builtin():
    sb = PythonSandbox()
    # This attempts to bypass AST `import` check but uses builtin __import__
    code = "__import__('os').system('echo hi')"
    try:
        sb.execute(code)
        assert False, "Should have thrown SandboxError"
    except SandboxError as e:
        print(f"Unsafe code correctly blocked by AST: {e}")

if __name__ == "__main__":
    test_sandbox_safe()
    test_sandbox_unsafe_builtin()
