from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import app.unauthorized_signals as unauthorized_signals
from app.bootstrap import build_app_context
from app.denial_safety import denial_safety_assertion, denial_safety_findings
from app.main import create_app
from app.settings import Settings


# RF1O recognition families. Wording is family-level development material written
# for these tests, not the RF1N fresh-probe text, so RF1N stays clean evidence of
# what was repaired.
_FAMILY_POSITIVES = [
    # 1. set-up / initiation / enrollment denial over an existing item
    ("non_origination", "Me está saliendo un débito automático cada mes. Yo nunca lo programé."),
    ("non_origination", "Hay un beneficiario en mi lista que yo jamás inscribí."),
    ("non_origination", "Tengo un cobro mensual de un club de vinos. Jamás contraté esa membresía."),
    ("non_origination", "Están saliendo pagos semanales hacia un tal Ortega; yo no los programé."),
    ("non_origination", "Me pidieron un código por mensaje para un giro que yo no inicié y luego se fue el dinero."),
    ("non_origination", "Tem um débito mensal de uma academia na minha conta. Eu jamais contratei isso."),
    ("non_origination", "Apareceu um favorecido na minha lista que eu jamais cadastrei."),
    ("non_origination", "Chegou uma cobrança recorrente de um app de música. Nunca contratei esse serviço."),
    ("non_origination", "Chegou um SMS pedindo para confirmar um Pix que jamais iniciei."),
    # 2. observed activity located where the customer has never been
    ("presence_denial", "Hay compras con mi tarjeta en un pueblo donde jamás he ido."),
    ("presence_denial", "Me salieron dos cargos en una gasolinera de Cali, ciudad en la que jamás he estado."),
    ("presence_denial", "Apareceram compras num shopping de Recife, onde eu nunca fui."),
    ("presence_denial", "Vi um saque numa agência de outra cidade onde nunca estive."),
    # 3. nobody in the household recognizes or made the activity
    ("household_denial", "Hay un consumo en un restaurante que nadie de mi familia hizo."),
    ("household_denial", "Me aparece un débito de una aerolínea. Ni yo ni mi esposo lo reconocemos."),
    ("household_denial", "Tem um gasto num posto que ninguém da minha casa reconhece."),
    ("household_denial", "Caiu um boleto pago na conta. Nem eu nem meu marido fizemos."),
    # 4. an unnamed party got into the customer's own account or app
    ("account_intrusion", "Anoche entraron a mi banca en línea y cambiaron la clave."),
    ("account_intrusion", "Sospecho que accedieron a mi cuenta desde otro país."),
    ("account_intrusion", "Unos desconocidos se metieron en mi app del banco."),
    ("account_intrusion", "Acho que mexeram na minha conta ontem à noite."),
    ("account_intrusion", "Alguém acessou meu aplicativo e trocou meu e-mail."),
    ("account_intrusion", "Hoje cedo entraram na minha conta e fizeram um Pix."),
    # 5. account provenance denial (misdirected alert)
    ("ownership_denial", "Me mandaron un SMS por un débito; ese débito no es de mi tarjeta."),
    ("ownership_denial", "Recebi uma notificação de compra. Essa compra não é do meu cartão."),
    # 6. a relative's denial relayed by the customer
    ("third_party_denial", "Escribo por mi abuela: le aparecen retiros y ella no los hizo."),
    ("third_party_denial", "Mi mamá no reconoce un cargo que le salió en su tarjeta."),
    ("third_party_denial", "Minha mãe viu um débito estranho e ela não fez esse pagamento."),
    ("third_party_denial", "Meu avô reclama que sumiu dinheiro da conta dele; ele jamais autorizou isso."),
]

# Near misses for the RF1O families. The layer must license none of them, and the
# full detector must not report them either.
_FAMILY_NEGATIVES = [
    # set-up: not yet, causal, complementizer, indefinite, forgotten, no negation
    "Todavía no programé el pago de la luz, ¿cómo lo hago?",
    "No inscribí al destinatario porque la app me pedía un código.",
    "Le confirmo que no programé ningún pago este mes.",
    "Nunca me suscribí a nada en este banco, ¿qué suscripciones ofrecen?",
    "Me suscribí a un servicio de video en junio; quiero cancelar esa suscripción.",
    "Se me olvidó agregar al beneficiario. No lo agregué.",
    "¿Cómo cancelo una suscripción que ya no uso?",
    "Ainda não cadastrei o favorecido, como faço?",
    "Não assinei o contrato porque estava viajando.",
    "Eu nunca cadastrei favorecido nenhum, como funciona?",
    "Quero cancelar a assinatura de streaming que eu fiz em maio.",
    # presence: planned travel, self-performed, known person, card possession only
    "Viajaré a una región donde jamás he ido; ¿puedo pagar con la tarjeta allá?",
    "Quiero sacar efectivo en un país donde no he estado antes, ¿cobran comisión por retiros?",
    "Hice compras en una ciudad donde nunca había estado y me bloquearon la tarjeta.",
    "Aparecen retiros en un pueblo adonde jamás he ido, pero era mi hija con la tarjeta adicional.",
    "Vou viajar para uma cidade onde nunca estive; posso fazer saques lá?",
    "Tengo la tarjeta conmigo, ¿por qué me rechazaron la compra?",
    "O cartão está comigo, por que a compra foi recusada?",
    # household: no activity, indefinite activity
    "Nadie en mi casa reconoce el nuevo logo del banco.",
    "Nadie en mi familia hizo compras este mes, ¿por qué mi saldo es igual?",
    "Ninguém da minha família fez compras online, quero desativar essa função.",
    # intrusion: negated, named subject, subjunctive, embedded question, hedge,
    # non-bank account, permission
    "Nadie accedió a mi cuenta; solo necesito el saldo.",
    "Mi hija entró a mi cuenta para pagar la luz.",
    "Mis papás entraron a mi cuenta para ver el saldo.",
    "¿Qué recomiendan para que nadie se meta en mi app?",
    "Quiero saber si entraron a mi cuenta desde otro celular.",
    "Entraron a mi cuenta de Netflix y cambiaron el perfil.",
    "Minha esposa acessou minha conta pra pagar um boleto.",
    "Ninguém acessou minha conta, só quero o extrato.",
    "Como sei se alguém entrou na minha conta?",
    "Tal vez entraron a mi cuenta, no sé.",
    "Entraron a mi cuenta los del banco con mi permiso para actualizar datos.",
    # provenance: corrective re-attribution, qualified account, open question
    "Ese débito no es de mi tarjeta de crédito sino de la débito.",
    "El cargo no es de mi tarjeta, es de la tarjeta de mi esposo.",
    "No sé si ese pago es de mi cuenta o de la de mi hermano.",
    # third party: self-performed, not yet, causal, no activity
    "Mi hijo no hizo esa compra, la hice yo.",
    "Mi mamá no envió la plata todavía, ¿cómo le ayudo?",
    "Mi papá no hizo el pago porque no le alcanzó.",
    "Mi esposa no reconoce el nuevo diseño de la app.",
    "Meu pai não fez a transferência ainda, pode me ajudar a fazer?",
    "Mi esposo no hizo el pago de la tarjeta este mes.",
    "Mi mamá no hizo la transferencia que le pedí ayer.",
    "Meu filho não fez o pagamento do boleto da escola.",
    # set-up: subjunctive relative clause and present-tense "inclui"
    "Quiero un pago programado que no inicie hasta el lunes.",
    "A assinatura que eu tenho não inclui frete, posso mudar o plano?",
    # intrusion: relative "que" and coordinated named subjects
    "Los técnicos que entraron a mi cuenta me ayudaron con la clave.",
    "Mis hijos usan la app y entraron a mi cuenta ayer para ver el saldo.",
    # owner-listed hard negatives: recognition, layout, no fraud, authorized
    # user, benign subscription management and merchant identification
    "Todos los cargos del mes los reconozco; ¿cuánto tengo disponible?",
    "Todas as cobranças da fatura eu reconheço, quero só ver o limite.",
    "No reconozco la nueva pantalla de inicio del app.",
    "Não reconheço o layout novo do aplicativo.",
    "Aquí no hay fraude, solo quiero el saldo.",
    "Não é fraude, está tudo certo; só quero o extrato.",
    "Quiero agregar a mi esposo como usuario autorizado de la tarjeta.",
    "Quero cadastrar meu filho como dependente autorizado no cartão.",
    "Quiero dar de baja mi suscripción a una plataforma de música.",
    "¿De qué comercio es este cobro que dice LMN STRM?",
    "Qual estabelecimento é essa cobrança com o nome XPTO?",
]

# Hypothetical / advice questions built on every RF1O family. RF1N observed a
# hypothetical non-recognition question escalating; RF1O must not widen that.
_HYPOTHETICALS = [
    "Si un día me salen cargos en un sitio donde jamás estuve, ¿cómo procedo?",
    "¿Qué pasa si aparecen compras en un país donde no he viajado?",
    "E se aparecerem compras num lugar onde jamais estive?",
    "Supongamos que hay un destinatario que yo nunca agregué: ¿cómo lo borro?",
    "Se aparecer uma assinatura que eu nunca contratei, o que faço?",
    "Si recibo un código para una transferencia que yo no inicié, ¿qué hago?",
    "Se eu receber um código de um Pix que eu não iniciei, o que faço?",
    "¿Qué hago si nadie de mi hogar reconoce un cargo?",
    "Me expliquem: se um dia surgir um débito que ninguém aqui em casa reconheceu, qual é o procedimento?",
    "¿Qué pasa si invadieron mi banca y no lo noto?",
    "Si alguien entra a mi cuenta, ¿cómo lo bloqueo?",
    "¿Qué hago si me avisan de una compra que no es de mis tarjetas?",
    "Si mi papá dice que él no hizo un retiro, ¿qué debe hacer?",
    "Caso minha mãe não reconheça um débito, o que ela deve fazer?",
    "Me expliquem: se um dia surgir um débito que eu não reconheço na fatura, qual é o procedimento?",
    "Vocês me orientam sobre o que fazer se por acaso houver um débito que eu não reconheço?",
    "Como devo proceder se um dia surgir um Pix que eu não reconheço?",
]


@pytest.mark.parametrize(("family", "message"), _FAMILY_POSITIVES)
def test_rf1o_family_positives_are_unauthorized_assertions(family: str, message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True
    assert any(
        finding.asserted and finding.family == family
        for finding in denial_safety_findings(message)
    )


@pytest.mark.parametrize("message", _FAMILY_NEGATIVES)
def test_rf1o_family_near_misses_are_not_reported(message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is False
    assert not any(finding.asserted for finding in denial_safety_findings(message))
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize("message", _HYPOTHETICALS)
def test_rf1o_hypothetical_questions_are_not_licensed_by_the_layer(message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is False
    assert not any(finding.asserted for finding in denial_safety_findings(message))


@pytest.mark.parametrize(
    "message",
    [
        message
        for message in _HYPOTHETICALS
        # This embedded "se um dia" advice frame is a pre-existing structural
        # over-assertion (like RF1N N1I01-ES); RF1O does not change the resolver.
        if not message.startswith("Como devo proceder")
    ],
)
def test_rf1o_hypothetical_questions_are_not_detected(message: str) -> None:
    assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is False


@pytest.mark.parametrize(
    "message",
    [
        "Vocês me orientam sobre o que fazer se por acaso houver um débito que eu não reconheço?",
        "Como devo proceder se um dia surgir um Pix que eu não reconheço?",
    ],
)
def test_rf1o_portuguese_indefinite_future_frame_is_a_protasis(message: str) -> None:
    # Before RF1O the layer licensed these: the relative clause was treated as a
    # presupposition and "se por acaso" / "se um dia" was not read as a protasis.
    (finding,) = denial_safety_findings(message)
    assert finding.family == "non_recognition"
    assert finding.blocked_by == "conditional_protasis"


@pytest.mark.parametrize(
    ("message", "blocked_by"),
    [
        ("Le confirmo que no programé ningún pago este mes.", None),
        ("No inscribí al destinatario porque la app me pedía un código.", None),
        ("Todavía no programé el pago de la luz, ¿cómo lo hago?", None),
        ("Viajaré a una región donde jamás he ido; ¿puedo pagar con la tarjeta allá?", "no_activity_anchor"),
        ("Quiero sacar efectivo en un país donde no he estado antes, ¿cobran comisión por retiros?", "no_activity_anchor"),
        ("Hice compras en una ciudad donde nunca había estado y me bloquearon la tarjeta.", "activity_not_observed"),
        ("Aparecen retiros en un pueblo adonde jamás he ido, pero era mi hija con la tarjeta adicional.", "authorized_third_party"),
        ("Nadie en mi familia hizo compras este mes, ¿por qué mi saldo es igual?", "no_existing_item"),
        ("Mi hija entró a mi cuenta para pagar la luz.", "named_or_negated_subject"),
        ("Mis papás entraron a mi cuenta para ver el saldo.", "named_or_negated_subject"),
        ("Entraron a mi cuenta de Netflix y cambiaron el perfil.", "non_bank_account"),
        ("Tal vez entraron a mi cuenta, no sé.", "uncertainty_hedge"),
        ("El cargo no es de mi tarjeta, es de la tarjeta de mi esposo.", "corrective_reattribution"),
        ("Mi hijo no hizo esa compra, la hice yo.", "self_performed_activity"),
        ("Mi papá no hizo el pago porque no le alcanzó.", "no_existing_item"),
        ("Mi mamá no envió esa transferencia todavía, la va a mandar hoy.", "not_yet_or_causal"),
        ("Mi abuela dice que ella no hizo el pago de la luz.", "no_existing_item"),
    ],
)
def test_rf1o_findings_record_the_blocking_reason(message: str, blocked_by: str | None) -> None:
    findings = denial_safety_findings(message)
    if blocked_by is None:
        # Not even a cue: the item is not presupposed to exist.
        assert not any(finding.family == "non_origination" for finding in findings)
        return
    assert findings
    assert blocked_by in {finding.blocked_by for finding in findings}
    assert not any(finding.asserted for finding in findings)


def test_rf1o_setup_denial_requires_an_existing_item() -> None:
    # Indefinite and bare objects describe something never set up, not a disowning.
    assert not denial_safety_findings("Nunca programé un pago automático.")
    assert not denial_safety_findings("Eu nunca cadastrei favorecido, como faço?")
    # A relative clause needs a nominal head, not a complementizer.
    (complement,) = denial_safety_findings("Te aviso que yo nunca inicié nada.")
    assert complement.asserted is False
    # The demonstrative object carries the back-reference across sentences.
    (borrowed,) = denial_safety_findings(
        "Hay un cobro de un gimnasio. Bueno, la verdad es que jamás me he suscrito a ese lugar."
    )
    assert borrowed.asserted is True
    assert borrowed.anchor == "cobro"


def test_rf1o_intrusion_singular_needs_an_unnamed_subject() -> None:
    assert denial_safety_assertion("Alguien más se metió en mi banca.", frozenset()) is True
    assert denial_safety_assertion("Mi esposo se metió en mi banca.", frozenset()) is False
    assert denial_safety_assertion("Sospecho que entraron a mi app.", frozenset()) is True
    assert denial_safety_assertion("Sospecho que no entraron a mi app.", frozenset()) is False


def test_rf1o_presence_denial_requires_observed_prior_activity() -> None:
    # The located activity must be observed and precede the place clause.
    assert denial_safety_assertion(
        "Me cobraron un consumo en un bar adonde no he ido nunca.", frozenset()
    ) is True
    assert denial_safety_assertion(
        "En un país en el que jamás he viajado me gustaría hacer compras.", frozenset()
    ) is False


def test_rf1o_third_party_denial_needs_a_named_relative() -> None:
    assert denial_safety_assertion(
        "Hay un retiro en la cuenta y ella no lo hizo.", frozenset()
    ) is False
    assert denial_safety_assertion(
        "Mi tía me pidió ayuda: hay un retiro en la cuenta y ella no lo hizo.", frozenset()
    ) is True


def test_rf1o_layer_never_consults_legacy_regex_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_legacy_regex(*_args, **_kwargs):
        raise AssertionError("legacy whole-message regex inventory was consulted")

    monkeypatch.setattr(unauthorized_signals, "_matches_any", fail_legacy_regex)
    for _family, message in _FAMILY_POSITIVES:
        assert unauthorized_signals.is_explicit_unauthorized_assertion(message) is True


@pytest.mark.parametrize("mode", ["hypothetical", "uncertain", "authorized_third_party", "retracted"])
@pytest.mark.parametrize(
    "message",
    [
        "Hay un beneficiario en mi lista que yo jamás inscribí.",
        "Anoche entraron a mi banca en línea y cambiaron la clave.",
        "Tem um gasto num posto que ninguém da minha casa reconhece.",
    ],
)
def test_rf1o_structural_non_assertive_modes_still_veto(mode: str, message: str) -> None:
    assert denial_safety_assertion(message, frozenset()) is True
    assert denial_safety_assertion(message, frozenset({mode})) is False


# ---------------------------------------------------------------- HTTP matrix
_OWNED = {"lucia": "DEMO-ES-1001", "rafael": "DEMO-PT-2001"}
_FOREIGN = {"lucia": "DEMO-PT-2001", "rafael": "DEMO-ES-1001"}
_FOREIGN_MARKERS = {
    "DEMO-PT-2001": ("Mercado Bairro", "219.90", "219,90", "BRL"),
    "DEMO-ES-1001": ("Mercado Central", "125000", "125.000", "COP"),
}
_HTTP_CASES = [
    ("lucia", "es", "La transferencia {ref} va a un beneficiario que jamás di de alta.",
     "Hay un beneficiario en mi lista que yo jamás inscribí."),
    ("lucia", "es", "El aviso del pago {ref} me llegó, y ese pago no es de mis cuentas.",
     "Anoche entraron a mi banca en línea y cambiaron la clave."),
    ("lucia", "es", "Mi mamá dice que ella no reconoce el pago {ref}.",
     "Escribo por mi abuela: le aparecen retiros y ella no los hizo."),
    ("rafael", "pt", "Vi o saque {ref} feito num bairro de Manaus onde jamais pisei.",
     "Apareceram compras num shopping de Recife, onde eu nunca fui."),
    ("rafael", "pt", "O débito {ref} é de uma loja que ninguém aqui em casa reconheceu.",
     "Hoje cedo entraram na minha conta e fizeram um Pix."),
    ("rafael", "pt", "Chegou um SMS para confirmar o Pix {ref}, um Pix que jamais iniciei.",
     "Meu avô reclama que sumiu dinheiro da conta dele; ele jamais autorizou isso."),
]


def _client(tmp_path):
    context = build_app_context(
        Settings(
            bank_db_path=tmp_path / "demo.duckdb",
            runtime_db_path=tmp_path / "runtime.sqlite",
            data_mode="synthetic",
        )
    )
    return TestClient(create_app(context)), context


def _turn(client: TestClient, persona: str, language: str, message: str) -> tuple[dict, dict]:
    session = client.post(
        "/api/demo/sessions",
        json={"persona_id": persona, "language": language},
    ).json()
    response = client.post(
        "/api/customer/turn",
        json={"message": message},
        headers={"X-Demo-Session": session["session_id"]},
    )
    assert response.status_code == 200
    return session, response.json()


def _escalation_context(context, session: dict, body: dict):
    assert body["route"] == "ESCALATE"
    assert body["reason_codes"] == ["unauthorized_activity_reported"]
    assert body["transactions"] == []
    assert body["products"] == []
    assert body["clarification_transaction_ids"] == []
    ticket_id = UUID(body["escalation_ticket_id"])
    resolved = context.store.resolve_verified_escalation_context(ticket_id)
    assert resolved is not None
    assert str(resolved.session.session_id) == session["session_id"]
    assert resolved.session.tenant_id == session["tenant_id"]
    assert ticket_id in context.store.list_verified_escalation_ticket_ids_for_tenant(
        session["tenant_id"]
    )
    assert resolved.reason_code == "unauthorized_activity_reported"
    return resolved


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1o_owned_reference_escalates_without_status_answer(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    owned = _OWNED[persona]
    session, body = _turn(client, persona, language, with_ref.format(ref=owned))
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id == owned
    lowered = body["response_text"].casefold()
    assert not any(
        status in lowered
        for status in ("aprobada", "aprovada", "pendiente", "pendente", "rechazada", "recusada")
    )


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1o_foreign_reference_escalates_without_disclosure_or_attachment(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    foreign = _FOREIGN[persona]
    session, body = _turn(client, persona, language, with_ref.format(ref=foreign))
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None
    blob = str(body) + (resolved.summary or "")
    assert not any(marker in blob for marker in _FOREIGN_MARKERS[foreign])


@pytest.mark.parametrize(("persona", "language", "with_ref", "no_ref"), _HTTP_CASES)
def test_rf1o_unreferenced_report_escalates_with_session_only_ticket(
    tmp_path, persona, language, with_ref, no_ref
) -> None:
    client, context = _client(tmp_path)
    session, body = _turn(client, persona, language, no_ref)
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None


def test_rf1o_third_party_report_discloses_nothing_and_stays_in_session_tenant(tmp_path) -> None:
    client, context = _client(tmp_path)
    message = (
        "Mi tía me pidió ayuda: hay un retiro en la cuenta y ella no lo hizo. "
        "¿Me pueden decir qué movimientos tiene la cuenta de ella?"
    )
    session, body = _turn(client, "lucia", "es", message)
    resolved = _escalation_context(context, session, body)
    assert resolved.transaction_id is None
    other, _ = _turn(client, "rafael", "pt", "Qual é o meu saldo?")
    assert UUID(body["escalation_ticket_id"]) not in (
        context.store.list_verified_escalation_ticket_ids_for_tenant(other["tenant_id"])
    )
    for markers in _FOREIGN_MARKERS.values():
        assert not any(marker in str(body) for marker in markers)


@pytest.mark.parametrize(
    ("persona", "language", "message"),
    [
        ("lucia", "es", "Si un día me salen cargos en un sitio donde jamás estuve, ¿cómo procedo?"),
        ("rafael", "pt", "Se aparecer uma assinatura que eu nunca contratei, o que faço?"),
        ("rafael", "pt", "Me expliquem: se um dia surgir um débito que eu não reconheço na fatura, qual é o procedimento?"),
        ("lucia", "es", "Nadie accedió a mi cuenta; solo necesito el saldo."),
        ("lucia", "es", "Quiero dar de baja mi suscripción a una plataforma de música."),
    ],
)
def test_rf1o_hypotheticals_and_near_misses_do_not_escalate_as_unauthorized(
    tmp_path, persona, language, message
) -> None:
    client, _ = _client(tmp_path)
    _, body = _turn(client, persona, language, message)
    assert "unauthorized_activity_reported" not in body["reason_codes"]
    assert body.get("escalation_ticket_id") is None
