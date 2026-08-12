import ast
import json
import os
import subprocess
import sys
import tempfile


class SandboxError(Exception):
    pass

class ASTValidator(ast.NodeVisitor):
    def __init__(self, allowed_modules: list):
        self.allowed_modules = set(allowed_modules)
        self.violations = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module not in self.allowed_modules:
                self.violations.append(f"Disallowed import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module not in self.allowed_modules:
                self.violations.append(f"Disallowed import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == '__import__':
            self.violations.append("Direct call to __import__ is not allowed.")
        self.generic_visit(node)

class PythonSandbox:
    def __init__(self, timeout: int = 10, max_memory_mb: int = 512):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.allowed_modules = ['math', 'datetime', 'typing', 'pandas', 'numpy', 'scipy', 'statsmodels', 'json']

    def validate_ast(self, code: str) -> bool:
        try:
            tree = ast.parse(code)
            validator = ASTValidator(self.allowed_modules)
            validator.visit(tree)
            if validator.violations:
                raise SandboxError(f"AST Validation failed: {', '.join(validator.violations)}")
            return True
        except SyntaxError as e:
            raise SandboxError(f"Syntax Error in generated code: {e}")

    def _get_runner_script(self, code_path: str, result_path: str) -> str:
        # We run the code in a subprocess. We apply resource limits if on Unix.
        script = f"""
import sys
import json
import platform

def apply_limits():
    if platform.system() == 'Linux' or platform.system() == 'Darwin':
        try:
            import resource
            # Limit memory (bytes)
            mem_limit = {self.max_memory_mb} * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
            # Limit CPU time (seconds)
            resource.setrlimit(resource.RLIMIT_CPU, ({self.timeout}, {self.timeout}))
        except ValueError:
            pass

apply_limits()

try:
    # Execute the generated code
    # The AST validator is the primary gatekeeper for dangerous imports.
    # We remove explicitly dangerous builtins like eval and exec,
    # but retain __import__ so valid AST imports can succeed, and retain core types (len, int, list).
    safe_builtins = __builtins__.copy() if isinstance(__builtins__, dict) else __builtins__.__dict__.copy()
    dangerous_builtins = ['eval', 'exec', 'compile', 'open', 'input']
    for b in dangerous_builtins:
        safe_builtins.pop(b, None)

    namespace = {{"__builtins__": safe_builtins}}
    with open('{code_path}', 'r') as f:
        exec(f.read(), namespace)

    # We expect the strategy to define a 'run_strategy' function or similar.
    # For sandboxing pure validation, just executing it without error is a start.
    result = {{"status": "success"}}
except Exception as e:
    result = {{"status": "error", "message": str(e)}}

with open('{result_path}', 'w') as f:
    json.dump(result, f)
"""
        return script

    def execute(self, code: str) -> tuple[bool, str]:
        self.validate_ast(code)

        with tempfile.TemporaryDirectory() as temp_dir:
            code_path = os.path.join(temp_dir, 'strategy.py')
            runner_path = os.path.join(temp_dir, 'runner.py')
            result_path = os.path.join(temp_dir, 'result.json')

            with open(code_path, 'w') as f:
                f.write(code)

            with open(runner_path, 'w') as f:
                f.write(self._get_runner_script(code_path, result_path))

            try:
                subprocess.run(  # noqa: PLW1510 - Implicit check=False is acceptable
                    [sys.executable, runner_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 2  # Buffer for OS
                )

                if os.path.exists(result_path):
                    with open(result_path, 'r') as f:
                        res = json.load(f)
                    if res.get('status') == 'success':
                        return True, "Execution successful"
                    else:
                        return False, res.get('message', 'Unknown error')
                return False, "Result file not generated."

            except subprocess.TimeoutExpired:
                return False, f"Execution timed out after {self.timeout} seconds."
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                return False, f"Sandbox error: {e!s}"
