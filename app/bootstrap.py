from __future__ import annotations

from dataclasses import dataclass

from app.artifact_identity import BankArtifactIdentityError, identify_bank_artifact_mode
from app.bank import BankRepository
from app.customer_service import CustomerResolutionService
from app.demo_data import DEMO_PERSONAS, DemoPersona, ensure_synthetic_demo_bank
from app.deterministic_provider import DeterministicDemoInterpretationProvider
from app.interpretation import InterpretationService, StructuredInterpretationProvider
from app.provider_adapters import CandidateProviderAdapter
from app.runtime import OperationalStore
from app.settings import Settings, settings as default_settings


@dataclass(frozen=True, slots=True)
class AppContext:
    bank: BankRepository
    store: OperationalStore
    customer_service: CustomerResolutionService
    personas: dict[str, DemoPersona]
    data_mode: str
    llm_connected: bool = False


def _build_interpretation_provider(
    settings: Settings,
) -> tuple[StructuredInterpretationProvider, bool]:
    if settings.interpretation_provider == "deterministic":
        return DeterministicDemoInterpretationProvider(), False

    if settings.interpretation_provider == "openai-gpt-6-luna":
        provider = CandidateProviderAdapter.from_environment(
            settings.interpretation_provider,
        )
        if not provider.is_configured():
            raise ValueError(
                "INTERPRETATION_PROVIDER=openai-gpt-6-luna requires "
                "OPENAI_API_KEY to be set"
            )
        return provider, True

    raise ValueError(
        f"Unsupported INTERPRETATION_PROVIDER: {settings.interpretation_provider!r}"
    )


def build_app_context(settings: Settings = default_settings) -> AppContext:
    """Build one runtime context without granting the model data authority."""

    if settings.data_mode == "synthetic":
        ensure_synthetic_demo_bank(settings.bank_db_path)

    artifact_mode = identify_bank_artifact_mode(settings.bank_db_path)
    if artifact_mode != settings.data_mode:
        raise BankArtifactIdentityError(
            "Configured DATA_MODE does not match the banking artifact identity: "
            f"configured={settings.data_mode!r}, artifact={artifact_mode!r}."
        )

    bank = BankRepository(settings.bank_db_path)
    store = OperationalStore(settings.runtime_db_path, session_creation_limit=100)
    store.initialize(data_mode=artifact_mode)
    store.cleanup_expired_state()

    provider, llm_connected = _build_interpretation_provider(settings)
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
        synthetic_data=artifact_mode == "synthetic",
    )
    return AppContext(
        bank=bank,
        store=store,
        customer_service=service,
        personas=dict(DEMO_PERSONAS),
        data_mode=artifact_mode,
        llm_connected=llm_connected,
    )
