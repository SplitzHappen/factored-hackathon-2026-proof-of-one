from __future__ import annotations

from dataclasses import dataclass

from app.bank import BankRepository
from app.customer_service import CustomerResolutionService
from app.demo_data import DEMO_PERSONAS, DemoPersona, build_synthetic_demo_bank
from app.deterministic_provider import DeterministicDemoInterpretationProvider
from app.interpretation import InterpretationService
from app.runtime import OperationalStore
from app.settings import Settings, settings as default_settings


@dataclass(frozen=True, slots=True)
class AppContext:
    bank: BankRepository
    store: OperationalStore
    customer_service: CustomerResolutionService
    personas: dict[str, DemoPersona]
    data_mode: str


def build_app_context(settings: Settings = default_settings) -> AppContext:
    """Build one runtime context without granting the model data authority."""

    if settings.data_mode == "synthetic":
        build_synthetic_demo_bank(settings.bank_db_path)

    bank = BankRepository(settings.bank_db_path)
    store = OperationalStore(settings.runtime_db_path)
    store.initialize()

    provider = DeterministicDemoInterpretationProvider()
    interpreter = InterpretationService(
        bank=bank,
        store=store,
        provider=provider,
        max_attempts=1,
    )
    service = CustomerResolutionService(
        bank=bank,
        store=store,
        interpreter=interpreter,
        synthetic_data=settings.data_mode == "synthetic",
    )
    return AppContext(
        bank=bank,
        store=store,
        customer_service=service,
        personas=dict(DEMO_PERSONAS),
        data_mode=settings.data_mode,
    )
