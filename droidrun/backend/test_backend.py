#!/usr/bin/env python3
"""
Simple test script for DroidRun backend.

Usage:
    python backend/test_backend.py
"""

import asyncio
import json
import sys

import aiohttp


async def test_backend():
    """Test the DroidRun backend API."""
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        print("🧪 Testing DroidRun Backend\n")

        # Test 1: Health check
        print("1️⃣  Testing health check...")
        try:
            async with session.get(f"{base_url}/health") as response:
                data = await response.json()
                print(f"   ✅ Health check passed: {data}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            print("   Make sure the server is running: python -m droidrun.backend")
            return

        # Test 2: Start agent
        print("\n2️⃣  Testing agent start...")
        try:
            agent_config = {
                "goal": "Test goal - list installed apps",
                "reasoning": False,
                "max_steps": 5,
                "debug": True,
                "llms": {
                    "default": {
                        "provider": "GoogleGenAI",
                        "model": "models/gemini-2.5-flash",
                        "temperature": 0.2,
                    }
                },
            }

            async with session.post(
                f"{base_url}/api/agent/run", json=agent_config
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    session_id = data["session_id"]
                    print(f"   ✅ Agent started successfully")
                    print(f"   Session ID: {session_id}")
                else:
                    error = await response.text()
                    print(f"   ❌ Failed to start agent: {error}")
                    return

        except Exception as e:
            print(f"   ❌ Error starting agent: {e}")
            return

        # Test 3: Get status
        print("\n3️⃣  Testing session status...")
        try:
            async with session.get(
                f"{base_url}/api/agent/status/{session_id}"
            ) as response:
                data = await response.json()
                print(f"   ✅ Status retrieved: {data['session']['status']}")
        except Exception as e:
            print(f"   ❌ Error getting status: {e}")

        # Test 4: Stream events (limited)
        print("\n4️⃣  Testing event streaming (first 5 events)...")
        try:
            event_count = 0
            max_events = 5

            async with session.get(
                f"{base_url}/api/agent/stream/{session_id}"
            ) as response:
                async for line in response.content:
                    line = line.decode("utf-8").strip()

                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        try:
                            event_data = json.loads(data)
                            print(f"   📨 Event: {event_type}")

                            event_count += 1
                            if event_count >= max_events:
                                print(f"   ✅ Received {event_count} events")
                                break

                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            print(f"   ⚠️  Event streaming test incomplete: {e}")

        # Test 5: Stop agent
        print("\n5️⃣  Testing agent stop...")
        try:
            async with session.post(
                f"{base_url}/api/agent/stop/{session_id}"
            ) as response:
                data = await response.json()
                print(f"   ✅ Agent stopped: {data['message']}")
        except Exception as e:
            print(f"   ❌ Error stopping agent: {e}")

        # Test 6: List sessions
        print("\n6️⃣  Testing session listing...")
        try:
            async with session.get(f"{base_url}/api/agent/sessions") as response:
                data = await response.json()
                print(f"   ✅ Found {data['total']} sessions")
        except Exception as e:
            print(f"   ❌ Error listing sessions: {e}")

        # Test 7: Get stats
        print("\n7️⃣  Testing backend stats...")
        try:
            async with session.get(f"{base_url}/api/admin/stats") as response:
                data = await response.json()
                print(f"   ✅ Stats retrieved:")
                print(f"      Total sessions: {data['total_sessions']}")
                print(f"      Running sessions: {data['running_sessions']}")
        except Exception as e:
            print(f"   ❌ Error getting stats: {e}")

        print("\n" + "=" * 60)
        print("✅ Backend test completed!")
        print("=" * 60)
        print("\n📚 Next steps:")
        print("   1. Open http://localhost:8000/docs for API documentation")
        print("   2. Open backend/example_frontend.html for live demo")
        print("   3. Build your own frontend using the API")


if __name__ == "__main__":
    print("Make sure the backend server is running:")
    print("  python -m droidrun.backend\n")

    try:
        asyncio.run(test_backend())
    except KeyboardInterrupt:
        print("\n⏹  Test interrupted by user")
        sys.exit(0)
