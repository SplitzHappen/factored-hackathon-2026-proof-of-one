from __future__ import annotations

import re
import unicodedata

from app.denial_safety import denial_safety_assertion, structural_assertion_demotion
from app.unauthorized_grammar import PropositionMode, resolve_positive_propositions


def normalize_unauthorized_text(text: str) -> str:
    """Normalize customer text for deterministic explicit-assertion checks."""

    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.split())


_ES_ACTIVITY = (
    r"(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|"
    r"movimiento|movimientos|operacion|operaciones|transaccion|transacciones|"
    r"transferencia|transferencias|debito|debitos|retiro|retiros|"
    r"consumo|consumos)"
)
_PT_ACTIVITY = (
    r"(?:cobranca|cobrancas|compra|compras|pagamento|pagamentos|"
    r"lancamento|lancamentos|operacao|operacoes|transacao|transacoes|"
    r"transferencia|transferencias|pix|debito|debitos|saque|saques|"
    r"gasto|gastos|ted|boleto|boletos|movimentacao|movimentacoes)"
)

# These patterns remain assertion-oriented, but they cover semantic forms rather
# than a small inventory of exact phrases. The lexical floor is deliberately
# asymmetric: missing an explicit unauthorized-activity report is worse than
# conservatively escalating a rare ambiguous case.
_CORE_ASSERTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Spanish and Portuguese non-recognition, including object clitics.
    re.compile(r"\bno (?:lo |la |los |las )?(?:reconozco|reconoci|identifico)\b"),
    re.compile(r"\b(?:desconozco|desconoci)\b"),
    re.compile(r"\bnao (?:o |a |os |as )?(?:reconheco|reconheci|identifico)\b"),
    re.compile(r"\bdesconheco\b"),
    # Explicit disowning.
    re.compile(r"\bno fui yo\b"),
    re.compile(r"\bnao fui eu\b"),
    re.compile(
        rf"\b{_ES_ACTIVITY}\b.{{0,100}}\b"
        r"no (?:es|fue|son|fueron) (?:mio|mia|mios|mias)\b"
    ),
    re.compile(
        rf"\b{_PT_ACTIVITY}\b.{{0,100}}\b"
        r"nao (?:e|foi|sao|foram) (?:meu|minha|meus|minhas)\b"
    ),
    re.compile(
        rf"\b{_ES_ACTIVITY}(?: [a-z0-9-]+)? "
        r"(?:es|fue) (?:ajeno|ajena|de otra persona)\b"
    ),
    re.compile(
        rf"\b{_PT_ACTIVITY}(?: [a-z0-9-]+)? "
        r"(?:e|foi) (?:de outra pessoa|alheio|alheia)\b"
    ),
    # First-person denial of having performed an activity.
    re.compile(
        rf"\b(?:yo )?no "
        r"(?:hice|realice|efectue|ordene|mande|solicite|pague|retire)\b"
        rf".{{0,80}}\b{_ES_ACTIVITY}\b"
    ),
    re.compile(
        rf"\b{_ES_ACTIVITY}\b.{{0,100}}\b(?:yo )?no "
        r"(?:hice|realice|efectue|ordene|mande|solicite|pague|retire)"
        r"(?: (?:ninguno|ninguna|ningunos|ningunas))?\b"
    ),
    re.compile(
        rf"\b(?:eu )?nao "
        r"(?:fiz|realizei|efetuei|mandei|solicitei|paguei|saquei)\b"
        rf".{{0,80}}\b{_PT_ACTIVITY}\b"
    ),
    re.compile(
        rf"\b{_PT_ACTIVITY}\b.{{0,100}}\b(?:eu )?nao "
        r"(?:fiz|realizei|efetuei|mandei|solicitei|paguei|saquei)"
        r"(?: (?:nenhum|nenhuma))?\b"
    ),
    re.compile(
        r"\b(?:yo )?no "
        r"(?:hice|realice|efectue|ordene|mande|solicite|pague|retire) "
        r"[a-z0-9-]+\b"
    ),
    re.compile(
        r"\b(?:eu )?nao "
        r"(?:fiz|realizei|efetuei|mandei|solicitei|paguei|saquei) "
        r"[a-z0-9-]+\b"
    ),
    re.compile(r"\bno (?:lo|la|los|las) (?:hice|realice|autorice|aprobe|ordene)\b"),
    re.compile(r"\bnao (?:o|a|os|as) (?:fiz|realizei|autorizei|aprovei|mandei)\b"),
    re.compile(r"\b(?:tampoco|tambien no) (?:lo|la) (?:autorice|aprobe|hice)\b"),
    re.compile(r"\btambem nao (?:o|a) (?:autorizei|aprovei|fiz)\b"),
    # Bare "never" forms and noun-first equivalents.
    re.compile(
        r"\b(?:yo )?(?:nunca|jamas) "
        r"(?:hice|realice|efectue|autorice|aprobe|ordene|mande|pague)\b"
        rf".{{0,80}}\b{_ES_ACTIVITY}\b"
    ),
    re.compile(
        rf"\b{_ES_ACTIVITY}\b.{{0,100}}\b(?:yo )?(?:nunca|jamas) "
        r"(?:lo |la )?"
        r"(?:hice|realice|efectue|autorice|aprobe|ordene|mande|pague)\b"
    ),
    re.compile(
        r"\b(?:eu )?(?:nunca|jamais) "
        r"(?:fiz|realizei|efetuei|autorizei|aprovei|mandei|paguei)\b"
        rf".{{0,80}}\b{_PT_ACTIVITY}\b"
    ),
    re.compile(
        rf"\b{_PT_ACTIVITY}\b.{{0,100}}\b(?:eu )?(?:nunca|jamais) "
        r"(?:fiz|realizei|efetuei|autorizei|aprovei|mandei|paguei)\b"
    ),
    # Direct authorization / consent denial.
    re.compile(
        r"\b(?:yo )?no "
        r"(?:autorice|aprobe|di autorizacion|di permiso|di mi consentimiento|"
        r"di consentimiento)\b"
    ),
    re.compile(
        r"\b(?:nunca|jamas) (?:di )?(?:mi )?"
        r"(?:autorizacion|permiso|consentimiento)\b"
    ),
    re.compile(
        r"\b(?:eu )?nao "
        r"(?:autorizei|aprovei|dei autorizacao|dei permissao|"
        r"dei consentimento|deixei)\b"
    ),
    re.compile(
        r"\bem momento algum eu "
        r"(?:autorizei|aprovei|dei autorizacao|dei permissao|dei consentimento)\b"
    ),
    re.compile(
        r"\b(?:nunca|jamais) (?:dei )?(?:(?:minha|meu) )?"
        r"(?:autorizacao|permissao|consentimento)\b"
    ),
    # Adjectival non-authorization, including "not authorized by me".
    re.compile(rf"\b{_ES_ACTIVITY}(?: [a-z0-9-]+)? no autorizad[oa]s?\b"),
    re.compile(
        rf"\b{_ES_ACTIVITY}\b.{{0,100}}\b"
        r"no (?:(?:fue|fueron) )?autorizad[oa]s?(?: por mi)?\b"
    ),
    re.compile(rf"\b{_PT_ACTIVITY}(?: [a-z0-9-]+)? nao autorizad[oa]s?\b"),
    re.compile(
        rf"\b{_PT_ACTIVITY}\b.{{0,100}}\b"
        r"nao (?:(?:foi|foram) )?autorizad[oa]s?(?: por mim)?\b"
    ),
    # Third-party use / account access.
    re.compile(r"\balguien (?:mas )?(?:uso|utilizo|entro|accedio)\b"),
    re.compile(r"\balguem (?:mais )?(?:usou|utilizou|entrou|acessou)\b"),
    re.compile(r"\b(?:lo|la|eso|esto) hizo otra persona\b"),
    re.compile(r"\b(?:quem fez|foi) .{0,30}\boutra pessoa\b.{0,20}\bnao eu\b"),
    re.compile(r"\bno (?:fue|ha sido) (?:hecho|hecha|realizado|realizada) por mi\b"),
    re.compile(r"\bnao (?:foi|foram) (?:feito|feita|feitos|feitas) por mim\b"),
    # Theft, cloning, compromise.
    re.compile(r"\bme (?:robaron|clonaron|hackearon)\b"),
    re.compile(r"\b(?:roubaram|clonaram|hackearam|invadiram|furtaram) (?:meu|minha)\b"),
    re.compile(
        r"\b(?:meu|minha) .{0,30}\b"
        r"foi (?:clonado|clonada|furtado|furtada|roubado|roubada)\b"
    ),
    # Common code-switch wording in the frozen ES/PT stress slice.
    re.compile(
        r"\b(?:that|this) (?:charge|transaction|purchase) "
        r"(?:was not|wasn't|is not|isn't) mine\b"
    ),
    re.compile(
        r"\bi did not (?:make|authorize|approve) "
        r"(?:that|this) (?:charge|transaction|purchase)\b"
    ),
)

# Compositional structures cover productive assertion grammar that should not
# require enumerating each surface phrase. These remain deliberately narrow:
# each pattern encodes an explicit ownership, performance, authorization, or
# origination denial rather than topical fraud language alone.
_COMPOSITIONAL_ASSERTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Coordinated negation: a prior action is denied and authorization is also
    # denied through ni/nem. The second conjunct carries the safety meaning.
    re.compile(
        r"\b(?:nunca|jamas)\b.{0,70}\bni "
        r"(?:lo |la )?(?:autorice|aprobe|consenti|permiti)\b"
    ),
    re.compile(
        r"\b(?:nunca|jamais)\b.{0,70}\bnem "
        r"(?:o |a )?(?:autorizei|aprovei|consenti|permiti)\b"
    ),
    # Negative quantifiers and correlative ownership denial.
    re.compile(
        rf"\b(?:ninguno|ninguna|ningunos|ningunas)\b"
        rf".{{0,80}}\b{_ES_ACTIVITY}\b.{{0,50}}\b"
        r"(?:es|son|fue|fueron) (?:mio|mia|mios|mias)\b"
    ),
    re.compile(
        rf"\bni\b.{{0,80}}\b{_ES_ACTIVITY}\b"
        r".{0,120}\bni\b.{0,80}\b"
        r"(?:es|son|fue|fueron) (?:mio|mia|mios|mias)\b"
    ),
    re.compile(
        rf"\b(?:nenhum|nenhuma|nenhuns|nenhumas)\b"
        rf".{{0,80}}\b{_PT_ACTIVITY}\b.{{0,50}}\b"
        r"(?:e|sao|foi|foram) (?:meu|minha|meus|minhas)\b"
    ),
    re.compile(
        rf"\bnem\b.{{0,80}}\b{_PT_ACTIVITY}\b"
        r".{0,120}\bnem\b.{0,80}\b"
        r"(?:e|sao|foi|foram) (?:meu|minha|meus|minhas)\b"
    ),
    # Idiomatic origination / provenance denial.
    re.compile(
        rf"\b{_ES_ACTIVITY}\b.{{0,80}}\b"
        r"no (?:salio|sale|partio|parte|provino|viene) de mi\b"
    ),
    re.compile(
        rf"\b{_PT_ACTIVITY}\b.{{0,80}}\b"
        r"nao (?:partiu|parte|saiu|sai|veio|vem) de mim\b"
    ),
)


# These are explicit scope signals showing that otherwise risky lexical material
# is not being asserted as a present unauthorized event. Keep them separate
# from the positive grammar so safety recall does not depend on broad negation.
_SCOPE_EXCLUSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Hypothetical / counterfactual questions.
    re.compile(r"^[¿?]?\s*que (?:pasa|pasaria) si\b"),
    re.compile(r"^si (?:algun dia|resultara que|viera|veo|pasara|ocurriera)\b"),
    re.compile(r"^(?:e )?possivel\b"),
    re.compile(r"^se (?:eu |um dia |alguem |a )"),
    # Security-information / policy questions rather than event assertions.
    re.compile(r"^[¿?]?\s*como (?:puedo|podria) (?:protegerme|evitar)\b"),
    re.compile(
        r"^[¿?]?\s*(?:que|cuales) (?:medidas|controles|mecanismos) "
        r"(?:de seguridad )?(?:tienen|usan|ofrecen|hay)\b"
        r".{0,120}\b(?:evitar|prevenir)\b"
        r".{0,100}\b(?:cargo|cargos|compra|compras|pago|pagos|"
        r"transferencia|transferencias|transaccion|transacciones) "
        r"no autorizad[oa]s?\b"
    ),
    re.compile(
        r"^acabo de (?:hacer|realizar|efectuar)\b.{0,120};\s*[¿?]?"
        r"(?:que|cuales) (?:medidas|controles|mecanismos) "
        r"(?:de seguridad )?(?:tienen|usan|ofrecen|hay)\b"
        r".{0,120}\b(?:evitar|prevenir)\b"
        r".{0,100}\b(?:cargo|cargos|compra|compras|pago|pagos|"
        r"transferencia|transferencias|transaccion|transacciones) "
        r"no autorizad[oa]s?\b"
    ),
    re.compile(
        r"^(?:quais|que) (?:medidas|controles|mecanismos) "
        r"(?:de seguranca )?(?:tem|existem|usam|oferecem)\b"
        r".{0,120}\b(?:evitar|prevenir)\b"
        r".{0,100}\b(?:cobranca|cobrancas|compra|compras|pagamento|pagamentos|"
        r"transferencia|transferencias|transacao|transacoes|pix) "
        r"nao autorizad[oa]s?\b"
    ),
    re.compile(r"^quais cuidados\b"),
    re.compile(r"^(?!.*\bnao autorizad[oa]s?\b).{0,100}\btem protecao caso\b"),
    re.compile(r"\b(?:seguro|protecao|proteccion) contra \b"),
    # Merchant/descriptor clarification, not transaction disowning.
    re.compile(
        r"^no reconozco (?:el |la )?(?:nombre|comercio|descriptor|descripcion)\b"
        r".{0,140}\b(?:que comercio es|que establecimiento es|"
        r"a que comercio corresponde)\b"
    ),
    re.compile(
        r"^nao reconheco (?:o |a )?(?:nome|comercio|descritor|descricao)\b"
        r".{0,140}\b(?:qual estabelecimento|a qual estabelecimento|"
        r"que comercio e|a que comercio corresponde)\b"
    ),
    # Same-message retraction / explicit correction.
    re.compile(
        r"\b(?:pense|crei)\b.{0,120}\b(?:pero|mas)\b.{0,120}\b"
        r"(?:si (?:lo |la )?hice|fui yo|era (?:mio|mia)|me acorde)\b.{0,60}$"
    ),
    re.compile(
        r"\b(?:eu )?(?:ia dizer|pensei|achei)\b.{0,120}\b"
        r"(?:mas|porem)\b.{0,120}\b"
        r"(?:fui eu|eu mesmo|era (?:meu|minha)|lembrei)\b.{0,60}$"
    ),
    # Explicitly negating the denial itself.
    re.compile(r"\bno digo que no (?:sea|es) (?:mio|mia)\b"),
    re.compile(r"\bnao (?:estou dizendo|digo) que nao (?:seja|e) (?:meu|minha)\b"),
)


def _is_scope_excluded(normalized: str) -> bool:
    return _matches_any(_SCOPE_EXCLUSION_PATTERNS, normalized)


_PERMISSION_ASSERTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsin (?:mi )?(?:autorizacion|permiso|consentimiento)\b"),
    re.compile(
        r"\bsin que yo (?:lo |la )?"
        r"(?:supiera|aprobara|autorizara|permitiera)\b"
    ),
    re.compile(r"\bnadie (?:tenia|tiene) (?:permiso|autorizacion)\b"),
    re.compile(
        r"\bsem (?:(?:a minha|o meu|minha|meu) )?"
        r"(?:autorizacao|permissao|anuencia|consentimento)\b"
    ),
    re.compile(r"\bsem eu (?:saber|permitir|autorizar|consentir)\b"),
    re.compile(r"\bninguem (?:tinha|tem) (?:permissao|autorizacao)\b"),
)

# Permission language can also appear in a hypothetical policy question. Suppress
# only that narrow form; a separate explicit assertion in the same message can
# still match one of the core patterns above.
_HYPOTHETICAL_PERMISSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bsi (?:algun dia )?alguien\b.{0,100}\b"
        r"sin (?:mi )?(?:autorizacion|permiso|consentimiento)\b"
    ),
    re.compile(
        r"\bse (?:um dia )?alguem\b.{0,100}\b"
        r"sem (?:(?:a minha|o meu|minha|meu) )?"
        r"(?:autorizacao|permissao|consentimento)\b"
    ),
)

_FRAUD_ASSERTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Exact declarative form retained because it was a prior audit miss.
    re.compile(r"^es (?:un )?fraude\b"),
    re.compile(r"^e (?:(?:um|uma) )?(?:fraude|golpe)\b"),
    re.compile(
        r"\b(?:esto|eso|ese|esa|este|esta|cargo|cobro|compra|pago|"
        r"movimiento|operacion|transaccion|transferencia|debito|consumo) "
        r"(?:[a-z0-9-]+ )?(?:es|fue) "
        r"(?:un )?(?:fraude|fraudulento|fraudulenta)\b"
    ),
    re.compile(
        r"\b(?:isso|isto|essa|esse|esta|este|cobranca|compra|pagamento|"
        r"lancamento|operacao|transacao|transferencia|pix|debito|gasto) "
        r"(?:[a-z0-9-]+ )?(?:e|foi) "
        r"(?:um |uma )?(?:fraude|golpe|fraudulento|fraudulenta)\b"
    ),
    re.compile(
        r"\b(?:cobranca|compra|pagamento|lancamento|operacao|transacao|"
        r"transferencia|pix|debito|gasto)(?: [a-z0-9-]+)? "
        r"(?:e|foi) fraudulent[oa]\b"
    ),
)

_FRAUD_UNCERTAINTY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:podria|puede|podra|seria) (?:ser )?(?:un )?fraude\b"),
    re.compile(r"\b(?:pode|poderia|sera) ser (?:um |uma )?(?:fraude|golpe)\b"),
    re.compile(
        r"\bsera que\b.{0,50}\b(?:e|foi) "
        r"(?:um |uma )?(?:fraude|golpe)\b"
    ),
)

_DIRECT_FRAUD_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"^[¿?]?\s*(?:(?:esto|eso|ese|esa|este|esta)\s+)?"
        r"(?:es|fue) (?:un )?fraude\?\s*$"
    ),
    re.compile(
        r"^\s*(?:(?:isso|isto|essa|esse|esta|este)\s+)?"
        r"(?:e|foi) (?:(?:um|uma) )?(?:fraude|golpe)\?\s*$"
    ),
)


def _matches_any(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _is_permission_assertion(normalized: str) -> bool:
    return _matches_any(
        _PERMISSION_ASSERTION_PATTERNS, normalized
    ) and not _matches_any(_HYPOTHETICAL_PERMISSION_PATTERNS, normalized)


def _is_declarative_fraud_assertion(normalized: str) -> bool:
    if not _matches_any(_FRAUD_ASSERTION_PATTERNS, normalized):
        return False
    if _matches_any(_FRAUD_UNCERTAINTY_PATTERNS, normalized):
        return False
    if _matches_any(_DIRECT_FRAUD_QUESTION_PATTERNS, normalized):
        return False
    return True


def is_explicit_unauthorized_assertion(text: str) -> bool:
    """Return True for an explicit unauthorized-activity assertion.

    The RF1H structural resolver is authoritative: any assertive positive in
    either supported grammar returns True. Only when it resolves no assertive
    positive is the bounded RF1K denial-safety layer consulted, and that layer
    defers to every resolved non-assertive mode except QUESTIONED.

    RF1Q narrows that authority for exactly two shapes the resolver asserts but
    which are not active reports: an embedded indefinite-future protasis in an
    advice question, and a non-recognition resolved later in the same message.
    RF1S adds three: a resolution earlier in the same sentence, a past
    non-recognition later attributed to a known relative, and the customer's own
    declined attempt labelled "not authorized". Such an assertive positive is
    demoted, and the denial-safety layer decides.
    """

    propositions = tuple(
        proposition
        for language in ("es", "pt")
        for proposition in resolve_positive_propositions(text, language)
    )
    if any(
        proposition.mode == PropositionMode.ASSERTIVE.value
        and structural_assertion_demotion(
            text, proposition.source_start, proposition.source_end
        )
        is None
        for proposition in propositions
    ):
        return True
    return denial_safety_assertion(
        text, frozenset(proposition.mode for proposition in propositions)
    )
