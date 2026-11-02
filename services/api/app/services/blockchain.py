import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TimeExhausted, TransactionNotFound

from app.core.config import get_settings

ABI_PATH = Path(__file__).with_name("PrismeImageRegistry.abi.json")
REGISTRY_ABI = json.loads(ABI_PATH.read_text(encoding="utf-8"))
_transaction_lock = asyncio.Lock()


class RegistryUnavailable(RuntimeError):
    """Base Sepolia or the registry could not complete an operation."""


class RegistryConfigurationError(RegistryUnavailable):
    """The registry configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class RegistryRecord:
    media_id: bytes
    metadata_sha256: bytes
    perceptual_hash: int
    difference_hash: int
    wavelet_hash: int
    registered_at: datetime
    registered_block: int
    publisher: str
    revoked: bool
    image_cid: str
    metadata_cid: str


@dataclass(frozen=True)
class TransactionOutcome:
    state: str
    tx_hash: str
    block_number: int | None = None


class BlockchainRegistry:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.w3 = AsyncWeb3(AsyncHTTPProvider(self.settings.base_rpc_url))
        self.contract_address = Web3.to_checksum_address(
            self.settings.registry_contract_address
        )
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=REGISTRY_ABI,
        )

    def _private_key(self) -> str:
        if self.settings.registry_private_key is None:
            raise RegistryConfigurationError(
                "La clé privée Base Sepolia n'est pas configurée."
            )
        return self.settings.registry_private_key.get_secret_value()

    @property
    def publisher_address(self) -> str:
        return self.w3.eth.account.from_key(self._private_key()).address

    async def validate_configuration(self) -> None:
        try:
            chain_id = await self.w3.eth.chain_id
            code = await self.w3.eth.get_code(self.contract_address)
            owner = await self.contract.functions.owner().call()
            authorized = await self.contract.functions.authorizedPublishers(
                self.publisher_address
            ).call()
        except Exception as exc:
            raise RegistryUnavailable("Base Sepolia est temporairement indisponible.") from exc
        if chain_id != self.settings.base_chain_id:
            raise RegistryConfigurationError("Le RPC ne correspond pas à Base Sepolia.")
        if not code:
            raise RegistryConfigurationError("Le contrat configuré ne contient aucun bytecode.")
        if Web3.to_checksum_address(owner) != Web3.to_checksum_address(
            self.publisher_address
        ):
            raise RegistryConfigurationError(
                "La clé configurée ne correspond pas au propriétaire du contrat."
            )
        if not authorized:
            raise RegistryConfigurationError(
                "L'adresse de publication n'est pas autorisée par le contrat."
            )

    async def exists(self, image_sha256: str) -> bool:
        try:
            return bool(
                await self.contract.functions.exists(bytes.fromhex(image_sha256)).call()
            )
        except Exception as exc:
            raise RegistryUnavailable("Le registre Base Sepolia est indisponible.") from exc

    async def get_image(self, image_sha256: str) -> RegistryRecord | None:
        if not await self.exists(image_sha256):
            return None
        try:
            item = await self.contract.functions.getImage(
                bytes.fromhex(image_sha256)
            ).call()
        except Exception as exc:
            raise RegistryUnavailable("La preuve blockchain est indisponible.") from exc
        return RegistryRecord(
            media_id=bytes(item[0]),
            metadata_sha256=bytes(item[1]),
            perceptual_hash=int(item[2]),
            difference_hash=int(item[3]),
            wavelet_hash=int(item[4]),
            registered_at=datetime.fromtimestamp(int(item[5]), tz=UTC),
            registered_block=int(item[6]),
            publisher=Web3.to_checksum_address(item[7]),
            revoked=bool(item[8]),
            image_cid=str(item[9]),
            metadata_cid=str(item[10]),
        )

    async def _send(self, function: object) -> TransactionOutcome:
        async with _transaction_lock:
            try:
                address = self.publisher_address
                nonce = await self.w3.eth.get_transaction_count(address, "pending")
                transaction = await function.build_transaction(
                    {
                        "from": address,
                        "nonce": nonce,
                        "chainId": self.settings.base_chain_id,
                    }
                )
                signed = self.w3.eth.account.sign_transaction(
                    transaction, private_key=self._private_key()
                )
                tx_hash_bytes = await self.w3.eth.send_raw_transaction(
                    signed.raw_transaction
                )
                tx_hash = tx_hash_bytes.hex()
            except Exception as exc:
                raise RegistryUnavailable("La transaction blockchain a été refusée.") from exc
        try:
            receipt = await self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=self.settings.blockchain_receipt_timeout_seconds,
            )
        except TimeExhausted:
            return TransactionOutcome(state="pending", tx_hash=tx_hash)
        if int(receipt["status"]) != 1:
            return TransactionOutcome(state="failed", tx_hash=tx_hash)
        return TransactionOutcome(
            state="confirmed",
            tx_hash=tx_hash,
            block_number=int(receipt["blockNumber"]),
        )

    async def register_image(
        self,
        *,
        image_sha256: str,
        perceptual_hash: str,
        difference_hash: str,
        wavelet_hash: str,
        image_cid: str,
        metadata_cid: str,
        metadata_sha256: str,
        media_id: bytes,
    ) -> TransactionOutcome:
        function = self.contract.functions.registerImage(
            bytes.fromhex(image_sha256),
            int(perceptual_hash, 16),
            int(difference_hash, 16),
            int(wavelet_hash, 16),
            image_cid,
            metadata_cid,
            bytes.fromhex(metadata_sha256),
            media_id,
        )
        return await self._send(function)

    async def revoke_image(self, image_sha256: str) -> TransactionOutcome:
        return await self._send(
            self.contract.functions.revokeImage(bytes.fromhex(image_sha256))
        )

    async def transaction_receipt(self, tx_hash: str) -> TransactionOutcome:
        try:
            receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            return TransactionOutcome(state="pending", tx_hash=tx_hash)
        except Exception as exc:
            raise RegistryUnavailable("Le reçu blockchain est indisponible.") from exc
        return TransactionOutcome(
            state="confirmed" if int(receipt["status"]) == 1 else "failed",
            tx_hash=tx_hash,
            block_number=int(receipt["blockNumber"]),
        )


def get_registry() -> BlockchainRegistry:
    return BlockchainRegistry()
