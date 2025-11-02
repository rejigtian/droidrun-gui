"""Production-ready Langfuse span processor with image upload support.

This module provides a custom OpenTelemetry span processor that:
- Uploads images to Langfuse blob storage (S3/Azure/GCS)
- Transforms LlamaIndex block-based messages to Langfuse content format
- Auto-scales from 3 to 50 worker threads based on load
- Uses HTTP connection pooling for performance
- Operates silently (warnings and errors only)

Usage:
    from droidrun.telemetry.langfuse_processor import LangfuseSpanProcessor

    processor = LangfuseSpanProcessor(
        public_key="pk-lf-...",
        secret_key="sk-lf-...",
        base_url="https://cloud.langfuse.com",
    )
"""

import base64
import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

import requests
from opentelemetry.sdk.trace import ReadableSpan

from langfuse._client.span_processor import LangfuseSpanProcessor as BaseLangfuseSpanProcessor

from droidrun import __version__

if TYPE_CHECKING:
    from droidrun import DroidAgent
# Configuration constants
MAX_IMAGE_SIZE_KB = 10000  # 10MB max per image
MAX_UPLOAD_WORKERS = 50  # Maximum concurrent upload threads
SHUTDOWN_TIMEOUT = 30  # Seconds to wait for pending uploads on shutdown

# Use DroidRun's logger
logger = logging.getLogger("droidrun")


class LangfuseSpanProcessor(BaseLangfuseSpanProcessor):
    """
    Production span processor with image upload and message formatting.

    Extends the base LangfuseSpanProcessor with:
    - Auto-scaling thread pool (3-50 workers based on load)
    - Image upload to blob storage with deduplication
    - Message format transformation (blocks → content)
    """

    def __init__(
        self,
        *,
        public_key: str,
        secret_key: str,
        base_url: str,
        timeout: Optional[int] = None,
        flush_at: Optional[int] = None,
        flush_interval: Optional[float] = None,
        blocked_instrumentation_scopes: Optional[List[str]] = None,
        additional_headers: Optional[dict] = None,

        agent: Optional["DroidAgent"] = None,
    ):
        """Initialize the span processor with media upload support.

        Args:
            agent: Optional DroidAgent instance for accessing agent context during span processing.
        """
        super().__init__(
            public_key=public_key,
            secret_key=secret_key,
            base_url=base_url,
            timeout=timeout,
            flush_at=flush_at,
            flush_interval=flush_interval,
            blocked_instrumentation_scopes=blocked_instrumentation_scopes,
            additional_headers=additional_headers,
        )

        # Store agent instance for context access
        self.agent = agent

        # Store credentials for media API calls
        self._base_url = base_url
        auth_string = f"{public_key}:{secret_key}"
        self._auth_header = "Basic " + base64.b64encode(auth_string.encode()).decode()

        # HTTP connection pooling (shared across all threads)
        self._http_session = requests.Session()
        self._http_session.headers.update(
            {
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
            }
        )
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=3, # Increase this if hosting on server with multiple users
            pool_maxsize=10, # Increase this if hosting on server with multiple users (task api)
            max_retries=3,
        )
        self._http_session.mount("http://", adapter)
        self._http_session.mount("https://", adapter)

        self._executor = ThreadPoolExecutor(
            max_workers=MAX_UPLOAD_WORKERS,
            thread_name_prefix="LangfuseMediaUpload",
        )

        self._pending_uploads: List[Future] = []
        self._pending_lock = threading.Lock()

    # Agent metadata extraction
    def _extract_agent_metadata(self) -> Optional[dict]:
        """Extract metadata from DroidAgent for first span injection."""
        if not self.agent:
            return None

        try:
            metadata = {}

            # 1. Goal
            if self.agent.shared_state.instruction:
                metadata['goal'] = self.agent.shared_state.instruction

            # 2. Reasoning mode
            metadata['reasoning'] = self.agent.config.agent.reasoning

            # 3. Device info
            if self.agent.config.device:
                device = self.agent.config.device
                metadata['device'] = {
                    'platform': device.platform,
                    'serial': device.serial,
                    'use_tcp': device.use_tcp,
                }

            # 4. Output model (structured output)
            if self.agent.output_model:
                metadata['output_model'] = self.agent.output_model.__name__

            # 5. DroidRun version
            metadata['droidrun_version'] = __version__

            # 6. After action sleep
            if self.agent.config.agent.after_sleep_action:
                metadata['after_action_sleep'] = self.agent.config.agent.after_sleep_action

            # 7. Active LLMs (only active ones based on reasoning mode) - LAST
            active_llms = []
            if self.agent.config.agent.reasoning:
                # Reasoning mode uses manager, executor, scripter
                llm_attrs = ['manager_llm', 'executor_llm']
                if self.agent.config.agent.scripter.enabled:
                    llm_attrs.append('scripter_llm')
            else:
                # Direct mode uses codeact
                llm_attrs = ['codeact_llm']

            # Add helper LLMs
            llm_attrs.extend(['text_manipulator_llm', 'app_opener_llm'])

            # Add structured_output if output_model is present
            if self.agent.output_model:
                llm_attrs.append('structured_output_llm')

            for llm_attr in llm_attrs:
                llm = getattr(self.agent, llm_attr)
                if llm:
                    llm_info = {
                        'role': llm_attr.replace('_llm', ''),
                        'provider': llm.class_name() if hasattr(llm, 'class_name') else 'unknown',
                    }

                    # Extract model name
                    if hasattr(llm, 'model'):
                        llm_info['model'] = llm.model
                    elif hasattr(llm, 'metadata') and hasattr(llm.metadata, 'model_name'):
                        llm_info['model'] = llm.metadata.model_name

                    # Extract temperature
                    if hasattr(llm, 'temperature'):
                        llm_info['temperature'] = llm.temperature

                    active_llms.append(llm_info)

            metadata['llms'] = active_llms

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract agent metadata: {e}")
            return None

    # Media API
    def _submit_upload(self, job: dict):
        """Submit upload job to thread pool (non-blocking)."""
        try:
            future = self._executor.submit(self._upload_media_to_langfuse, job)

            with self._pending_lock:
                self._pending_uploads.append(future)

            future.add_done_callback(self._cleanup_future)

        except Exception as e:
            logger.error(f"Failed to submit media upload: {e}")

    def _cleanup_future(self, future: Future):
        """Remove completed future from tracking list."""
        with self._pending_lock:
            try:
                self._pending_uploads.remove(future)
            except ValueError:
                pass

    def _upload_media_to_langfuse(self, job: dict):
        """Upload media to Langfuse blob storage."""
        try:
            # Step 1: Request presigned upload URL
            upload_response = self._request_upload_url(
                media_id=job["media_id"],
                content_type=job["content_type"],
                content_length=job["content_length"],
                sha256_hash=job["sha256_hash"],
                trace_id=job["trace_id"],
                observation_id=job.get("observation_id"),
                field=job["field"],
            )

            if not upload_response or not upload_response.get("uploadUrl"):
                # Media already exists (deduplication)
                return

            upload_url = upload_response["uploadUrl"]

            # Step 2: Upload to blob storage (S3/Azure/GCS)
            headers = {"Content-Type": job["content_type"]}

            # GCS doesn't support these headers
            if "storage.googleapis.com" not in upload_url:
                headers["x-ms-blob-type"] = "BlockBlob"
                headers["x-amz-checksum-sha256"] = job["sha256_hash"]

            response = self._http_session.put(
                upload_url, headers=headers, data=job["content_bytes"]
            )

            # Step 3: Notify Langfuse of upload completion
            if response.status_code in (200, 201):
                self._notify_upload_complete(job["media_id"], response.status_code)
            else:
                logger.error(
                    f"Media upload failed for {job['media_id']}: "
                    f"HTTP {response.status_code} - {response.text}"
                )

        except Exception as e:
            logger.error(f"Failed to upload media {job['media_id']}: {e}")

    def _request_upload_url(
        self,
        media_id: str,
        content_type: str,
        content_length: int,
        sha256_hash: str,
        trace_id: str,
        observation_id: Optional[str],
        field: str,
    ) -> Optional[dict]:
        """Request presigned upload URL from Langfuse API."""
        try:
            url = f"{self._base_url}/api/public/media"
            payload = {
                "traceId": trace_id,
                "observationId": observation_id,
                "contentType": content_type,
                "contentLength": content_length,
                "sha256Hash": sha256_hash,
                "field": field,
            }

            response = self._http_session.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 201:
                data = response.json()
                if data.get("uploadUrl") is None:
                    # media already exists (deduplication)
                    return None
                return data
            else:
                logger.error(
                    f"Failed to request upload URL: HTTP {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error requesting upload URL: {e}")
            return None

    def _notify_upload_complete(self, media_id: str, status_code: int):
        """Notify Langfuse that upload completed."""
        try:
            url = f"{self._base_url}/api/public/media/{media_id}"
            payload = {
                "uploadedAt": datetime.now(timezone.utc).isoformat(),
                "uploadHttpStatus": status_code,
            }

            response = self._http_session.patch(url, json=payload, timeout=10)

            if response.status_code != 200:
                logger.warning(
                    f"Failed to notify upload complete: HTTP {response.status_code}"
                )

        except Exception as e:
            logger.error(f"Error notifying upload complete: {e}")

    def shutdown(self):
        """Override shutdown to wait for pending media uploads."""

        self._executor.shutdown(wait=False, cancel_futures=False)

        # Wait for pending uploads with timeout
        deadline = time.time() + SHUTDOWN_TIMEOUT
        all_done = False

        while time.time() < deadline:
            with self._pending_lock:
                pending = [f for f in self._pending_uploads if not f.done()]
                pending_count = len(pending)

            if pending_count == 0:
                all_done = True
                break

            time.sleep(0.1)

        if not all_done:
            with self._pending_lock:
                pending_count = len([f for f in self._pending_uploads if not f.done()])
            logger.warning(
                f"Langfuse shutdown timeout after {SHUTDOWN_TIMEOUT}s - "
                f"{pending_count} media uploads still pending"
            )

        self._http_session.close()

        super().shutdown()

    def _inject_executor_metadata(self, span: ReadableSpan) -> None:
        """Inject ExecutorAgent metadata into prepare_context span's input.value."""
        if not self.agent:
            return

        try:
            # Extract subgoal from span attributes
            if not hasattr(span, '_attributes') or span._attributes is None:
                return

            attrs = span._attributes

            # Try to get subgoal from input.value if it exists
            subgoal = "Unknown"
            if "input.value" in attrs:
                try:
                    input_data = json.loads(attrs["input.value"])
                    subgoal = input_data.get("subgoal", "Unknown")
                except (json.JSONDecodeError, TypeError):
                    pass

            metadata = {
                "subgoal": subgoal
            }

            # Serialize and inject
            metadata_json = json.dumps(metadata, indent=2)
            span._attributes["input.value"] = metadata_json

        except Exception as e:
            logger.warning(f"Failed to inject metadata into ExecutorAgent span: {e}")

    def _inject_manager_metadata(self, span: ReadableSpan) -> None:
        """Inject ManagerAgent metadata into prepare_context span's input.value."""
        if not self.agent:
            return

        try:
            if not hasattr(span, '_attributes') or span._attributes is None:
                return

            # Calculate memory size and message history count
            memory_size = 0
            if self.agent.shared_state.memory:
                memory_size = len(self.agent.shared_state.memory)

            message_history_count = len(self.agent.shared_state.message_history) + 1  # +1 for system prompt

            metadata = {
                "memory_size": memory_size,
                "message_history_count": message_history_count
            }

            # Serialize and inject
            metadata_json = json.dumps(metadata, indent=2)
            span._attributes["input.value"] = metadata_json

            # Add error recovery as tag
            tags = []
            if self.agent.shared_state.error_flag_plan:
                tags.append("error_recovery")

            if tags:
                span._attributes["langfuse.trace.tags"] = tags

        except Exception as e:
            logger.warning(f"Failed to inject metadata into ManagerAgent span: {e}")

    def _inject_metadata_to_start_handler(self, span: ReadableSpan) -> None:
        """Inject DroidAgent metadata into start_handler span's input.value."""
        if not self.agent:
            return

        try:
            metadata = self._extract_agent_metadata()
            if not metadata:
                return

            # Inject metadata into span attributes
            if hasattr(span, '_attributes') and span._attributes is not None:
                # Serialize metadata to JSON
                metadata_json = json.dumps(metadata, indent=2)

                # Inject into input.value
                span._attributes["input.value"] = metadata_json

                # Add reasoning mode as tag
                tags = []
                if metadata.get('reasoning'):
                    tags.append("reasoning")
                else:
                    tags.append("fast")

                span._attributes["langfuse.trace.tags"] = tags

        except Exception as e:
            logger.warning(f"Failed to inject metadata into start_handler span: {e}")

    # Span processing
    def on_end(self, span: ReadableSpan) -> None:
        """Override on_end to apply custom formatting and inject metadata."""
        if self._is_langfuse_span(span) and not self._is_langfuse_project_span(span):
            return

        if self._is_blocked_instrumentation_scope(span):
            return

        try:
            # Inject metadata into agent spans
            if span.name == "DroidAgent.run":
                self._inject_metadata_to_start_handler(span)
            elif span.name == "ExecutorAgent.run":
                self._inject_executor_metadata(span)
            elif span.name == "ManagerAgent.run":
                self._inject_manager_metadata(span)
            # Format LLM chat spans
            elif span.name.endswith(".achat") or span.name.endswith(".chat"):
                self._format_chat(span)
            elif span.name.endswith(".complete") or span.name.endswith(".acomplete"):
                self._format_complete(span)
        except Exception as e:
            logger.error(f"Error processing span for Langfuse: {e}")

        super(BaseLangfuseSpanProcessor, self).on_end(span)
    def _format_complete(self, span: ReadableSpan) -> None:
        span._attributes["input.value"] = span._attributes["llm.prompts"][0]
        del span._attributes["llm.prompts"]
        pass
    def _format_chat(self, span: ReadableSpan) -> None:
        """
        Apply custom formatting to transform blocks and set Langfuse attributes.

        Processes both input.value and output.value attributes:
        - Plain strings: Set langfuse.observation.{field} directly
        - JSON with blocks: Transform blocks to content format (images, tool calls, etc.)
        - JSON without blocks: Set langfuse.observation.{field} as-is
        """
        if not hasattr(span, "_attributes") or span._attributes is None:
            return

        attrs = span._attributes
        trace_id = format(span.context.trace_id, "032x")

        self._process_field(attrs, trace_id, "input")
        self._process_field(attrs, trace_id, "output")

    # Message transformation
    def _process_field(self, attrs: dict, trace_id: str, field: str) -> None:
        """Process input or output field - handle both JSON messages and plain strings."""
        field_key = f"{field}.value"

        if field_key not in attrs:
            return

        value = attrs[field_key]
        if not isinstance(value, str):
            return

        # Try parsing as JSON with messages
        try:
            data = json.loads(value)

            # Check if it has messages with blocks that need transformation
            if self._has_blocks_to_transform(data):
                self._transform_and_set_field(attrs, trace_id, field, data)
                return

        except (json.JSONDecodeError, ValueError):
            pass


        attrs[f"langfuse.observation.{field}"] = value

    def _has_blocks_to_transform(self, data: dict) -> bool:
        """Check if data contains messages with blocks that need transformation."""
        if not isinstance(data, dict) or "messages" not in data:
            return False

        messages = data["messages"]
        if not isinstance(messages, list):
            return False

        return any(
            isinstance(msg, dict) and "blocks" in msg
            for msg in messages
        )

    def _transform_and_set_field(
        self, attrs: dict, trace_id: str, field: str, data: dict
    ) -> None:
        """Transform blocks to content and set Langfuse attributes."""
        # Remove legacy LLM message attributes
        prefix = f"llm.{field}_messages."
        keys_to_remove = [key for key in attrs if key.startswith(prefix)]
        for key in keys_to_remove:
            del attrs[key]

        # Transform and set
        formatted = self._transform_blocks_to_content(data, trace_id, field)
        attrs[f"langfuse.observation.{field}"] = formatted
        attrs[f"{field}.value"] = formatted

    def _transform_blocks_to_content(
        self, data: dict, trace_id: str, field: str
    ) -> str:
        """Transform parsed message data from blocks to content format."""
        processed = self._convert_message_array(data["messages"], trace_id, field)
        return json.dumps({"messages": json.loads(processed)})

    def _convert_message_array(
        self, messages: list, trace_id: str, field: str
    ) -> str:
        """Convert message array from blocks format to content format."""
        restructured_messages = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            if "content" in msg and "blocks" not in msg:
                restructured_messages.append(msg)
                continue

            if "json" in msg and isinstance(msg["json"], dict) and "blocks" in msg["json"]:
                msg = msg.copy()
                msg.update(msg["json"])
                del msg["json"]

            if "blocks" not in msg or "role" not in msg:
                if "role" in msg:
                    restructured_messages.append(msg)
                continue

            role = msg["role"]
            blocks = msg["blocks"]

            if not isinstance(blocks, list) or len(blocks) == 0:
                restructured_messages.append(msg)
                continue

            if (
                len(blocks) == 1
                and isinstance(blocks[0], dict)
                and blocks[0].get("block_type") == "text"
                and "text" in blocks[0]
            ):
                restructured_messages.append(
                    {"role": role, "content": blocks[0]["text"]}
                )
            else:
                content_blocks = self._convert_blocks_to_content(
                    blocks, trace_id, field
                )

                if content_blocks:
                    restructured_messages.append(
                        {"role": role, "content": content_blocks}
                    )
                else:
                    restructured_messages.append(msg)

        return json.dumps(restructured_messages)

    def _convert_blocks_to_content(
        self,
        blocks: list,
        trace_id: str,
        field: str,
    ) -> list:
        """Convert LlamaIndex blocks to Langfuse content blocks."""
        content_blocks = []

        for block in blocks:
            if not isinstance(block, dict) or "block_type" not in block:
                continue

            block_type = block["block_type"]

            if block_type == "text":
                if "text" in block:
                    content_blocks.append({"type": "text", "text": block["text"]})

            elif block_type == "image":
                image_block = self._upload_image_to_storage(
                    block, trace_id, field
                )
                if image_block:
                    content_blocks.append(image_block)

            elif block_type == "tool_call":
                if "tool_name" in block and "tool_kwargs" in block:
                    content_blocks.append(
                        {
                            "type": "tool_call",
                            "tool_call": {
                                "name": block["tool_name"],
                                "arguments": block["tool_kwargs"],
                            },
                        }
                    )

        return content_blocks

    # Image upload
    def _upload_image_to_storage(
        self,
        block: dict,
        trace_id: str,
        field: str,
    ) -> Optional[dict]:
        """Upload image to blob storage and return media reference."""
        if "image" in block and block["image"] is not None:
            image_base64 = block["image"]
            mime_type = block.get("image_mimetype")

            if not mime_type:
                logger.warning("Image missing MIME type, skipping upload")
                return None

            try:
                image_bytes = base64.b64decode(image_base64)
                size_kb = len(image_bytes) / 1024

                if size_kb > MAX_IMAGE_SIZE_KB:
                    logger.warning(
                        f"Image size ({size_kb:.1f}KB) exceeds limit ({MAX_IMAGE_SIZE_KB}KB), skipping upload"
                    )
                    return None

                sha256_hash_bytes = hashlib.sha256(image_bytes).digest()
                sha256_hash = base64.b64encode(sha256_hash_bytes).decode()
                media_id = (
                    sha256_hash.replace("+", "-").replace("/", "_").rstrip("=")[:22]
                )

                self._submit_upload(
                    {
                        "media_id": media_id,
                        "content_bytes": image_bytes,
                        "content_type": mime_type,
                        "content_length": len(image_bytes),
                        "sha256_hash": sha256_hash,
                        "trace_id": trace_id,
                        "observation_id": None,
                        "field": field,
                    }
                )

                reference_string = (
                    f"@@@langfuseMedia:type={mime_type}|id={media_id}|source=bytes@@@"
                )
                return {
                    "type": "image_url",
                    "image_url": {"url": reference_string},
                }

            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                return None

        if "url" in block and block["url"] is not None:
            return {"type": "image_url", "image_url": {"url": block["url"]}}

        if "path" in block and block["path"] is not None:
            logger.warning(f"Using file path for image - may not work on server: {block['path']}")
            return {
                "type": "image_url",
                "image_url": {"url": f"file://{block['path']}"},
            }

        return None
