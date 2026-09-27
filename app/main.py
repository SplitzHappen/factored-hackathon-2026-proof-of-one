from __future__ import annotations

import hashlib
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, Request, Response, status

from app.bootstrap import AppContext, build_app_context
from app.runtime import RateLimitExceededError, TicketLimitExceededError
from app.schemas import (
    AuthenticatedSession,
    CustomerTurnRequest,
    CustomerTurnResponse,
    DemoPersonaSummary,
    DemoSessionCreateRequest,
    DemoSessionResponse,
    EscalationRecord,
    HealthResponse,
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

    @staticmethod
    def _peer_rate_subject(request: Request) -> str:
        host = request.client.host if request.client is not None else "unknown"
        return hashlib.sha256(
            f"proof-of-one-demo-session-create|{host}".encode("utf-8")
        ).hexdigest()

    def customer_session(
        x_demo_session: str = Header(alias="X-Demo-Session"),
    ) -> AuthenticatedSession:
        try:
            session_id = UUID(x_demo_session)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid demo session",
            ) from exc

        session = runtime().store.get_authenticated_session(session_id)
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
        try:
            runtime().store.enforce_session_request_rate(session.session_id)
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo session request limit reached",
            ) from exc
        return session

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="proof-of-one",
            llm_connected=False,
        )

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
        try:
            runtime().store.enforce_session_creation_rate(
                _peer_rate_subject(http_request)
            )
        except RateLimitExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demo session creation limit reached",
            ) from exc

        persona = runtime().personas.get(request.persona_id)
        if persona is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unknown demo persona",
            )

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
        x_demo_session: str = Header(alias="X-Demo-Session"),
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
        x_demo_session: str = Header(alias="X-Demo-Session"),
    ) -> Response:
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
    )
    def customer_turn(
        request: CustomerTurnRequest,
        x_demo_session: str = Header(alias="X-Demo-Session"),
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
