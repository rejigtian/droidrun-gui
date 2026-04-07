"""Standalone OpenAI OAuth subclass for LlamaIndex.

Usage:
    from openai_oauth_llm import OpenAIOAuth

    llm = OpenAIOAuth(
        auth_model="openai-codex/gpt-5.4",
        custom_model="gpt-5.4",  # optional override
        oauth_refresh_token="rt_...",
        oauth_access_token="eyJ...",  # optional if cached file already exists
        oauth_credential_path=str(OPENAI_OAUTH_CREDENTIAL_PATH),
    )
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import httpx
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, LLMMetadata, MessageRole
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai.base import llm_retry_decorator
from llama_index.llms.openai.utils import to_openai_message_dicts
from droidrun.config_manager.credential_paths import OPENAI_OAUTH_CREDENTIAL_PATH

DEFAULT_OPENAI_OAUTH_ISSUER = "https://auth.openai.com"
DEFAULT_OPENAI_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
DEFAULT_OPENAI_OAUTH_CREDENTIAL_PATH = OPENAI_OAUTH_CREDENTIAL_PATH
DEFAULT_AUTH_MODEL = "openai-codex/gpt-5.4"
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"
DEFAULT_CODEX_API_BASE = "https://chatgpt.com/backend-api/codex"
DEFAULT_BACKEND_API_BASE = "https://chatgpt.com/backend-api"
DEFAULT_OPENAI_OAUTH_CALLBACK_HOST = "localhost"
DEFAULT_OPENAI_OAUTH_CALLBACK_PORT = 1455
DEFAULT_OPENAI_OAUTH_CALLBACK_PATH = "/auth/callback"
DEFAULT_OPENAI_OAUTH_SCOPE = (
    "openid profile email offline_access api.connectors.read api.connectors.invoke"
)


def _b64_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _pkce_pair() -> tuple[str, str]:
    verifier = _b64_no_pad(secrets.token_bytes(64))
    challenge = _b64_no_pad(hashlib.sha256(verifier.encode("utf-8")).digest())
    return verifier, challenge


@dataclass
class OpenAIOAuthCredentials:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at_ms: Optional[int] = None
    account_id: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "OpenAIOAuthCredentials":
        access_token = payload.get("access") or payload.get("access_token")
        if not access_token:
            raise ValueError("OpenAI OAuth payload missing access token.")

        refresh_token = payload.get("refresh") or payload.get("refresh_token")
        account_id = payload.get("account_id")

        raw_expires = payload.get("expires")
        expires_at_ms: Optional[int]
        if raw_expires is None:
            expires_at_ms = None
        else:
            try:
                expires_at_ms = int(raw_expires)
            except (TypeError, ValueError):
                expires_at_ms = None

        return cls(
            access_token=str(access_token),
            refresh_token=str(refresh_token) if refresh_token else None,
            expires_at_ms=expires_at_ms,
            account_id=str(account_id) if account_id else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "oauth",
            "provider": "openai-chatgpt",
            "access": self.access_token,
            "refresh": self.refresh_token,
            "expires": self.expires_at_ms,
            "account_id": self.account_id,
        }

    def is_valid(self, skew_ms: int = 60_000) -> bool:
        if not self.access_token:
            return False
        if self.expires_at_ms is None:
            return True
        return int(time.time() * 1000) + skew_ms < self.expires_at_ms


class OpenAIOAuthCredentialStore:
    def __init__(self, path: str | Path = DEFAULT_OPENAI_OAUTH_CREDENTIAL_PATH) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> Optional[OpenAIOAuthCredentials]:
        if not self.path.exists():
            return None

        payload = json.loads(self.path.read_text())
        try:
            return OpenAIOAuthCredentials.from_payload(payload)
        except ValueError:
            return None

    def save(self, credentials: OpenAIOAuthCredentials) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        payload = json.dumps(credentials.to_dict(), indent=2)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass


class OpenAIOAuthSessionManager:
    def __init__(
        self,
        *,
        issuer: str = DEFAULT_OPENAI_OAUTH_ISSUER,
        client_id: str = DEFAULT_OPENAI_OAUTH_CLIENT_ID,
        credential_store: Optional[OpenAIOAuthCredentialStore] = None,
        request_timeout: float = 15.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.request_timeout = request_timeout
        self.credential_store = credential_store or OpenAIOAuthCredentialStore()
        self.http_client = http_client
        self._lock = threading.Lock()
        self._credentials: Optional[OpenAIOAuthCredentials] = None

    @staticmethod
    def _jwt_claims(token: str) -> Dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            return {}

        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        try:
            raw = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
            claims = json.loads(raw)
            return claims if isinstance(claims, dict) else {}
        except Exception:
            return {}

    @classmethod
    def _extract_account_id(cls, token: str) -> Optional[str]:
        claims = cls._jwt_claims(token)

        auth_claims = claims.get("https://api.openai.com/auth")
        if isinstance(auth_claims, dict):
            nested = auth_claims.get("chatgpt_account_id")
            if isinstance(nested, str) and nested:
                return nested

        direct = claims.get("chatgpt_account_id")
        if isinstance(direct, str) and direct:
            return direct

        orgs = claims.get("organizations")
        if isinstance(orgs, list) and orgs:
            first = orgs[0]
            if isinstance(first, dict):
                org_id = first.get("id")
                if isinstance(org_id, str) and org_id:
                    return org_id

        return None

    @classmethod
    def _compute_expiry_ms(cls, token: str, expires_in: Optional[Any]) -> Optional[int]:
        if expires_in is not None:
            try:
                return int(time.time() * 1000) + int(expires_in) * 1000
            except (TypeError, ValueError):
                pass

        claims = cls._jwt_claims(token)
        exp = claims.get("exp")
        if isinstance(exp, (int, float)):
            return int(exp * 1000)
        return None

    def set_initial_credentials(self, credentials: OpenAIOAuthCredentials) -> None:
        with self._lock:
            self._credentials = credentials
            self.credential_store.save(credentials)

    def _load_cached_credentials(self) -> Optional[OpenAIOAuthCredentials]:
        if self._credentials is not None:
            return self._credentials

        cached = self.credential_store.load()
        if cached is not None:
            self._credentials = cached
        return cached

    def _refresh(self, refresh_token: str) -> OpenAIOAuthCredentials:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        if self.http_client is not None:
            response = self.http_client.post(
                f"{self.issuer}/oauth/token",
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=self.request_timeout,
            )
        else:
            response = httpx.post(
                f"{self.issuer}/oauth/token",
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=self.request_timeout,
            )

        response.raise_for_status()
        payload = response.json()

        access = payload.get("access_token")
        if not isinstance(access, str) or not access:
            raise RuntimeError("OpenAI OAuth refresh response missing access_token.")

        new_refresh = payload.get("refresh_token")
        if not isinstance(new_refresh, str) or not new_refresh:
            new_refresh = refresh_token

        expires_at_ms = self._compute_expiry_ms(access, payload.get("expires_in"))
        id_or_access = payload.get("id_token") if isinstance(payload.get("id_token"), str) else access
        account_id = self._extract_account_id(id_or_access)

        return OpenAIOAuthCredentials(
            access_token=access,
            refresh_token=new_refresh,
            expires_at_ms=expires_at_ms,
            account_id=account_id,
        )

    def get_valid_credentials(self, skew_ms: int = 60_000) -> OpenAIOAuthCredentials:
        with self._lock:
            cached = self._load_cached_credentials()
            if cached is not None and cached.is_valid(skew_ms=skew_ms):
                return cached

            if cached is None or not cached.refresh_token:
                raise ValueError(
                    "No valid OpenAI OAuth credentials found. Provide a refresh token or a cached credential file."
                )

            refreshed = self._refresh(cached.refresh_token)
            self._credentials = refreshed
            self.credential_store.save(refreshed)
            return refreshed

    def exchange_authorization_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> OpenAIOAuthCredentials:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }

        if self.http_client is not None:
            response = self.http_client.post(
                f"{self.issuer}/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                timeout=self.request_timeout,
            )
        else:
            response = httpx.post(
                f"{self.issuer}/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                timeout=self.request_timeout,
            )

        response.raise_for_status()
        payload = response.json()

        access = payload.get("access_token")
        if not isinstance(access, str) or not access:
            raise RuntimeError("OpenAI OAuth code exchange response missing access_token.")

        refresh = payload.get("refresh_token")
        credentials = OpenAIOAuthCredentials(
            access_token=access,
            refresh_token=refresh if isinstance(refresh, str) and refresh else None,
            expires_at_ms=self._compute_expiry_ms(access, payload.get("expires_in")),
            account_id=self._extract_account_id(
                payload.get("id_token")
                if isinstance(payload.get("id_token"), str)
                else access
            ),
        )
        self.set_initial_credentials(credentials)
        return credentials


class OpenAIOAuth(OpenAI):
    """OpenAI LLM backed by ChatGPT OAuth refresh/access tokens."""

    @classmethod
    def class_name(cls) -> str:
        return "OpenAIOAuth"

    @property
    def metadata(self) -> LLMMetadata:
        # Codex model IDs are not always in llama-index's static OpenAI map.
        return LLMMetadata(
            context_window=400000,
            num_output=self.max_tokens or -1,
            is_chat_model=True,
            is_function_calling_model=True,
            model_name=self.model,
            system_role=MessageRole.SYSTEM,
        )

    @staticmethod
    def _resolve_model_name(
        *,
        auth_model: str,
        custom_model: Optional[str],
        model: Optional[str],
    ) -> str:
        if custom_model and custom_model.strip():
            return custom_model.strip()
        if model and model.strip():
            return model.strip()

        alias = auth_model.strip()
        if "/" in alias:
            return alias.split("/", 1)[1].strip()
        if alias:
            return alias

        return "gpt-5.4"

    @staticmethod
    def _build_auth_url(
        *,
        issuer: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        scope: str = DEFAULT_OPENAI_OAUTH_SCOPE,
    ) -> str:
        query = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "id_token_add_organizations": "true",
            "codex_cli_simplified_flow": "true",
            "state": state,
            "originator": "codex_cli_rs",
        }
        return f"{issuer.rstrip('/')}/oauth/authorize?{urlencode(query)}"

    def __init__(
        self,
        auth_model: str = DEFAULT_AUTH_MODEL,
        custom_model: Optional[str] = None,
        model: Optional[str] = None,
        oauth_refresh_token: Optional[str] = None,
        oauth_access_token: Optional[str] = None,
        oauth_expires_at_ms: Optional[int] = None,
        oauth_account_id: Optional[str] = None,
        oauth_credential_path: Optional[str] = None,
        oauth_client_id: str = DEFAULT_OPENAI_OAUTH_CLIENT_ID,
        oauth_issuer: str = DEFAULT_OPENAI_OAUTH_ISSUER,
        oauth_refresh_skew_seconds: int = 60,
        use_chatgpt_account_header: bool = False,
        **kwargs: Any,
    ) -> None:
        resolved_model = self._resolve_model_name(
            auth_model=auth_model,
            custom_model=custom_model,
            model=model,
        )

        seed_api_key = oauth_access_token or kwargs.pop("api_key", None) or "oauth"
        kwargs.setdefault("api_base", DEFAULT_OPENAI_API_BASE)
        super().__init__(model=resolved_model, api_key=seed_api_key, **kwargs)
        object.__setattr__(
            self, "_oauth_refresh_skew_ms", max(0, int(oauth_refresh_skew_seconds)) * 1000
        )
        object.__setattr__(self, "_use_chatgpt_account_header", use_chatgpt_account_header)
        object.__setattr__(self, "_oauth_account_id", oauth_account_id)
        object.__setattr__(self, "_active_access_token", None)
        object.__setattr__(self, "_responses_api_base", DEFAULT_CODEX_API_BASE)

        store = OpenAIOAuthCredentialStore(
            oauth_credential_path or DEFAULT_OPENAI_OAUTH_CREDENTIAL_PATH
        )
        self._oauth_manager = OpenAIOAuthSessionManager(
            issuer=oauth_issuer,
            client_id=oauth_client_id,
            credential_store=store,
            request_timeout=self.timeout,
            http_client=self._http_client,
        )

        if oauth_access_token or oauth_refresh_token:
            self._oauth_manager.set_initial_credentials(
                OpenAIOAuthCredentials(
                    access_token=oauth_access_token or seed_api_key,
                    refresh_token=oauth_refresh_token,
                    expires_at_ms=oauth_expires_at_ms,
                    account_id=oauth_account_id,
                )
            )

    def login(
        self,
        *,
        open_browser: bool = True,
        timeout_seconds: float = 300.0,
        callback_host: str = DEFAULT_OPENAI_OAUTH_CALLBACK_HOST,
        callback_port: int = DEFAULT_OPENAI_OAUTH_CALLBACK_PORT,
        callback_path: str = DEFAULT_OPENAI_OAUTH_CALLBACK_PATH,
        redirect_host: str = DEFAULT_OPENAI_OAUTH_CALLBACK_HOST,
        scope: str = DEFAULT_OPENAI_OAUTH_SCOPE,
    ) -> OpenAIOAuthCredentials:
        result: Dict[str, Optional[str]] = {"code": None, "state": None, "error": None}
        done = threading.Event()
        code_verifier, code_challenge = _pkce_pair()
        state = _b64_no_pad(secrets.token_bytes(32))

        class _OAuthHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != callback_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                params = parse_qs(parsed.query)
                result["code"] = params.get("code", [None])[0]
                result["state"] = params.get("state", [None])[0]
                result["error"] = params.get("error", [None])[0]

                ok = result["code"] is not None and result["error"] is None
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                if ok:
                    self.wfile.write(
                        b"<html><body><h3>Login complete. You can close this tab.</h3></body></html>"
                    )
                else:
                    self.wfile.write(
                        b"<html><body><h3>Login failed. Return to your terminal.</h3></body></html>"
                    )
                done.set()

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        httpd = HTTPServer((callback_host, callback_port), _OAuthHandler)
        actual_port = httpd.server_address[1]
        redirect_uri = f"http://{redirect_host}:{actual_port}{callback_path}"
        auth_url = self._build_auth_url(
            issuer=self._oauth_manager.issuer,
            client_id=self._oauth_manager.client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
            scope=scope,
        )

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        try:
            if open_browser:
                webbrowser.open(auth_url)
            else:
                print(f"Open this URL to login:\n{auth_url}")

            if not done.wait(timeout=timeout_seconds):
                raise TimeoutError("OAuth login timed out before callback was received.")
            if result["error"]:
                raise RuntimeError(f"OAuth callback returned error: {result['error']}")
            if result["state"] != state:
                raise RuntimeError("OAuth callback state mismatch.")
            if not result["code"]:
                raise RuntimeError("OAuth callback did not include an authorization code.")

            creds = self._oauth_manager.exchange_authorization_code(
                code=result["code"],
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
            )
            if creds.account_id:
                object.__setattr__(self, "_oauth_account_id", creds.account_id)
            return creds
        finally:
            httpd.shutdown()
            httpd.server_close()

    def _ensure_access_token(self) -> OpenAIOAuthCredentials:
        creds = self._oauth_manager.get_valid_credentials(skew_ms=self._oauth_refresh_skew_ms)

        if self._active_access_token != creds.access_token:
            self._active_access_token = creds.access_token
            self.api_key = creds.access_token
            self._client = None
            self._aclient = None

        if creds.account_id and not self._oauth_account_id:
            self._oauth_account_id = creds.account_id

        if self.api_base != self._responses_api_base:
            self.api_base = self._responses_api_base
            self._client = None
            self._aclient = None

        return creds

    def _get_client(self):  # type: ignore[override]
        self._ensure_access_token()
        return super()._get_client()

    def _get_aclient(self):  # type: ignore[override]
        self._ensure_access_token()
        return super()._get_aclient()

    def _get_credential_kwargs(self, is_async: bool = False) -> Dict[str, Any]:
        creds = self._ensure_access_token()
        kwargs = super()._get_credential_kwargs(is_async=is_async)
        kwargs["api_key"] = creds.access_token

        headers = dict(self.default_headers or {})
        headers.setdefault("originator", "codex_cli_rs")
        headers.setdefault("Accept", "application/json")
        account_id = self._oauth_account_id or creds.account_id
        if self._use_chatgpt_account_header and account_id:
            headers["ChatGPT-Account-Id"] = account_id
        kwargs["default_headers"] = headers or None

        return kwargs


    def _resolve_codex_instructions(self, messages: list[ChatMessage]) -> str:
        system_parts: list[str] = []
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                continue
            content = msg.content
            if isinstance(content, str) and content.strip():
                system_parts.append(content.strip())
        return "\n\n".join(system_parts) if system_parts else "You are a helpful coding assistant."

    def _build_responses_payload(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        non_system_messages = [m for m in messages if m.role != MessageRole.SYSTEM]
        try:
            payload_raw = to_openai_message_dicts(
                non_system_messages,
                model=self.model,
                is_responses_api=True,
                store=False,
            )
        except TypeError:
            payload_raw = to_openai_message_dicts(
                non_system_messages,
                model=self.model,
                is_responses_api=True,
            )

        if isinstance(payload_raw, str):
            payload: list[dict[str, Any]] = [{"role": "user", "content": payload_raw}]
        else:
            payload = payload_raw

        normalized: list[dict[str, Any]] = []
        for item in payload:
            role = str(item.get("role", "user"))
            content = item.get("content")

            if isinstance(content, str):
                text_type = "input_text" if role == "user" else "output_text"
                normalized.append({**item, "content": [{"type": text_type, "text": content}]})
                continue

            if isinstance(content, list):
                fixed: list[Any] = []
                for entry in content:
                    if (
                        isinstance(entry, dict)
                        and entry.get("type") == "text"
                        and isinstance(entry.get("text"), str)
                    ):
                        text_type = "input_text" if role == "user" else "output_text"
                        fixed.append({**entry, "type": text_type})
                    else:
                        fixed.append(entry)
                normalized.append({**item, "content": fixed})
                continue

            normalized.append(item)

        return normalized

    def _collect_stream_text_sync(self, events: Any) -> tuple[str, Any]:
        text_parts: list[str] = []
        final_response: Any = None
        try:
            for event in events:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        text_parts.append(delta)
                elif event_type == "response.completed":
                    final_response = getattr(event, "response", None)
        finally:
            close = getattr(events, "close", None)
            if callable(close):
                close()

        collected = "".join(text_parts)
        if collected:
            return collected, final_response

        if final_response is not None:
            final_text = getattr(final_response, "output_text", None)
            if isinstance(final_text, str) and final_text:
                return final_text, final_response

        return collected, final_response

    async def _collect_stream_text_async(self, events: Any) -> tuple[str, Any]:
        text_parts: list[str] = []
        final_response: Any = None
        try:
            async for event in events:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        text_parts.append(delta)
                elif event_type == "response.completed":
                    final_response = getattr(event, "response", None)
        finally:
            aclose = getattr(events, "aclose", None)
            if callable(aclose):
                await aclose()

        collected = "".join(text_parts)
        if collected:
            return collected, final_response

        if final_response is not None:
            final_text = getattr(final_response, "output_text", None)
            if isinstance(final_text, str) and final_text:
                return final_text, final_response

        return collected, final_response

    @staticmethod
    def _is_not_found_error(exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code == 404:
            return True
        response = getattr(exc, "response", None)
        if response is not None and getattr(response, "status_code", None) == 404:
            return True
        return "404" in str(exc) and "not found" in str(exc).lower()

    @llm_retry_decorator
    def _chat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        self._ensure_access_token()
        client = self._get_client()
        payload = self._build_responses_payload(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": self._resolve_codex_instructions(messages),
            "tools": [],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
            "stream": True,
        }
        for key in ("reasoning", "include", "service_tier", "text"):
            if key in kwargs and kwargs[key] is not None:
                request_kwargs[key] = kwargs[key]

        try:
            events = client.responses.create(input=payload, **request_kwargs)
            text, response = self._collect_stream_text_sync(events)
        except Exception as exc:
            if self._responses_api_base == DEFAULT_CODEX_API_BASE and self._is_not_found_error(exc):
                self._responses_api_base = DEFAULT_BACKEND_API_BASE
                self.api_base = self._responses_api_base
                self._client = None
                self._aclient = None
                client = self._get_client()
                events = client.responses.create(input=payload, **request_kwargs)
                text, response = self._collect_stream_text_sync(events)
            else:
                raise

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=text),
            raw=response,
            additional_kwargs={},
        )

    @llm_retry_decorator
    async def _achat(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        self._ensure_access_token()
        aclient = self._get_aclient()
        payload = self._build_responses_payload(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": self._resolve_codex_instructions(messages),
            "tools": [],
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
            "stream": True,
        }
        for key in ("reasoning", "include", "service_tier", "text"):
            if key in kwargs and kwargs[key] is not None:
                request_kwargs[key] = kwargs[key]

        try:
            events = await aclient.responses.create(input=payload, **request_kwargs)
            text, response = await self._collect_stream_text_async(events)
        except Exception as exc:
            if self._responses_api_base == DEFAULT_CODEX_API_BASE and self._is_not_found_error(exc):
                self._responses_api_base = DEFAULT_BACKEND_API_BASE
                self.api_base = self._responses_api_base
                self._client = None
                self._aclient = None
                aclient = self._get_aclient()
                events = await aclient.responses.create(input=payload, **request_kwargs)
                text, response = await self._collect_stream_text_async(events)
            else:
                raise

        return ChatResponse(
            message=ChatMessage(role=MessageRole.ASSISTANT, content=text),
            raw=response,
            additional_kwargs={},
        )
