from __future__ import annotations

import asyncio
import http.client
import json
import os
import secrets
from collections.abc import AsyncIterator
from typing import Any, List, Protocol, cast
from urllib.parse import urlsplit

import httpx

from ai_tools_api.config import Settings
from ai_tools_api.errors import ApiError
from ai_tools_api.wav import valid_wav


class TranscriptionService(Protocol):
    async def transcribe(self, audio: bytes, language: str, timeout: float) -> str: ...


class SynthesisService(Protocol):
    async def synthesize(self, text: str, timeout: float) -> bytes: ...


class GenerationService(Protocol):
    async def complete(
        self, payload: dict[str, Any], timeout: float
    ) -> dict[str, Any]: ...

    def stream(
        self, payload: dict[str, Any], timeout: float
    ) -> AsyncIterator[bytes]: ...


class LlamaService:
    def __init__(
        self,
        url: str,
        max_output_bytes: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.url = url
        self.max_output_bytes = max_output_bytes
        self.transport = transport

    async def complete(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(transport=self.transport) as client:
                    async with client.stream(
                        "POST", self.url, json=payload
                    ) as response:
                        if response.status_code != 200 or not response.headers.get(
                            "content-type", ""
                        ).lower().startswith("application/json"):
                            raise ApiError("backend_failure", 502)
                        raw = await self._read_bounded(response)
            return self._completion(raw)
        except TimeoutError as error:
            raise ApiError("timeout", 504) from error
        except ApiError:
            raise
        except httpx.HTTPError as error:
            raise ApiError("backend_unavailable", 503) from error

    async def stream(
        self, payload: dict[str, Any], timeout: float
    ) -> AsyncIterator[bytes]:
        total = 0
        buffer = bytearray()
        done = False
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient(transport=self.transport) as client:
                    async with client.stream(
                        "POST", self.url, json=payload
                    ) as response:
                        if response.status_code != 200 or not response.headers.get(
                            "content-type", ""
                        ).lower().startswith("text/event-stream"):
                            raise ApiError("backend_failure", 502)
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > self.max_output_bytes:
                                raise ApiError("backend_failure", 502)
                            buffer.extend(chunk)
                            buffer[:] = buffer.replace(b"\r\n", b"\n")
                            while b"\n\n" in buffer:
                                event, _, remainder = buffer.partition(b"\n\n")
                                buffer = bytearray(remainder)
                                normalized, event_done = self._stream_event(
                                    bytes(event)
                                )
                                done = done or event_done
                                yield normalized
                        if buffer or not done:
                            raise ApiError("backend_failure", 502)
        except TimeoutError as error:
            raise ApiError("timeout", 504) from error
        except ApiError:
            raise
        except httpx.HTTPError as error:
            raise ApiError("backend_unavailable", 503) from error

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        content = bytearray()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > self.max_output_bytes:
                raise ApiError("backend_failure", 502)
        return bytes(content)

    @staticmethod
    def _completion(raw: bytes) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError("backend_failure", 502) from error
        if not LlamaService._valid_response(value, "chat.completion"):
            raise ApiError("backend_failure", 502)
        return cast(dict[str, Any], value)

    @staticmethod
    def _stream_event(event: bytes) -> tuple[bytes, bool]:
        lines = event.splitlines()
        if len(lines) != 1 or not lines[0].startswith(b"data: "):
            raise ApiError("backend_failure", 502)
        data = lines[0][6:]
        if data == b"[DONE]":
            return b"data: [DONE]\n\n", True
        try:
            value = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApiError("backend_failure", 502) from error
        if not LlamaService._valid_response(value, "chat.completion.chunk"):
            raise ApiError("backend_failure", 502)
        normalized = json.dumps(value, separators=(",", ":")).encode()
        return b"data: " + normalized + b"\n\n", False

    @staticmethod
    def _valid_response(value: object, kind: str) -> bool:
        return (
            isinstance(value, dict)
            and value.get("object") == kind
            and isinstance(value.get("id"), str)
            and isinstance(value.get("model"), str)
            and isinstance(value.get("choices"), list)
        )


class WhisperService:
    def __init__(self, url: str, max_output_bytes: int) -> None:
        self.url = url
        self.max_output_bytes = max_output_bytes

    async def transcribe(self, audio: bytes, language: str, timeout: float) -> str:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._transcribe_sync, audio, language, timeout),
                timeout,
            )
        except TimeoutError as error:
            raise ApiError("timeout", 504) from error
        except ApiError:
            raise
        except (OSError, http.client.HTTPException) as error:
            raise ApiError("backend_unavailable", 503) from error

    def _transcribe_sync(self, audio: bytes, language: str, timeout: float) -> str:
        parsed = urlsplit(self.url)
        boundary = "ai-tools-" + secrets.token_hex(12)
        prefix = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            'filename="audio"\r\nContent-Type: application/octet-stream\r\n\r\n'
        ).encode()
        fields = (
            f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="language"'
            f"\r\n\r\n{language}\r\n--{boundary}--\r\n"
        ).encode()
        body = prefix + audio + fields
        hostname = parsed.hostname
        if hostname is None:
            raise ApiError("backend_unavailable", 503)
        connection = http.client.HTTPConnection(hostname, parsed.port, timeout=timeout)
        try:
            connection.request(
                "POST",
                parsed.path,
                body,
                {"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            response = connection.getresponse()
            payload = response.read(self.max_output_bytes + 1)
        finally:
            connection.close()
        if response.status != 200 or len(payload) > self.max_output_bytes:
            raise ApiError("backend_failure", 502)
        try:
            decoded = json.loads(payload)
            text = decoded["text"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ApiError("backend_failure", 502) from error
        if not isinstance(text, str):
            raise ApiError("backend_failure", 502)
        return text


class PiperService:
    def __init__(
        self,
        executable: str,
        model: str,
        config: str,
        max_output_bytes: int,
    ) -> None:
        self.command: List[str] = [executable, "--model", model]
        if config:
            self.command += ["--config", config]
        self.command += ["--output_file", "-"]
        self.max_output_bytes = max_output_bytes

    async def synthesize(self, text: str, timeout: float) -> bytes:
        try:
            process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as error:
            raise ApiError("backend_unavailable", 503) from error
        try:
            stdout = await asyncio.wait_for(
                self._communicate(process, text.encode("utf-8") + b"\n"), timeout
            )
        except TimeoutError as error:
            await self._stop(process)
            raise ApiError("timeout", 504) from error
        except asyncio.CancelledError:
            await self._stop(process)
            raise
        except ApiError:
            await self._stop(process)
            raise
        if process.returncode != 0 or not valid_wav(stdout):
            raise ApiError("backend_failure", 502)
        return stdout

    async def _communicate(
        self, process: asyncio.subprocess.Process, input_bytes: bytes
    ) -> bytes:
        if process.stdin is None or process.stdout is None or process.stderr is None:
            raise ApiError("backend_failure", 502)
        process.stdin.write(input_bytes)
        try:
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        process.stdin.close()
        stdout_task = asyncio.create_task(self._read_bounded(process.stdout))
        stderr_task = asyncio.create_task(self._read_bounded(process.stderr))
        try:
            stdout, _stderr, _status = await asyncio.gather(
                stdout_task, stderr_task, process.wait()
            )
            return stdout
        finally:
            stdout_task.cancel()
            stderr_task.cancel()

    async def _read_bounded(self, stream: asyncio.StreamReader) -> bytes:
        content = bytearray()
        while chunk := await stream.read(64 * 1024):
            content.extend(chunk)
            if len(content) > self.max_output_bytes:
                raise ApiError("backend_failure", 502)
        return bytes(content)

    @staticmethod
    async def _stop(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 0.75)
        except TimeoutError:
            process.kill()
            await process.wait()


def trusted_whisper_service(settings: Settings) -> WhisperService:
    return WhisperService(str(settings.whisper_url), settings.max_backend_output_bytes)


def trusted_llama_service(settings: Settings) -> LlamaService:
    return LlamaService(str(settings.llama_url), settings.llm_max_output_bytes)


def trusted_piper_service(settings: Settings) -> PiperService:
    for value in (settings.piper_executable, settings.piper_model):
        if not os.path.isabs(value) or not os.path.isfile(value):
            raise ValueError("owned Piper runtime is unavailable")
    if settings.piper_config and (
        not os.path.isabs(settings.piper_config)
        or not os.path.isfile(settings.piper_config)
    ):
        raise ValueError("owned Piper configuration is unavailable")
    return PiperService(
        settings.piper_executable,
        settings.piper_model,
        settings.piper_config,
        settings.max_backend_output_bytes,
    )
