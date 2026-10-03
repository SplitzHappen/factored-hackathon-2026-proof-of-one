from __future__ import annotations

import hashlib
import sqlite3

import duckdb
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from app.artifact_identity import identify_bank_artifact_mode
from app.bank import IncompatibleBankDatabaseError
from app.bootstrap import AppContext, build_app_context
from app.demo_ui import render_demo_ui
from app.http_safety import RequestBodyLimitMiddleware
from app.runtime import RateLimitExceededError, TicketLimitExceededError
from app.schemas import (
    AuthenticatedSession,
    CustomerTurnRequest,
    CustomerTurnResponse,
    DependencyUnavailableResponse,
    ExecutionStatus,
    DemoPersonaSummary,
    DemoSessionCreateRequest,
    DemoSessionResponse,
    EscalationRecord,
    HealthResponse,
    ReadyResponse,
    SessionRole,
    SupportedLanguage,
)


def create_app(context: AppContext | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Production initialization happens before the app accepts requests. Tests
        # may inject an already-built context without changing this lifecycle.
        if context is None:
            app.state.context = build_app_context()
        else:
            app.state.context = context
        yield

    app = FastAPI(
        title="Proof of One",
        description=(
            "Bounded account and payment support prototype for the "
            "Factored AI & Data Hackathon 2026."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=64 * 1024,
    )

    @app.exception_handler(sqlite3.Error)
    async def sqlite_runtime_error_handler(
        request: Request,
        exc: sqlite3.Error,
    ) -> JSONResponse:
        del request, exc
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Operational state is temporarily unavailable"},
        )

    def bank_unavailable_response() -> JSONResponse:
        payload = DependencyUnavailableResponse(
            detail=(
                "Verified banking data is temporarily unavailable. "
                "No account information was returned."
            ),
            dependency="bank",
            execution_status=ExecutionStatus.DEPENDENCY_UNAVAILABLE,
            action_completed=False,
            banking_fact_released=False,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(mode="json"),
        )

    @app.exception_handler(duckdb.Error)
    async def duckdb_bank_error_handler(
        request: Request,
        exc: duckdb.Error,
    ) -> JSONResponse:
        del request, exc
        return bank_unavailable_response()

    @app.exception_handler(IncompatibleBankDatabaseError)
    async def incompatible_bank_error_handler(
        request: Request,
        exc: IncompatibleBankDatabaseError,
    ) -> JSONResponse:
        del request, exc
        return bank_unavailable_response()

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        detail = [
            {
                "type": error.get("type", "validation_error"),
                "loc": list(error.get("loc", ())),
                "msg": error.get("msg", "Invalid request"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": detail},
        )

    if context is not None:
        # Preserve deterministic injected-context unit tests even when they do not
        # enter TestClient's lifespan context manager.
        app.state.context = context

    def runtime() -> AppContext:
        runtime_context = getattr(app.state, "context", None)
        if runtime_context is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Application runtime is not initialized",
            )
        return runtime_context

    def demo_shell_html() -> str:
        runtime_context = runtime()
        html = render_demo_ui()
        if not runtime_context.llm_connected:
            return html

        replacements = (
            (
                "The lamps are computed from the local synthetic API response, "
                "not from static design placeholders.",
                "The lamps are computed from the backend synthetic API response; "
                "OpenAI interprets language while deterministic policy sets routes.",
            ),
            (
                "Local prototype · synthetic",
                "Live LLM · synthetic",
            ),
            (
                "<strong>Interpreter:</strong> awaiting message",
                "<strong>Interpreter:</strong> OpenAI GPT-6 Luna · deterministic "
                "policy authority retained",
            ),
            (
                "No live LLM · Not fraud detection",
                "Live LLM interpretation · Not fraud detection",
            ),
            (
                "Synthetic data · local API · no live LLM · not fraud detection · "
                "not production/pilot-ready",
                "Synthetic data · live LLM interpretation · deterministic policy · "
                "not fraud detection · not production/pilot-ready",
            ),
            (
                "Boundary: synthetic demo data only · local API prototype · no "
                "production or pilot readiness claim · no live-provider readiness "
                "claim · not fraud detection · no final submission/go-live claim.",
                "Boundary: synthetic demo data only · live-provider interpretation "
                "behind deterministic policy · no production or pilot readiness "
                "claim · not fraud detection · no final submission/go-live claim.",
            ),
            (
                "deterministic provider · no live LLM",
                "OpenAI GPT-6 Luna · deterministic policy authority retained",
            ),
            (
                "els.lineBoundary.textContent = 'Deterministic checks override intent · Not fraud detection';",
                "els.lineBoundary.innerHTML = '• LLM interprets language<br>"
                "• Deterministic checks override intent<br>• Not fraud detection';",
            ),
        )
        for old, new in replacements:
            html = html.replace(old, new)
        return html

    def _peer_rate_subject(request: Request) -> str:
        host = request.client.host if request.client is not None else "unknown"
        return hashlib.sha256(
            f"proof-of-one-demo-session-create|{host}".encode("utf-8")
        ).hexdigest()

    def customer_session(
        x_demo_session: str | None = Header(default=None, alias="X-Demo-Session"),
    ) -> AuthenticatedSession:
        if x_demo_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Demo session required",
            )
        try:
            session_id = UUID(x_demo_session)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid demo session",
            ) from exc

        try:
            session = runtime().store.authenticate_session_request(session_id)
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo session request limit reached",
            ) from exc
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown, expired, or revoked demo session",
            )
        if session.role is not SessionRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer role required",
            )
        return session

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        runtime_context = getattr(app.state, "context", None)
        return HealthResponse(
            status="ok",
            service="proof-of-one",
            llm_connected=(
                bool(runtime_context.llm_connected)
                if runtime_context is not None
                else False
            ),
        )

    @app.get("/ready", response_model=ReadyResponse)
    def ready() -> ReadyResponse | JSONResponse:
        runtime_context = getattr(app.state, "context", None)
        if runtime_context is None:
            payload = ReadyResponse(
                status="not_ready",
                service="proof-of-one",
                data_mode=None,
                synthetic_data=None,
                bank_ready=False,
                runtime_ready=False,
                llm_connected=False,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=payload.model_dump(mode="json"),
            )

        bank_ready = False
        runtime_ready = False
        try:
            artifact_mode = identify_bank_artifact_mode(
                runtime_context.bank.database_path
            )
            if artifact_mode != runtime_context.data_mode:
                raise RuntimeError("bank artifact mode changed after startup")
            runtime_context.bank.check_ready()
            bank_ready = True
        except Exception:
            bank_ready = False

        try:
            runtime_context.store.check_ready(
                expected_data_mode=runtime_context.data_mode
            )
            runtime_ready = True
        except Exception:
            runtime_ready = False

        payload = ReadyResponse(
            status="ready" if bank_ready and runtime_ready else "not_ready",
            service="proof-of-one",
            data_mode=runtime_context.data_mode,
            synthetic_data=runtime_context.data_mode == "synthetic",
            bank_ready=bank_ready,
            runtime_ready=runtime_ready,
            llm_connected=runtime_context.llm_connected,
        )
        if not (bank_ready and runtime_ready):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=payload.model_dump(mode="json"),
            )
        return payload

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def demo_shell_root() -> HTMLResponse:
        return HTMLResponse(demo_shell_html())

    @app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
    def demo_shell() -> HTMLResponse:
        return HTMLResponse(demo_shell_html())

    @app.get(
        "/api/demo/personas",
        response_model=list[DemoPersonaSummary],
    )
    def list_demo_personas() -> list[DemoPersonaSummary]:
        if runtime().data_mode != "synthetic":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Public demo personas are available only in synthetic mode",
            )
        return [
            DemoPersonaSummary(
                persona_id=persona.persona_id,
                display_name=persona.display_name,
                default_language=persona.default_language,
                synthetic_data=True,
            )
            for persona in runtime().personas.values()
        ]

    @app.post(
        "/api/demo/sessions",
        response_model=DemoSessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_demo_session(
        request: DemoSessionCreateRequest,
        http_request: Request,
    ) -> DemoSessionResponse:
        if runtime().data_mode != "synthetic":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Public demo sessions are available only in synthetic mode",
            )
        runtime().store.cleanup_expired_state()
        persona = runtime().personas.get(request.persona_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown demo persona",
            )
        try:
            runtime().store.enforce_session_creation_rate(
                _peer_rate_subject(http_request)
            )
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo session creation limit reached",
            ) from exc

        language = (
            SupportedLanguage(request.language)
            if request.language is not None
            else persona.default_language
        )
        session = AuthenticatedSession(
            session_id=uuid4(),
            tenant_id=f"demo-{uuid4().hex}",
            role=SessionRole.CUSTOMER,
            demo_persona_id=persona.persona_id,
            customer_id=persona.customer_id,
            language=language,
        )
        runtime().store.save_authenticated_session(session)
        return DemoSessionResponse(
            session_id=session.session_id,
            tenant_id=session.tenant_id,
            role=session.role,
            persona_id=persona.persona_id,
            display_name=persona.display_name,
            language=session.language,
            synthetic_data=True,
        )

    @app.post(
        "/api/customer/handoff",
        response_model=EscalationRecord,
        status_code=status.HTTP_201_CREATED,
    )
    def create_customer_handoff(
        x_demo_session: str | None = Header(default=None, alias="X-Demo-Session"),
    ) -> EscalationRecord:
        session = customer_session(x_demo_session)
        try:
            return runtime().customer_service.create_support_handoff(session=session)
        except TicketLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo support ticket limit reached",
            ) from exc

    @app.delete(
        "/api/demo/session",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def revoke_demo_session(
        x_demo_session: str | None = Header(default=None, alias="X-Demo-Session"),
    ) -> Response:
        if x_demo_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Demo session required",
            )
        try:
            session_id = UUID(x_demo_session)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid demo session",
            ) from exc
        session = runtime().store.get_authenticated_session(session_id)
        if session is None or session.role is not SessionRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unknown, expired, or revoked demo session",
            )
        runtime().store.revoke_session(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/api/customer/turn",
        response_model=CustomerTurnResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": DependencyUnavailableResponse,
                "description": (
                    "Trusted banking data is unavailable; no banking fact is released."
                ),
            }
        },
    )
    def customer_turn(
        request: CustomerTurnRequest,
        x_demo_session: str | None = Header(default=None, alias="X-Demo-Session"),
    ) -> CustomerTurnResponse:
        session = customer_session(x_demo_session)
        persona = runtime().personas.get(session.demo_persona_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session persona is not permitted",
            )
        reference_date = datetime.now(
            ZoneInfo(persona.timezone_name)
        ).date()
        try:
            return runtime().customer_service.resolve_turn(
                session=session,
                message=request.message,
                reference_date=reference_date,
            )
        except TicketLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo support ticket limit reached",
            ) from exc

    return app


app = create_app()
