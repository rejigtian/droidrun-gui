"""Test mid-run external user message injection.

Run with: python tests/test_external_message.py
Requires a connected Android device and configured LLM in ~/.config/droidrun/config.yaml
"""

import asyncio

from droidrun.agent.droid import DroidAgent
from droidrun.agent.droid.events import (
    ExternalUserMessageAppliedEvent,
    ExternalUserMessageDroppedEvent,
)
from droidrun.config_manager.loader import ConfigLoader


async def main():
    config = ConfigLoader.load()
    agent = DroidAgent(
        goal="Open the settings app and check the android version", config=config
    )
    handler = agent.run()

    async def inject_after_delay():
        await asyncio.sleep(10)
        print(
            "\n>>> Sending: 'Actually open Chrome and go to google.com'\n"
        )
        queued = agent.send_user_message(
            "Actually open Chrome and go to google.com"
        )
        print(f"[QUEUED] id={queued.id}")

    task = asyncio.create_task(inject_after_delay())

    async for ev in handler.stream_events():
        if isinstance(ev, ExternalUserMessageAppliedEvent):
            print(
                f"[APPLIED] ids={ev.message_ids} consumer={ev.consumer} step={ev.step_number}"
            )
        elif isinstance(ev, ExternalUserMessageDroppedEvent):
            print(f"[DROPPED] ids={ev.message_ids} reason={ev.reason}")

    result = await handler
    task.cancel()

    print(
        f"\nResult: success={result.success} reason={result.reason} steps={result.steps}"
    )


if __name__ == "__main__":
    asyncio.run(main())
