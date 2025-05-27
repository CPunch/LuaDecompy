import os
import subprocess
import pytest
import tempfile # Ensure this is imported

# Assuming lundump and lparser are in the parent directory or PYTHONPATH
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import lundump
import lparser

# --- Configuration ---
LUA_TEST_SUITE_DIR = os.path.join(os.path.dirname(__file__), 'lua5.1_suite')
# Assume luac and lua are in PATH. Error handling for their absence can be added later.
LUAC_CMD = 'luac5.1' # Specify version if needed, e.g., luac5.1
LUA_CMD = 'lua5.1'   # Specify version if needed, e.g., lua5.1

# --- Helper to find Lua files ---
def get_lua_test_files():
    lua_files = []
    if not os.path.isdir(LUA_TEST_SUITE_DIR):
        # Raise an error or return empty if dir not found, so pytest can report it
        # For now, let's allow pytest to fail if parametrized with nothing
        return []
    for filename in os.listdir(LUA_TEST_SUITE_DIR):
        if filename.endswith('.lua'):
            lua_files.append(os.path.join(LUA_TEST_SUITE_DIR, filename))
    return lua_files

# --- Pytest Parametrization ---
lua_test_files = get_lua_test_files()
if not lua_test_files:
    # If no test files are found, we should ensure pytest doesn't just pass silently.
    # One way is to create a dummy test that fails or skips.
    # For now, pytest will likely report 0 tests run for this parametrization,
    # which is acceptable as a starting point.
    pass

@pytest.mark.parametrize("lua_file_path", lua_test_files)
def test_lua_file(lua_file_path, tmp_path):
    """
    Tests decompilation and execution of a single Lua file from the test suite.
    1. Compiles .lua to .luac using luac.
    2. Decompiles .luac to pseudocode using LuaDecompy.
    3. Executes the pseudocode using a Lua interpreter.
    4. Asserts that the Lua interpreter exits successfully (code 0).
    """
    base_name = os.path.basename(lua_file_path)
    luac_output_path = tmp_path / (base_name + 'c')
    pseudocode_output_path = tmp_path / (base_name + "_pseudo.lua")

    # 1. Compile .lua to .luac
    compile_cmd = [LUAC_CMD, '-o', str(luac_output_path), lua_file_path]
    compile_process = subprocess.run(compile_cmd, capture_output=True, text=True)
    assert compile_process.returncode == 0, \
        f"luac compilation failed for {lua_file_path}\n{compile_process.stderr}"

    # 2. Decompile .luac to pseudocode
    try:
        undumper = lundump.LuaUndump()
        chunk = undumper.loadFile(str(luac_output_path))
        # Optional: undumper.print_dissassembly() # For debugging
        
        decompiler = lparser.LuaDecomp(chunk)
        pseudocode = decompiler.getPseudoCode()
    except Exception as e:
        pytest.fail(f"LuaDecompy failed for {luac_output_path}\n{str(e)}")

    with open(pseudocode_output_path, 'w') as f:
        f.write(pseudocode)

    # 3. Execute the pseudocode
    execute_cmd = [LUA_CMD, str(pseudocode_output_path)]
    execute_process = subprocess.run(execute_cmd, capture_output=True, text=True)

    # 4. Assert successful execution
    # The original lua tests print 'OK' or errors.
    # A simple return code check is a good first step.
    # More advanced checks could parse output if tests have a standard success signature.
    assert execute_process.returncode == 0, \
        f"Execution of pseudocode for {lua_file_path} failed.\n" \
        f"STDOUT:\n{execute_process.stdout}\n" \
        f"STDERR:\n{execute_process.stderr}"

# --- Optional: Add a test to ensure test files were found ---
def test_found_lua_files():
    if not lua_test_files:
        pytest.skip("No Lua test files found in {LUA_TEST_SUITE_DIR}. Skipping individual file tests.")
    assert len(lua_test_files) > 0, f"No .lua files found in {LUA_TEST_SUITE_DIR}"
