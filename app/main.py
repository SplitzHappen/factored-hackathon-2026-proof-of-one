from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException, status

from app.bootstrap import AppContext, build_app_context
from app.demo_data import DEMO_TENANT_ID
from app.schemas import (
    AuthenticatedSession,
    CustomerTurnRequest,
    CustomerTurnResponse,
    DemoPersonaSummary,
    DemoSessionCreateRequest,
    DemoSessionResponse,
    HealthResponse,
    SessionRole,
)


def create_app(context: AppContext | None = None) -> FastAPI:
    app = FastAPI(
        title="Proof of One",
        description=(
            "Bounded account and payment support prototype for the "
            "Factored AI & Data Hackathon 2026."
        ),
        version="0.2.0",
    )
    cached_context = context

    def runtime() -> AppContext:
        nonlocal cached_context
        if cached_context is None:
            cached_context = build_app_context()
        return cached_context

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
        if session.tenant_id != DEMO_TENANT_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session tenant is not permitted",
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

        language = request.language or persona.default_language
        session = AuthenticatedSession(
            session_id=uuid4(),
            tenant_id=DEMO_TENANT_ID,
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
