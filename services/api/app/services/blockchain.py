import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from hexbytes import HexBytes
from web3 import AsyncHTTPProvider, AsyncWeb3, Web3
from web3.exceptions import TransactionNotFound

from app.core.config import get_settings

ABI_PATH = Path(__file__).with_name("PrismeOpenImageRegistry.abi.json")
REGISTRY_ABI = json.loads(ABI_PATH.read_text(encoding="utf-8"))


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


@dataclass(frozen=True)
class WalletTransaction:
    chain_id: int
    chain_id_hex: str
    contract_address: str
    from_address: str
    data: str
    value: str = "0x0"


class BlockchainRegistry:
    def __init__(self, contract_address: str | None = None) -> None:
        self.settings = get_settings()
        self.w3 = AsyncWeb3(AsyncHTTPProvider(self.settings.base_rpc_url))
        self.contract_address = Web3.to_checksum_address(
            contract_address or self.settings.registry_contract_address
        )
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=REGISTRY_ABI,
        )

    async def validate_configuration(self, *, require_open: bool = True) -> None:
        try:
            chain_id = await self.w3.eth.chain_id
            code = await self.w3.eth.get_code(self.contract_address)
        except Exception as exc:
            raise RegistryUnavailable("Base Sepolia est temporairement indisponible.") from exc
        if chain_id != self.settings.base_chain_id:
            raise RegistryConfigurationError("Le RPC ne correspond pas à Base Sepolia.")
        if not code:
            raise RegistryConfigurationError(
                "Le contrat configuré ne contient aucun bytecode."
            )
        if require_open:
            try:
                is_open = bool(await self.contract.functions.registrationOpen().call())
            except Exception as exc:
                raise RegistryConfigurationError(
                    "Le contrat configuré n'est pas le registre public Prisme."
                ) from exc
            if not is_open:
                raise RegistryConfigurationError(
                    "Le contrat configuré n'accepte pas les publications publiques."
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

    def registration_transaction(
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
        publisher_address: str,
    ) -> WalletTransaction:
        sender = Web3.to_checksum_address(publisher_address)
        data = self.contract.encode_abi(
            "registerImage",
            args=[
                bytes.fromhex(image_sha256),
                int(perceptual_hash, 16),
                int(difference_hash, 16),
                int(wavelet_hash, 16),
                image_cid,
                metadata_cid,
                bytes.fromhex(metadata_sha256),
                media_id,
            ],
        )
        return WalletTransaction(
            chain_id=self.settings.base_chain_id,
            chain_id_hex=hex(self.settings.base_chain_id),
            contract_address=self.contract_address,
            from_address=sender,
            data=data,
        )

    def revocation_transaction(
        self, image_sha256: str, *, publisher_address: str
    ) -> WalletTransaction:
        sender = Web3.to_checksum_address(publisher_address)
        data = self.contract.encode_abi(
            "revokeImage", args=[bytes.fromhex(image_sha256)]
        )
        return WalletTransaction(
            chain_id=self.settings.base_chain_id,
            chain_id_hex=hex(self.settings.base_chain_id),
            contract_address=self.contract_address,
            from_address=sender,
            data=data,
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

    async def verified_transaction_receipt(
        self,
        tx_hash: str,
        *,
        expected_sender: str,
        expected_data: str,
    ) -> TransactionOutcome:
        outcome = await self.transaction_receipt(tx_hash)
        if outcome.state == "pending":
            return outcome
        try:
            transaction = await self.w3.eth.get_transaction(tx_hash)
            target = transaction.get("to")
            sender = transaction.get("from")
            input_value = transaction.get("input", "0x")
        except Exception as exc:
            raise RegistryUnavailable("La transaction ne peut pas être vérifiée.") from exc

        actual_data = (
            input_value.hex()
            if isinstance(input_value, (bytes, HexBytes))
            else str(input_value)
        )
        if not actual_data.startswith("0x"):
            actual_data = f"0x{actual_data}"
        if target is None or Web3.to_checksum_address(target) != self.contract_address:
            raise RegistryConfigurationError(
                "La transaction ne cible pas le contrat Prisme configuré."
            )
        if sender is None or Web3.to_checksum_address(sender) != Web3.to_checksum_address(
            expected_sender
        ):
            raise RegistryConfigurationError(
                "La transaction n'a pas été signée par le portefeuille attendu."
            )
        if actual_data.lower() != expected_data.lower():
            raise RegistryConfigurationError(
                "Les données de la transaction divergent des preuves préparées."
            )
        return outcome


def get_registry(contract_address: str | None = None) -> BlockchainRegistry:
    return BlockchainRegistry(contract_address)
