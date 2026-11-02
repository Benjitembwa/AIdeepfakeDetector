import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PinataUnavailable(RuntimeError):
    """Pinata could not complete an operation."""


@dataclass(frozen=True)
class PinataFile:
    file_id: str
    cid: str


class PinataClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = get_settings()
        self.transport = transport

    def _jwt(self) -> str:
        if self.settings.pinata_jwt is None:
            raise PinataUnavailable("La clé Pinata n'est pas configurée.")
        return self.settings.pinata_jwt.get_secret_value()

    async def upload_public(
        self,
        contents: bytes,
        *,
        filename: str,
        media_type: str,
        keyvalues: dict[str, str],
    ) -> PinataFile:
        data = {
            "network": "public",
            "cid_version": "v1",
            "name": filename,
            "keyvalues": json.dumps(keyvalues, separators=(",", ":")),
        }
        headers = {"Authorization": f"Bearer {self._jwt()}"}
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.pinata_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    self.settings.pinata_upload_url,
                    headers=headers,
                    data=data,
                    files={"file": (filename, contents, media_type)},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("L'envoi Pinata a échoué (%s)", type(exc).__name__)
            raise PinataUnavailable("Le stockage IPFS est temporairement indisponible.") from exc
        item = payload.get("data") if isinstance(payload, dict) else None
        file_id = item.get("id") if isinstance(item, dict) else None
        cid = item.get("cid") if isinstance(item, dict) else None
        if not isinstance(file_id, str) or not file_id or not isinstance(cid, str) or not cid:
            raise PinataUnavailable("Pinata a renvoyé une réponse incomplète.")
        return PinataFile(file_id=file_id, cid=cid)

    async def delete_public(self, file_id: str) -> None:
        headers = {"Authorization": f"Bearer {self._jwt()}"}
        url = f"{self.settings.pinata_api_url.rstrip('/')}/files/public/{file_id}"
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.pinata_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.delete(url, headers=headers)
                if response.status_code != 404:
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Le désépinglage Pinata a échoué (%s)", type(exc).__name__)
            raise PinataUnavailable("Le fichier IPFS n'a pas pu être désépinglé.") from exc

    def gateway_url(self, cid: str) -> str | None:
        base = self.settings.pinata_gateway_base_url
        return f"{base}/ipfs/{cid}" if base else None


def get_pinata_client() -> PinataClient:
    return PinataClient()
