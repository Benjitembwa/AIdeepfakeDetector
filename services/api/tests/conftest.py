import os
import hashlib
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime

import pytest_asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["PRISME_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["PRISME_JWT_SECRET_KEY"] = "test-secret-that-is-longer-than-thirty-two-characters"
os.environ["PRISME_APP_ENV"] = "test"
os.environ["PRISME_SIGHTENGINE_API_USER"] = "test-user"
os.environ["PRISME_SIGHTENGINE_API_SECRET"] = "test-secret"
os.environ["PRISME_PINATA_JWT"] = "test-pinata-jwt"
os.environ["PRISME_PINATA_GATEWAY"] = "test-gateway.mypinata.cloud"
os.environ["PRISME_REGISTRY_CONTRACT_ADDRESS"] = (
    "0x12DD566159a151Ab14009BC5d7624519C60c3647"
)

from app.db import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.blockchain import (  # noqa: E402
    RegistryRecord,
    TransactionOutcome,
    WalletTransaction,
)
from app.services.c2pa_provenance import C2paReport, SignedC2paAsset  # noqa: E402
from app.services.pinata import PinataFile  # noqa: E402
from app.services.sightengine import SightengineResult  # noqa: E402


class FakePinata:
    def __init__(self) -> None:
        self.counter = 0
        self.deleted: list[str] = []

    async def upload_public(self, *_: object, **__: object) -> PinataFile:
        self.counter += 1
        return PinataFile(
            file_id=f"pinata-file-{self.counter}",
            cid=f"bafy-test-cid-{self.counter}",
        )

    async def delete_public(self, file_id: str) -> None:
        self.deleted.append(file_id)


class FakeRegistry:
    contract_address = "0x12DD566159a151Ab14009BC5d7624519C60c3647"

    def __init__(self) -> None:
        self.records: dict[str, RegistryRecord] = {}
        self.transactions: dict[str, TransactionOutcome] = {}
        self.actions: dict[str, tuple[str, dict[str, object]]] = {}
        self.counter = 0

    async def validate_configuration(self, *, require_open: bool = True) -> None:
        assert require_open
        return None

    async def exists(self, image_sha256: str) -> bool:
        return image_sha256 in self.records

    async def get_image(self, image_sha256: str) -> RegistryRecord | None:
        return self.records.get(image_sha256)

    def registration_transaction(self, **values: object) -> WalletTransaction:
        image_sha256 = str(values["image_sha256"])
        data = f"0x{hashlib.sha256(f'register:{image_sha256}'.encode()).hexdigest()}"
        self.actions[data] = ("register", values)
        return WalletTransaction(
            chain_id=84532,
            chain_id_hex="0x14a34",
            contract_address=self.contract_address,
            from_address=str(values["publisher_address"]),
            data=data,
        )

    def revocation_transaction(
        self, image_sha256: str, *, publisher_address: str
    ) -> WalletTransaction:
        data = f"0x{hashlib.sha256(f'revoke:{image_sha256}'.encode()).hexdigest()}"
        self.actions[data] = (
            "revoke",
            {"image_sha256": image_sha256, "publisher_address": publisher_address},
        )
        return WalletTransaction(
            chain_id=84532,
            chain_id_hex="0x14a34",
            contract_address=self.contract_address,
            from_address=publisher_address,
            data=data,
        )

    async def verified_transaction_receipt(
        self,
        tx_hash: str,
        *,
        expected_sender: str,
        expected_data: str,
    ) -> TransactionOutcome:
        outcome = self.transactions.get(tx_hash)
        if outcome is None:
            self.counter += 1
            outcome = TransactionOutcome(
                state="confirmed",
                tx_hash=tx_hash,
                block_number=52962707 + self.counter,
            )
            self.transactions[tx_hash] = outcome
        if outcome.state != "confirmed":
            return outcome
        action, values = self.actions[expected_data]
        assert str(values["publisher_address"]).lower() == expected_sender.lower()
        image_sha256 = str(values["image_sha256"])
        if action == "register":
            self.records[image_sha256] = RegistryRecord(
                media_id=bytes(values["media_id"]),
                metadata_sha256=bytes.fromhex(str(values["metadata_sha256"])),
                perceptual_hash=int(str(values["perceptual_hash"]), 16),
                difference_hash=int(str(values["difference_hash"]), 16),
                wavelet_hash=int(str(values["wavelet_hash"]), 16),
                registered_at=datetime.now(UTC),
                registered_block=outcome.block_number or 0,
                publisher=expected_sender,
                revoked=False,
                image_cid=str(values["image_cid"]),
                metadata_cid=str(values["metadata_cid"]),
            )
        else:
            self.records[image_sha256] = replace(
                self.records[image_sha256], revoked=True
            )
        return outcome

    async def transaction_receipt(self, tx_hash: str) -> TransactionOutcome:
        return self.transactions.get(
            tx_hash, TransactionOutcome(state="pending", tx_hash=tx_hash)
        )


@pytest.fixture(autouse=True)
def sightengine_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_analysis(*_: object, **__: object) -> SightengineResult:
        return SightengineResult(
            ai_generated_score=0.87,
            deepfake_score=0.08,
            likely_generator="midjourney",
            likely_generator_score=0.72,
            request_id="req_test",
            operations=6,
        )

    monkeypatch.setattr("app.routers.verification.analyze_image", fake_analysis)


@pytest.fixture(autouse=True)
def external_services_stub(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    pinata = FakePinata()
    registry = FakeRegistry()
    monkeypatch.setattr("app.routers.images.get_pinata_client", lambda: pinata)
    monkeypatch.setattr("app.routers.images.get_registry", lambda _address=None: registry)
    monkeypatch.setattr(
        "app.routers.verification.get_registry", lambda _address=None: registry
    )

    def fake_sign_c2pa(contents: bytes, **_: object) -> SignedC2paAsset:
        return SignedC2paAsset(
            contents=contents,
            sha256=hashlib.sha256(contents).hexdigest(),
            report=C2paReport(
                status="valid_untrusted",
                active_manifest="urn:c2pa:test",
                claim_generator="Prisme",
                issuer="C2PA Test Signing Cert",
                validation_codes=("signingCredential.untrusted",),
                manifest_store_json="{}",
            ),
        )

    monkeypatch.setattr("app.routers.images.sign_c2pa", fake_sign_c2pa)
    monkeypatch.setattr(
        "app.routers.verification.inspect_c2pa",
        lambda *_: C2paReport(status="absent"),
    )
    return {"pinata": pinata, "registry": registry}


@pytest_asyncio.fixture(autouse=True)
async def database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
