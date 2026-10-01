"""RF1K denial-safety layer for explicit unauthorized-activity assertions.

The RF1H structural resolver is the authoritative ES/PT path. Fresh independent
probes (RF1D, RF1G, RF1J) kept finding natural, explicit first-person denials that
the closed grammar resolves to *no proposition at all*, so the turn was answered as
an ordinary transaction or account request.

This layer is a bounded safety net for that structural silence only. Its contract:

1. Structural precedence. It is consulted only when the resolver produced no
   ASSERTIVE proposition. Any resolved non-assertive mode other than QUESTIONED
   (hypothetical, uncertain, information request, descriptor clarification,
   authorized third party, retracted, reported prior belief) is a veto. QUESTIONED
   is not a veto because interrogative scope is re-checked here clause by clause.
2. Closed cue families. A cue must be a first-person denial of performing,
   authorizing, soliciting, recognizing, or owning account activity. Third-person,
   subjunctive, and "not yet" forms do not match. RF1M adds money-movement denials
   that point back at an existing movement, elliptical ownership denial over listed
   items, and emphatic/elliptical agency denial.
3. Activity anchor. The cue's sentence must name account activity (activity noun,
   charge/debit verb, or use of the customer's card/account). A short follow-up
   sentence may borrow the anchor of the immediately preceding sentence (a
   clause-initial agency denial is measured by its own clause; a "who did it"
   sentence in between extends the reach by exactly one sentence).
4. Scope blockers. A cue inside interrogative scope, a conditional protasis,
   prior-belief/retraction framing, reported speech, double negation, or an
   uncertainty hedge is not an assertion; neither is an agency denial followed by
   a permission grant to the actor, or explained as forgotten or failed. Two
   presupposition forms stay asserted inside questions: a relative-clause denial ("... el cargo que no reconozco?")
   and a factual preterite protasis inside a why-question ("por qué ... si yo no
   compré ...").

It never consults the retired legacy whole-message regex inventory in
``app.unauthorized_signals``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


# Structural modes that are not a veto. Anything else the resolver produced wins.
_NON_VETO_MODES = frozenset({"assertive", "questioned"})


@dataclass(frozen=True, slots=True)
class DenialSafetyFinding:
    """One cue occurrence and the decision taken on it (for tests and audit)."""

    family: str
    cue: str
    sentence_index: int
    asserted: bool
    blocked_by: str | None
    anchor: str | None


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(normalized.split())


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


# ---------------------------------------------------------------- cue families
# Preterite first-person verbs whose negation disowns an activity that happened.
# Payment/transfer verbs are deliberately excluded: "no pagué la cuota" is a
# failure to pay, not a denial of unauthorized activity.
_ES_DISOWN_VERBS = (
    r"(?:hice|realice|efectue|solicite|pedi|compre|he hecho|he realizado|"
    r"he efectuado|he solicitado|he pedido|he comprado)"
)
_PT_DISOWN_VERBS = r"(?:fiz|realizei|efetuei|solicitei|pedi|comprei)"
_ES_CLITICS = r"(?:(?:me|te|le|les|lo|la|los|las|se)\s+){0,2}"
_PT_CLITICS = r"(?:(?:me|lhe|o|a|os|as)\s+){0,2}"

# RF1M money-movement denials. Unlike the disown verbs above, "no envié" /
# "não transferi" is usually a failure to move money, so the family is licensed
# only when (a) the speaker is an explicit first-person subject and (b) the verb
# points back at an existing movement: an object clitic, a demonstrative object,
# a null object closing the clause, or (mover/mexer/tocar) a money object.
_ES_MOVE_VERBS = (
    r"(?:envie|mande|transferi|saque|he enviado|he mandado|he transferido|he sacado)"
)
_PT_MOVE_VERBS = r"(?:enviei|mandei|transferi|saquei)"
_ES_HANDLE_VERBS = r"(?:movi|toque|he movido|he tocado)"
_PT_HANDLE_VERBS = r"(?:mexi|movi|toquei)"
_ES_DEMONSTRATIVE = r"(?:esa|ese|esta|este|esos|esas|estos|estas|eso|esto)"
_PT_DEMONSTRATIVE = r"(?:essa|esse|esta|este|essas|esses|estas|estes|isso|isto)"
_ES_MONEY = (
    r"(?:(?:esa|ese|esta|este|la|el|mi|mis|esos|esas)\s+)?"
    r"(?:plata|platica|dinero|fondos|saldo)"
)
_PT_MONEY = (
    r"(?:(?:em|no|na|nos|nas|nesse|nessa|neste|nesta|nesses|nessas|o|a|meu|minha)\s+)?"
    r"(?:dinheiro|grana|saldo|conta|valor|valores)"
)
_CLAUSE_END = r"(?=\s*(?:,|$))"
_SENTENCE_END = r"(?=\s*$)"
_ES_MOVE_NEG = r"\byo\s+(?:no|nunca|jamas)\s+"
_PT_MOVE_NEG = r"\beu\s+(?:nao|nunca|jamais)\s+"

_CUE_FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "non_recognition",
        # reconosco/reconozo/reconoso: closed misspellings of the core stem only.
        _rx(
            r"\b(?:no|tampoco)\s+(?:(?:lo|la|los|las)\s+)?"
            r"(?:reconozco|reconoci|identifico|reconosco|reconozo|reconoso)\b"
        ),
    ),
    ("non_recognition", _rx(r"(?<!no )(?<!nunca )(?<!tampoco )\b(?:desconozco|desconoci)\b")),
    (
        "non_recognition",
        _rx(r"\b(?:nao|tambem nao)\s+(?:(?:o|a|os|as)\s+)?(?:reconheco|reconheci|identifico)\b"),
    ),
    ("non_recognition", _rx(r"(?<!nao )(?<!nunca )\b(?:desconheco|desconheci)\b")),
    (
        "non_authorization",
        _rx(
            r"\b(?:no|nunca|jamas)\s+" + _ES_CLITICS
            + r"(?:autorice|he autorizado|consenti|aprobe)\b"
        ),
    ),
    (
        "non_authorization",
        _rx(r"\bsin\s+mi\s+(?:autorizacion|consentimiento|permiso|conocimiento)\b"),
    ),
    (
        "non_authorization",
        _rx(r"\bsin\s+que\s+yo\s+(?:lo\s+|la\s+)?(?:sepa|supiera|autorice|autorizara)\b"),
    ),
    ("non_authorization", _rx(r"\bno\s+(?:le\s+|les\s+)?di\s+(?:mi\s+)?(?:permiso|autorizacion)\b")),
    (
        "non_authorization",
        _rx(r"\b(?:nao|nunca|jamais)\s+" + _PT_CLITICS + r"(?:autorizei|consenti|aprovei)\b"),
    ),
    (
        "non_authorization",
        _rx(r"\bsem\s+(?:a\s+)?minha\s+(?:autorizacao|permissao|consentimento|conhecimento)\b"),
    ),
    (
        "non_authorization",
        _rx(r"\bsem\s+(?:que\s+)?eu\s+(?:saber|soubesse|autorizar|autorizasse)\b"),
    ),
    ("non_authorization", _rx(r"\bnao\s+dei\s+(?:(?:a\s+)?minha\s+)?(?:permissao|autorizacao)\b")),
    (
        "non_performance",
        _rx(r"\b(?:no|nunca|jamas)\s+" + _ES_CLITICS + _ES_DISOWN_VERBS + r"\b"),
    ),
    ("non_performance", _rx(r"\b(?:yo no fui|no fui yo|no he sido yo)\b")),
    (
        "non_performance",
        _rx(r"\b(?:nao|nunca|jamais)\s+" + _PT_CLITICS + _PT_DISOWN_VERBS + r"\b"),
    ),
    ("non_performance", _rx(r"\b(?:eu nao fui|nao fui eu)\b")),
    # Emphatic or elliptical agency denial that closes its clause.
    (
        "non_performance",
        _rx(
            r"\byo\s+(?:seguro|seguramente|desde luego|por supuesto|claro|obvio|obviamente|"
            r"definitivamente|ciertamente|te aseguro|le aseguro|les aseguro)\s+"
            r"(?:que\s+)?(?:no|tampoco)(?:\s+(?:fui|he sido))?" + _CLAUSE_END
        ),
    ),
    (
        "non_performance",
        _rx(
            r"\beu\s+(?:e\s+)?que\s+nao\s+(?:fui|fiz)(?:\s+(?:isso|isto|essa|esse))?"
            + _CLAUSE_END
        ),
    ),
    (
        "non_performance",
        _rx(
            r"\beu\s+(?:com certeza|certamente|claro|obviamente|definitivamente|"
            r"te garanto|lhe garanto|garanto)\s+(?:que\s+)?nao(?:\s+(?:fui|fiz))?"
            + _CLAUSE_END
        ),
    ),
    (
        "non_movement",
        _rx(
            _ES_MOVE_NEG + r"(?:(?:me|le|les|se)\s+)?(?:lo|la|los|las)\s+" + _ES_MOVE_VERBS + r"\b"
            + r"|" + _ES_MOVE_NEG + _ES_MOVE_VERBS + r"\s+" + _ES_DEMONSTRATIVE + r"\b"
            + r"|" + _ES_MOVE_NEG + _ES_MOVE_VERBS + _SENTENCE_END
            + r"|" + _ES_MOVE_NEG + _ES_HANDLE_VERBS + r"\s+" + _ES_MONEY + r"\b"
            + r"|\b(?:no|nunca|jamas)\s+(?:lo|la|los|las)\s+" + _ES_MOVE_VERBS + r"\s+yo\b"
        ),
    ),
    (
        "non_movement",
        _rx(
            _PT_MOVE_NEG + r"(?:(?:o|a|os|as)\s+)?" + _PT_MOVE_VERBS + _SENTENCE_END
            + r"|" + _PT_MOVE_NEG + _PT_MOVE_VERBS + r"\s+" + _PT_DEMONSTRATIVE + r"\b"
            + r"|" + _PT_MOVE_NEG + _PT_HANDLE_VERBS + r"\s+" + _PT_MONEY + r"\b"
        ),
    ),
    (
        "passive_agent_denial",
        _rx(
            r"\bno\s+(?:fue|fueron|ha sido|han sido)\s+"
            r"(?:realizad|hech|efectuad|autorizad|solicitad)[oa]s?\s+por\s+mi\b"
        ),
    ),
    (
        "passive_agent_denial",
        _rx(
            r"\bnao\s+(?:foi|foram)\s+"
            r"(?:realizad|feit|efetuad|autorizad|solicitad)[oa]s?\s+por\s+mim\b"
        ),
    ),
    ("ownership_denial", _rx(r"\bno\s+(?:es|son|era|eran|fue|fueron)\s+(?:mio|mia|mios|mias)\b")),
    ("ownership_denial", _rx(r"\bnao\s+(?:e|sao|era|eram|foi|foram)\s+(?:meu|minha|meus|minhas)\b")),
    # Elliptical ownership denial over listed items ("ninguno es mío").
    (
        "ownership_denial",
        _rx(
            r"\bningun[oa]s?\s+(?:de\s+(?:ellos|ellas|esos|esas|estos|estas|los|las)"
            r"(?:\s+[a-z]+){0,2}\s+)?"
            r"(?:(?:es|son|era|eran|fue|fueron)\s+(?:mio|mia|mios|mias)|me\s+pertenecen?)\b"
        ),
    ),
    (
        "ownership_denial",
        _rx(
            r"\bnenhum(?:a)?\s+(?:(?:dele|dela|deles|delas|desse|dessa|desses|dessas|deste|"
            r"desta|destes|destas|dos|das)(?:\s+[a-z]+){0,2}\s+)?"
            r"(?:(?:e|era|foi)\s+(?:meu|minha|meus|minhas)|me\s+pertence)\b"
        ),
    ),
    (
        "negated_truth",
        _rx(
            r"\bno\s+es\s+(?:cierto|verdad)\s+que\s+(?:yo\s+)?(?:haya|hubiera)\s+"
            r"(?:hecho|realizado|efectuado|autorizado|solicitado|comprado)\b"
        ),
    ),
    (
        "negated_truth",
        _rx(
            r"\bnao\s+e\s+verdade\s+que\s+(?:eu\s+)?(?:tenha|tivesse)\s+"
            r"(?:feito|realizado|efetuado|autorizado|solicitado|comprado)\b"
        ),
    ),
    (
        "negative_quantifier",
        _rx(
            r"\bningun[oa]s?\s+[^,]{0,60}?(?:,[^,]{0,40},)?\s*"
            r"(?:(?:los|las|lo|la)\s+)?(?:hice|realice|autorice|solicite)\b"
        ),
    ),
    (
        "negative_quantifier",
        _rx(
            r"\bnenhum[a]?s?\s+[^,]{0,60}?(?:,[^,]{0,40},)?\s*"
            r"(?:fui eu que (?:fiz|realizei|autorizei)|eu (?:fiz|realizei|autorizei))\b"
        ),
    ),
)

# ---------------------------------------------------------------- activity anchors
_ANCHORS: tuple[re.Pattern[str], ...] = (
    _rx(
        r"\b(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|"
        r"operacion|operaciones|transaccion|transacciones|transferencia|transferencias|"
        r"debito|debitos|retiro|retiros|consumo|consumos|giro|giros)\b"
    ),
    _rx(
        r"\b(?:cobranca|cobrancas|pagamento|pagamentos|lancamento|lancamentos|operacao|"
        r"operacoes|transacao|transacoes|pix|saque|saques|gasto|gastos|ted|boleto|boletos|"
        r"movimentacao|movimentacoes)\b"
    ),
    _rx(
        r"\b(?:cobraron|cobraban|han cobrado|cargaron|han cargado|debitaron|han debitado|"
        r"sacaron|retiraron|transfirieron|cobraram|cobrou|debitaram|debitou|tiraram|"
        r"sacaram|transferiram|levaram|vaciaron|han vaciado|esvaziaram|zeraram)\b"
    ),
    _rx(
        r"\b(?:usando|usaron|uso|utilizaron|utilizando|utilizo|usou|usaram)\s+"
        r"(?:mi|mis|minha|minhas|meu|meus)\s+(?:tarjeta|tarjetas|cuenta|cartao|cartoes|conta|datos|dados)\b"
    ),
)
# A reported balance drop is account activity even without an activity noun,
# unless the same sentence explains the drop ("... porque pagué la renta").
_BALANCE_DROP_ANCHOR = _rx(
    r"\b(?:mi|meu|el|o)\s+saldo\s+(?:es|esta|ficou|e)\s+(?:menor|mas bajo|mais baixo)\b"
    r"|\b(?:mi|meu)\s+saldo\s+(?:bajo|disminuyo|cayo|baixou|diminuiu|caiu)\b"
    r"|\b(?:bajo|disminuyo|cayo|baixou|diminuiu|caiu)\s+(?:mi|el|o|meu|o meu)\s+saldo\b"
)
_CAUSAL_MARKER = _rx(r"\b(?:porque|ya que|pues|pois|por causa)\b")

# ---------------------------------------------------------------- scope blockers
_INTERROGATIVE_OPENERS = _rx(
    r"\b(?:que|como|cuando|donde|cual|cuales|quien|quienes|por que|porque|para que|"
    r"o que|quando|onde|qual|quais|quem|pode|podem|podria|podrian|puede|pueden|"
    r"me pueden|me podria|voces podem|vc pode|sera que)\b"
)
_RELATIVIZER_TAIL = _rx(
    r"\b(?:que|quien|quienes|el cual|la cual|los cuales|las cuales|o qual|a qual|"
    r"os quais|as quais)\s+(?:yo\s+|eu\s+)?$"
)
_WHY = _rx(r"\bpor\s*que\b")
_PRETERITE_DISOWN = _rx(
    r"\b(?:hice|realice|efectue|solicite|pedi|compre|autorice|fiz|realizei|efetuei|"
    r"solicitei|comprei|autorizei)\b"
)
_PROTASIS = _rx(
    r"\b(?:si|en caso de que|no caso de|supongamos que|suponhamos que|imagina que|"
    r"imagine que|(?:se|caso) (?=eu\b|nao\b|voce\b|alguem\b|algum\b|alguma\b|a gente\b))"
)
_PRIOR_BELIEF = _rx(
    r"\b(?:pense|pensaba|crei|creia|pensei|achei|achava|imagine|imaginei|supuse|supus)\s+que\b"
    r"|\b(?:iba a decir|ia dizer|ia falar)\b"
)
_REPORTED_SPEECH = _rx(
    r"\b(?:dice|dijo|dicen|dijeron|diz|disse|dizem|disseram|afirma|afirmou|alega|alegou)\s+que\b"
)
_DOUBLE_NEGATION = _rx(r"\b(?:no es que|nao e que)\b")
# A later permission grant makes the activity an authorized third-party one.
# Negated grants ("no le di permiso") are scrubbed first: they are denials.
_NEGATED_GRANT = _rx(
    r"\b(?:no|nao|nunca|jamas|jamais)\s+(?:(?:le|les|lhe|lo|la|o|a)\s+)?"
    r"(?:di|dei|autorice|autorizei|deje|deixei)\b"
)
_PERMISSION_GRANTED = _rx(
    r"\bcon\s+(?:mi|el)\s+(?:permiso|autorizacion|consentimiento)\b"
    r"|\bcom\s+(?:a\s+|o\s+)?(?:minha|meu)\s+(?:permissao|autorizacao|consentimento)\b"
    r"|\b(?:di|dei)\s+(?:(?:mi|minha)\s+)?(?:permiso|permissao|autorizacion|autorizacao)\b"
    r"|\b(?:yo|eu)\s+(?:(?:lo|la|le|o|a)\s+)?(?:autorice|autorizei|deje|deixei)\b"
)
# Forgetting to act explains a movement or act that did not happen.
_FORGOT_TO_ACT = _rx(
    r"\b(?:se me olvido|me olvide de|olvide)\s+(?:de\s+)?"
    r"(?:hacer|hacerla|hacerlo|enviar|enviarla|mandar|mandarla|pagar|transferir|realizar)\b"
    r"|\bse me olvido(?=\s*(?:,|$))"
    r"|\b(?:me\s+)?esqueci\s+(?:de\s+)?(?:fazer|enviar|mandar|pagar|transferir|realizar)\b"
)
# A system failure in the same sentence explains a movement that did not go out.
_SYSTEM_FAILURE = _rx(r"\b(?:travou|deu erro|dio error|no me dejo|nao deixou)\b")
_HEDGE_TAIL = _rx(
    r"\b(?:creo|creia|acho|achava|supongo|suponho|me parece|parece|quizas|quiza|tal vez|"
    r"talvez|puede que|pode ser que|no se si|nao sei se)\s+(?:que\s+)?(?:yo\s+|eu\s+)?$"
)
_NOT_YET_BEFORE = _rx(r"\b(?:todavia|aun|ainda)\s+$")
_NOT_YET_OR_CAUSAL_AFTER = _rx(
    r"^\W*(?:[a-z0-9-]+\s+){0,3}?(?:todavia|aun|ainda|porque|ya que|pues|pois)\b"
)
_LATER_RECOGNITION = _rx(
    r"\b(?:pero|mas|ahora|agora|ya|ja)\b.{0,50}?"
    r"(?:\b(?:si|sim)\s*,?\s*(?:lo |la |o |a )?(?:reconozco|reconheco|hice|fiz)\b"
    r"|\bya\s+(?:lo\s+|la\s+)?(?:reconoci|recorde|vi que|me acorde)\b"
    r"|\bja\s+(?:o\s+|a\s+)?(?:reconheci|lembrei|vi que)\b"
    r"|(?<!no )(?<!nao )\b(?:fui yo|fui eu)\b"
    r"|(?<!no )(?<!nao )(?<!ninguno )(?<!ninguna )(?<!nenhum )(?<!nenhuma )"
    r"\b(?:es|e)\s+(?:mio|mia|meu|minha)\b)"
)
# Non-recognition of a descriptor (name, merchant, code) is a clarification
# request about how an item is labelled, not a denial of the activity itself.
_DESCRIPTOR_OBJECT = _rx(
    r"^\s*(?:(?:el|la|los|las|este|esta|ese|esa|o|a|os|as|esse|essa|este|esta)\s+)?"
    r"(?:nombre|nombres|descripcion|concepto|comercio|comercios|establecimiento|"
    r"referencia|codigo|glosa|detalle|nome|nomes|descricao|estabelecimento|loja|"
    r"referencia|codigo|descritivo)\b"
)
_ANAPHORIC_FAMILIES = frozenset(
    {"non_recognition", "ownership_denial", "non_performance", "non_movement"}
)
_ANAPHORIC_MAX_TOKENS = 8
# Agency denials that open their sentence ("No fui yo, y ...") are measured by
# their own clause, so a trailing coordinated clause does not defeat anaphora.
_CLAUSE_INITIAL_FAMILIES = frozenset({"non_performance", "non_movement"})
_CLAUSE_BREAK = _rx(r",|\s(?:y|e|ni|pero|mas|porque|pois|ya que|sino)\s")
# A "who did it" sentence continues the activity named just before it, so an
# elliptical answer ("Yo seguro que no.") may reach one sentence further back.
_AGENT_REFERENCE = _rx(
    r"\b(?:quien|quienes|quem)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?"
    r"(?:hizo|hicieron|realizo|realizaron|mando|envio|fez|fizeram|realizou|mandou|enviou)\b"
)
_QUESTION_TAG_MAX_TOKENS = 4
# An emphatic first-person subject marks disowning ("no lo hice yo, pues ..."),
# so a following reason clause does not turn it into a failure to perform.
_EMPHATIC_AFTER = _rx(r"^\s*(?:yo|eu)\b")
_EMPHATIC_BEFORE = _rx(r"\b(?:yo|eu)\s+$")


@dataclass(frozen=True, slots=True)
class _Sentence:
    text: str
    question_start: int | None  # offset where interrogative scope begins, if any


def _sentences(normalized: str) -> list[_Sentence]:
    sentences: list[_Sentence] = []
    for raw, delimiter in re.findall(r"([^.!?;:\n]*)([.!?;:\n]+|$)", normalized):
        text = raw.strip(" ,")
        if not text:
            continue
        question_start: int | None = None
        if "¿" in text:
            question_start = text.index("¿")
        elif "?" in delimiter:
            last_comma = text.rfind(",")
            tail_start = last_comma + 1 if last_comma >= 0 else 0
            tail = text[tail_start:].strip()
            # Without an opening mark, a final comma clause that starts with an
            # interrogative/request form, or is a short tag ("me ayudan?"), is the
            # question; otherwise the whole question sentence is in scope.
            if last_comma >= 0 and (
                _INTERROGATIVE_OPENERS.match(tail)
                or len(tail.split()) <= _QUESTION_TAG_MAX_TOKENS
            ):
                question_start = tail_start
            else:
                question_start = 0
        sentences.append(_Sentence(text=text.replace("¿", " "), question_start=question_start))
    return sentences


def _clause_prefix(text: str, start: int) -> str:
    before = text[:start]
    cut = max(before.rfind(","), before.rfind("("))
    return before[cut + 1 :] if cut >= 0 else before


def _anchor(text: str) -> str | None:
    for pattern in _ANCHORS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    balance = _BALANCE_DROP_ANCHOR.search(text)
    if balance and not _CAUSAL_MARKER.search(text):
        return balance.group(0)
    return None


def _anaphora_eligible(text: str, start: int, end: int, family: str) -> bool:
    if len(text.split()) <= _ANAPHORIC_MAX_TOKENS:
        return True
    if family not in _CLAUSE_INITIAL_FAMILIES or len(text[:start].split()) > 1:
        return False
    clause_break = _CLAUSE_BREAK.search(text, end)
    clause = text[: clause_break.start()] if clause_break else text
    return len(clause.split()) <= _ANAPHORIC_MAX_TOKENS


def _borrowed_anchor(sentences: list[_Sentence], index: int) -> str | None:
    previous = sentences[index - 1].text
    anchor = _anchor(previous)
    if anchor is None and index >= 2 and _AGENT_REFERENCE.search(previous):
        anchor = _anchor(sentences[index - 2].text)
    return anchor


def _blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str = "",
) -> str | None:
    text = sentence.text
    before = text[:start]
    prefix = _clause_prefix(text, start)
    presupposed_relative = bool(_RELATIVIZER_TAIL.search(prefix))

    if _DOUBLE_NEGATION.search(before):
        return "double_negation"
    if _PRIOR_BELIEF.search(before):
        return "prior_belief"
    if _REPORTED_SPEECH.search(before):
        return "reported_speech"
    if _HEDGE_TAIL.search(prefix):
        return "uncertainty_hedge"
    if _LATER_RECOGNITION.search(message_tail):
        return "later_recognition"
    if family in _CLAUSE_INITIAL_FAMILIES and _PERMISSION_GRANTED.search(
        _NEGATED_GRANT.sub(" ", message_tail)
    ):
        return "authorized_third_party"

    protasis = _PROTASIS.search(prefix)
    factual_why_protasis = bool(
        protasis
        and _WHY.search(text)
        and _PRETERITE_DISOWN.search(text[start:end])
    )
    if protasis and not factual_why_protasis:
        return "conditional_protasis"

    in_question = sentence.question_start is not None and start >= sentence.question_start
    if in_question and not (presupposed_relative or factual_why_protasis):
        return "interrogative_scope"

    if family == "non_recognition" and _DESCRIPTOR_OBJECT.search(text[end:]):
        return "descriptor_clarification"
    if family == "non_performance":
        if _NOT_YET_BEFORE.search(before):
            return "not_yet_or_causal"
        cue = text[start:end]
        emphatic = (
            "fui" in cue.split()
            or bool(_EMPHATIC_AFTER.search(text[end:]))
            or bool(_EMPHATIC_BEFORE.search(before))
            or cue.startswith(("yo ", "eu "))
        )
        if not emphatic and _NOT_YET_OR_CAUSAL_AFTER.search(text[end:]):
            return "not_yet_or_causal"
    if family in _CLAUSE_INITIAL_FAMILIES and (
        _FORGOT_TO_ACT.search(message_head) or _FORGOT_TO_ACT.search(message_tail)
    ):
        return "not_yet_or_causal"
    if family == "non_movement" and (
        _NOT_YET_BEFORE.search(before)
        or _NOT_YET_OR_CAUSAL_AFTER.search(text[end:])
        or _SYSTEM_FAILURE.search(text)
    ):
        # Even with an emphatic subject, "todavía" / "porque" marks a movement the
        # customer has not made yet or did not make for a reason, not a disowning.
        return "not_yet_or_causal"
    return None


def denial_safety_findings(text: str) -> tuple[DenialSafetyFinding, ...]:
    """Return every cue occurrence with its anchor and blocking decision."""

    normalized = _normalize(text)
    sentences = _sentences(normalized)
    findings: list[DenialSafetyFinding] = []
    for index, sentence in enumerate(sentences):
        seen: set[tuple[int, int]] = set()
        for family, pattern in _CUE_FAMILIES:
            for match in pattern.finditer(sentence.text):
                span = (match.start(), match.end())
                if span in seen:
                    continue
                seen.add(span)
                anchor = _anchor(sentence.text)
                if (
                    anchor is None
                    and family in _ANAPHORIC_FAMILIES
                    and index > 0
                    and _anaphora_eligible(sentence.text, match.start(), match.end(), family)
                ):
                    anchor = _borrowed_anchor(sentences, index)
                tail = " ".join(s.text for s in sentences[index:])[match.end() :]
                head = " ".join(
                    [s.text for s in sentences[:index]] + [sentence.text[: match.start()]]
                )
                blocked = (
                    "no_activity_anchor"
                    if anchor is None
                    else _blocker(sentence, match.start(), match.end(), family, tail, head)
                )
                findings.append(
                    DenialSafetyFinding(
                        family=family,
                        cue=match.group(0),
                        sentence_index=index,
                        asserted=blocked is None,
                        blocked_by=blocked,
                        anchor=anchor,
                    )
                )
    return tuple(findings)


def denial_safety_assertion(text: str, structural_modes: frozenset[str]) -> bool:
    """Return True when the layer licenses an unauthorized-activity assertion.

    ``structural_modes`` are the modes the RF1H resolver produced for ``text``.
    The caller consults this layer only when none of them is ASSERTIVE.
    """

    if structural_modes - _NON_VETO_MODES:
        return False
    return any(finding.asserted for finding in denial_safety_findings(text))
