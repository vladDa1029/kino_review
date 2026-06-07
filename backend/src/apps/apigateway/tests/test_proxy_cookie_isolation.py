import asyncio
import contextlib

import httpx

from app.setup import get_aclient


def test_proxy_client_does_not_persist_upstream_cookies() -> None:
    """An upstream Set-Cookie must never be captured by the shared client.

    Otherwise one user's ``refresh`` cookie would leak onto every subsequent
    proxied request through the shared httpx client.
    """

    async def _run() -> None:
        agen = get_aclient()
        client = await agen.__anext__()
        try:
            request = httpx.Request("POST", "http://upstream.local/auth/refresh")
            response = httpx.Response(
                200,
                headers=[("set-cookie", "refresh=secret-token; Path=/; HttpOnly")],
                request=request,
            )

            # Simulate httpx storing response cookies into the client jar.
            client.cookies.extract_cookies(response)

            assert len(client.cookies.jar) == 0
            assert "refresh" not in client.cookies
        finally:
            with contextlib.suppress(StopAsyncIteration):
                await agen.__anext__()

    asyncio.run(_run())
