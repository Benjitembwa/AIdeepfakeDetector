from types import SimpleNamespace

import pytest

from app.services.blockchain import (
    BlockchainRegistry,
    RegistryConfigurationError,
    TransactionOutcome,
)

CONTRACT = "0x12DD566159a151Ab14009BC5d7624519C60c3647"
PUBLISHER = "0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81"


async def test_registry_encodes_registration_for_the_connected_wallet() -> None:
    captured_name = ""
    captured_args: list[object] = []

    class Contract:
        def encode_abi(self, name: str, *, args: list[object]) -> str:
            nonlocal captured_name, captured_args
            captured_name = name
            captured_args = args
            return "0x1234"

    registry = object.__new__(BlockchainRegistry)
    registry.contract = Contract()
    registry.contract_address = CONTRACT
    registry.settings = SimpleNamespace(base_chain_id=84532)

    transaction = registry.registration_transaction(
        image_sha256="ab" * 32,
        perceptual_hash="ffffffffffffffff",
        difference_hash="0123456789abcdef",
        wavelet_hash="0000000000000001",
        image_cid="bafy-image",
        metadata_cid="bafy-json",
        metadata_sha256="cd" * 32,
        media_id=b"m" * 32,
        publisher_address=PUBLISHER,
    )

    assert captured_name == "registerImage"
    assert captured_args[0] == bytes.fromhex("ab" * 32)
    assert captured_args[1] == 2**64 - 1
    assert captured_args[2] == int("0123456789abcdef", 16)
    assert captured_args[3] == 1
    assert captured_args[4:6] == ["bafy-image", "bafy-json"]
    assert captured_args[6] == bytes.fromhex("cd" * 32)
    assert captured_args[7] == b"m" * 32
    assert transaction.chain_id_hex == "0x14a34"
    assert transaction.from_address == PUBLISHER
    assert transaction.data == "0x1234"


async def test_successful_receipt_is_normalized() -> None:
    class Eth:
        async def get_transaction_receipt(self, _: str) -> dict[str, int]:
            return {"status": 1, "blockNumber": 52962707}

    class W3:
        eth = Eth()

    registry = object.__new__(BlockchainRegistry)
    registry.w3 = W3()
    outcome = await registry.transaction_receipt(f"0x{'2' * 64}")
    assert outcome.state == "confirmed"
    assert outcome.block_number == 52962707


async def test_receipt_rejects_a_transaction_from_another_wallet() -> None:
    class Eth:
        async def get_transaction(self, _: str) -> dict[str, str]:
            return {
                "to": CONTRACT,
                "from": "0x1111111111111111111111111111111111111111",
                "input": "0x1234",
            }

    class W3:
        eth = Eth()

    registry = object.__new__(BlockchainRegistry)
    registry.w3 = W3()
    registry.contract_address = CONTRACT

    async def confirmed(_: str) -> TransactionOutcome:
        return TransactionOutcome(
            state="confirmed", tx_hash=f"0x{'3' * 64}", block_number=1
        )

    registry.transaction_receipt = confirmed
    with pytest.raises(RegistryConfigurationError, match="portefeuille attendu"):
        await registry.verified_transaction_receipt(
            f"0x{'3' * 64}",
            expected_sender=PUBLISHER,
            expected_data="0x1234",
        )
