from types import MethodType

from app.services.blockchain import BlockchainRegistry, TransactionOutcome


async def test_registry_converts_hashes_to_contract_abi_types() -> None:
    captured: tuple[object, ...] = ()
    sentinel = object()

    class Functions:
        def registerImage(self, *values: object) -> object:  # noqa: N802 - ABI name
            nonlocal captured
            captured = values
            return sentinel

    class Contract:
        functions = Functions()

    registry = object.__new__(BlockchainRegistry)
    registry.contract = Contract()

    async def fake_send(_: BlockchainRegistry, function: object) -> TransactionOutcome:
        assert function is sentinel
        return TransactionOutcome(state="confirmed", tx_hash=f"0x{'1' * 64}", block_number=1)

    registry._send = MethodType(fake_send, registry)
    outcome = await registry.register_image(
        image_sha256="ab" * 32,
        perceptual_hash="ffffffffffffffff",
        difference_hash="0123456789abcdef",
        wavelet_hash="0000000000000001",
        image_cid="bafy-image",
        metadata_cid="bafy-json",
        metadata_sha256="cd" * 32,
        media_id=b"m" * 32,
    )

    assert outcome.state == "confirmed"
    assert captured[0] == bytes.fromhex("ab" * 32)
    assert captured[1] == 2**64 - 1
    assert captured[2] == int("0123456789abcdef", 16)
    assert captured[3] == 1
    assert captured[4:6] == ("bafy-image", "bafy-json")
    assert captured[6] == bytes.fromhex("cd" * 32)
    assert captured[7] == b"m" * 32


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
