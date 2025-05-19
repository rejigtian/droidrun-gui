import io
import contextlib
import ast
import traceback
from typing import Any, Dict
from .async_utils import async_to_sync
import asyncio

class SimpleCodeExecutor:
    """
    A simple code executor that runs Python code with state persistence.

    This executor maintains a global and local state between executions,
    allowing for variables to persist across multiple code runs.

    NOTE: not safe for production use! Use with caution.
    """

    def __init__(self, loop, locals: Dict[str, Any] = {}, globals: Dict[str, Any] = {}, tools = {}, use_same_scope: bool = True):
        """
        Initialize the code executor.

        Args:
            locals: Local variables to use in the execution context
            globals: Global variables to use in the execution context
            tools: List of tools available for execution
        """

        # loop throught tools and add them to globals, but before that check if tool value is async, if so convert it to sync. tools is a dictionary of tool name: function
        # e.g. tools = {'tool_name': tool_function}
        
        # check if tools is a dictionary
        if isinstance(tools, dict):
            for tool_name, tool_function in tools.items():
                if asyncio.iscoroutinefunction(tool_function):
                    # If the function is async, convert it to sync
                    tool_function = async_to_sync(tool_function)
                # Add the tool to globals
                globals[tool_name] = tool_function
        elif isinstance(tools, list):
            # If tools is a list, convert it to a dictionary with tool name as key and function as value
            for tool in tools:
                if asyncio.iscoroutinefunction(tool):
                    # If the function is async, convert it to sync
                    tool = async_to_sync(tool)
                # Add the tool to globals
                globals[tool.__name__] = tool
        else:
            raise ValueError("Tools must be a dictionary or a list of functions.")


        # add time to globals
        import time
        globals['time'] = time
        # State that persists between executions
        self.globals = globals
        self.locals = locals
        self.loop = loop
        self.use_same_scope = use_same_scope
        if self.use_same_scope:
            # If using the same scope, set the globals and locals to the same dictionary
            self.globals = self.locals = {**self.locals, **{k: v for k, v in self.globals.items() if k not in self.locals}}

    async def execute(self, code: str) -> str:
        """
        Execute Python code and capture output and return values.

        Args:
            code: Python code to execute

        Returns:
            str: Output from the execution, including print statements.
        """
        # Capture stdout and stderr
        stdout = io.StringIO()
        stderr = io.StringIO()

        output = ""
        try:
            # Execute with captured output
            with contextlib.redirect_stdout(
                stdout
            ), contextlib.redirect_stderr(stderr):

                exec(code, self.globals, self.locals)

            # Get output
            output = stdout.getvalue()
            if stderr.getvalue():
                output += "\n" + stderr.getvalue()

        except Exception as e:
            # Capture exception information
            output = f"Error: {type(e).__name__}: {str(e)}\n"
            output += traceback.format_exc()

        return output
    



if __name__ == "__main__":
    async def async_main():
        # Example usage
        import builtins
        initial_globals = {'__builtins__': builtins}
        initial_locals = {'initial_message': 'Hello from the start!'}

        executor = SimpleCodeExecutor(locals=initial_locals, globals=initial_globals, loop=None)

#         print("--- Initial State ---")
#         print("Locals:", list(executor.locals.keys()))
#         print("-" * 20)

#         # 2. First execution: Import math, define a variable, print
#         code_step_1 = """
# import math
# my_variable = 10 * math.pi
# print(f"Imported math and calculated my_variable: {my_variable:.2f}")
# """
#         print("\n--- Executing Step 1 ---")
#         output_step_1 = await executor.execute(code_step_1)
#         print(output_step_1)

#         print("\n--- State After Step 1 ---")
#         print("Locals:", list(executor.locals.keys())) # Should now include 'math' and 'my_variable'
#         print("-" * 20)


#         # 3. Second execution: Use the imported math and the defined variable
#         code_step_2 = """
# # Use math and my_variable from the previous step
# result = math.sqrt(my_variable)
# print(f"Calculated sqrt of my_variable: {result:.2f}")
# # Return value capture test (last expression)
# result * 2
#     """
#         print("\n--- Executing Step 2 ---")
#         output_step_2 = await executor.execute(code_step_2)
#         print(output_step_2)

#         print("\n--- State After Step 2 ---")
#         print("Locals:", list(executor.locals.keys())) # Should now include 'result'
#         print("-" * 20)

#         # 4. Access the final state directly
#         print("\n--- Final State Check ---")
#         print("Final my_variable:", executor.locals.get('my_variable'))
#         print("Final result:", executor.locals.get('result'))
#         print("Final initial_message:", executor.locals.get('initial_message'))


        print("Testing if conditions: ")
        code_step_3 = """
if True:
    5 + 10
"""  
        output_step_3 = await executor.execute(code_step_3)
        print(output_step_3)
        print("Locals:", list(executor.locals.keys())) # Should now include 'result'

    import asyncio
    asyncio.run(async_main())
