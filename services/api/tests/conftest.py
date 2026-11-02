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
from app.services.blockchain import RegistryRecord, TransactionOutcome  # noqa: E402
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
    publisher_address = "0x9f06FcF98fDB0B374E63FdE559590bF2CA472E81"

    def __init__(self) -> None:
        self.records: dict[str, RegistryRecord] = {}
        self.transactions: dict[str, TransactionOutcome] = {}
        self.counter = 0
        self.next_registration_state = "confirmed"

    async def validate_configuration(self) -> None:
        return None

    async def exists(self, image_sha256: str) -> bool:
        return image_sha256 in self.records

    async def get_image(self, image_sha256: str) -> RegistryRecord | None:
        return self.records.get(image_sha256)

    async def register_image(self, **values: object) -> TransactionOutcome:
        self.counter += 1
        tx_hash = f"0x{self.counter:064x}"
        if self.next_registration_state != "confirmed":
            outcome = TransactionOutcome(
                state=self.next_registration_state, tx_hash=tx_hash
            )
            self.transactions[tx_hash] = outcome
            return outcome
        image_sha256 = str(values["image_sha256"])
        self.records[image_sha256] = RegistryRecord(
            media_id=bytes(values["media_id"]),
            metadata_sha256=bytes.fromhex(str(values["metadata_sha256"])),
            perceptual_hash=int(str(values["perceptual_hash"]), 16),
            difference_hash=int(str(values["difference_hash"]), 16),
            wavelet_hash=int(str(values["wavelet_hash"]), 16),
            registered_at=datetime.now(UTC),
            registered_block=52962707 + self.counter,
            publisher=self.publisher_address,
            revoked=False,
            image_cid=str(values["image_cid"]),
            metadata_cid=str(values["metadata_cid"]),
        )
        outcome = TransactionOutcome(
            state="confirmed", tx_hash=tx_hash, block_number=52962707 + self.counter
        )
        self.transactions[tx_hash] = outcome
        return outcome

    async def revoke_image(self, image_sha256: str) -> TransactionOutcome:
        self.counter += 1
        tx_hash = f"0x{self.counter:064x}"
        self.records[image_sha256] = replace(
            self.records[image_sha256], revoked=True
        )
        outcome = TransactionOutcome(
            state="confirmed", tx_hash=tx_hash, block_number=52962707 + self.counter
        )
        self.transactions[tx_hash] = outcome
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
    monkeypatch.setattr("app.routers.images.get_registry", lambda: registry)
    monkeypatch.setattr("app.routers.verification.get_registry", lambda: registry)

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
