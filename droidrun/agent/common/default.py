from llama_index.core.workflow import step, StartEvent, StopEvent, Workflow, Context
class MockWorkflow(Workflow):
    @step()
    async def sub_start(self, ctx: Context, ev: StartEvent) -> StopEvent:
        return StopEvent(result="This is a mock Workflow")