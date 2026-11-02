"""Upload, retrieve, and delete a harmless Pinata validation probe."""

import asyncio

import httpx

from app.services.pinata import PinataClient


async def main() -> None:
    pinata = PinataClient()
    uploaded = await pinata.upload_public(
        b'{"probe":"prisme-step-6"}',
        filename="prisme-step6-probe.json",
        media_type="application/json",
        keyvalues={"kind": "validation-probe"},
    )
    print("UPLOAD_OK", uploaded.cid)
    try:
        gateway_url = pinata.gateway_url(uploaded.cid)
        if gateway_url is None:
            raise RuntimeError("PRISME_PINATA_GATEWAY is missing")
        status_code = 0
        async with httpx.AsyncClient(timeout=20) as client:
            for _ in range(5):
                response = await client.get(gateway_url)
                status_code = response.status_code
                if status_code == 200:
                    break
                await asyncio.sleep(2)
        print("GATEWAY_STATUS", status_code)
        if status_code != 200:
            raise RuntimeError("The uploaded CID was not served by the gateway")
    finally:
        await pinata.delete_public(uploaded.file_id)
        print("DELETE_OK")


if __name__ == "__main__":
    asyncio.run(main())
