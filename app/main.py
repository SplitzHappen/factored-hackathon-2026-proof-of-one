from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, status

from app.bootstrap import AppContext, build_app_context
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
                detail="Unknown demo session",
            )
        if session.role is not SessionRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer role required",
            )
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
    ) -> DemoSessionResponse:
        if runtime().data_mode != "synthetic":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Public demo sessions are available only in synthetic mode",
            )
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
        return runtime().customer_service.create_support_handoff(session=session)

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
        return runtime().customer_service.resolve_turn(
            session=session,
            message=request.message,
            reference_date=reference_date,
        )

    return app


app = create_app()
