"""RF4 B-HYBRID fail-safe escalation floor.

The authoritative unauthorized-activity detector
(``app.unauthorized_signals.is_explicit_unauthorized_assertion``) is unchanged.
This module adds a separate, deterministic recall floor that the interpretation
post-check consults only when that detector is silent. It can only add an
escalation; it can never remove one (monotonic ``false -> true``).

Contract
--------
The floor fires only when **both** are present in the customer's message:

1. a closed first-person **denial / non-consent cue**: non-consent ("sin mi
   permiso", "não autorizei"), non-recognition ("no reconozco"), negated self
   agency ("no fui yo", "eu não fiz", "nunca estuve"), or attribution of the act
   to another party with a negated self ("foi outra pessoa ..., não eu"); and
2. a **money / instrument / account mention** (plata, saldo, cuenta, tarjeta,
   cupo, CDT, dinheiro, conta, cartão, Pix, ...).

Negated-self and non-recognition cues additionally need some account event in
the message (a charge, a withdrawal, money leaving, an item appearing), so that
"no he usado la tarjeta en meses" is not treated as a report.

Every cue then passes through one **centralized guard table**, applied the same
way to every cue family:

``hypothetical``         conditional / hypothetical frame before the cue
``worry_or_purpose``     fear, wish or purpose frame ("me da miedo que", "para que")
``prevention_question``  the cue sits inside a prevention / procedure / policy /
                         education / insurance question (including a fronted
                         "Sin mi permiso, ¿pueden ...?" fragment)
``interface``            non-recognition of the app, a screen, menu or icon
``lawful_cause``         seizure, embargo, garnishment, tax authority, court order,
                         fee, interest, collections, chargeback, bank-initiated debit
``failure_to_act``       the customer did not pay or could not pay
``retraction``           the customer recalls or confirms it was theirs
``permission``           explicit permission to the actor
``double_negation``      "no es que no ..."
``no_transaction``       data compromise with explicitly no transaction
``declined_own``         "no autorizado" as the status of the customer's own declined
                         payment ("salió como no autorizado ... me rechazaron")
``named_actor``          the act is attributed to a named relative or acquaintance
                         (the product's existing policy for such reports)
``hearsay``              someone else's account, or something heard or read
``incoming``             money that arrived, not money that left
``no_event``             no account event for a negated-self / non-recognition cue

Escalations from this floor carry the distinct reason code
``possible_unauthorized_activity``. They are a conservative request for human
review, not a fraud determination.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ------------------------------------------------------------------ normalization


def _normalize(text: str) -> str:
    lowered = unicodedata.normalize("NFC", text).casefold()
    # Accent folding would merge the affirmative "sí" with the conditional "si".
    lowered = re.sub(r"(?<!\w)sí(?!\w)", " si_afirm ", lowered)
    folded = unicodedata.normalize("NFKD", lowered)
    folded = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(folded.split())


@dataclass(frozen=True, slots=True)
class _Segment:
    text: str
    interrogative: bool
    # A comma-ended fragment directly followed by "¿...?" ("Sin mi permiso,
    # ¿pueden ...?"): the question that follows, when there is one.
    question_lead: str | None = None


_TAG_QUESTION = re.compile(
    r"^\s*(?:cierto|verdad|no|correcto|certo|ne|nao e|nao e mesmo|ok|tudo bem)\s*\??\s*$"
)


def _segments(normalized: str) -> list[_Segment]:
    """Split on sentence punctuation, ';' and an opening '¿'; mark questions."""

    parts: list[tuple[str, bool]] = []
    buffer = ""
    opened_question = False
    for char in normalized:
        if char == "¿":
            if buffer.strip():
                parts.append((buffer, opened_question))
            buffer, opened_question = "", True
            continue
        buffer += char
        if char in ".!?;":
            parts.append((buffer, opened_question or char == "?"))
            buffer, opened_question = "", False
    if buffer.strip():
        parts.append((buffer, opened_question))

    segments: list[_Segment] = []
    for text, interrogative in parts:
        if interrogative and segments and _TAG_QUESTION.match(text.strip(" ?")):
            # "..., ¿cierto?" turns the preceding statement into a question.
            previous = segments.pop()
            segments.append(_Segment(previous.text, True))
            continue
        if interrogative and segments and segments[-1].text.endswith(","):
            previous = segments.pop()
            segments.append(_Segment(previous.text, previous.interrogative, text.strip()))
        segments.append(_Segment(text.strip(), interrogative))
    return segments


def _rx(*parts: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{part})" for part in parts))


# ------------------------------------------------------------------ cue families

_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "non_consent",
        _rx(
            # es
            r"\bsin (?:haber dado |dar )?(?:mi |su |ningun |ninguna )?"
            r"(?:permiso|autorizacion|consentimiento|aval)\b",
            r"\bsin que yo (?:lo |la |los |las )?(?:supiera|autorizara|aprobara|permitiera|"
            r"pidiera|solicitara)\b",
            r"\b(?:no|nunca|jamas) (?:le |les )?(?:he dado|di|otorgue|firme) "
            r"(?:(?:ninguna|ningun|mi|el|la|ese|esa) )?(?:permiso|autorizacion|consentimiento|aval)\b",
            r"\b(?:no|nunca|jamas) (?:lo |la |los |las |le )?(?:autorice|he autorizado|aprobe|"
            r"he aprobado|consenti|permiti|solicite|he solicitado|contrate|he contratado|acepte)\b",
            r"\bno autorizad[oa]s?\b",
            # pt
            r"\bsem (?:ter dado |dar )?(?:a |o )?(?:minha |meu |nenhuma |nenhum )?"
            r"(?:permissao|autorizacao|consentimento|anuencia|aval)\b",
            r"\bsem (?:que )?eu (?:saber|soubesse|autorizar|autorizasse|permitir|permitisse|"
            r"consentir|pedir|pedisse|solicitar|ter (?:contratado|pedido|feito|autorizado|solicitado))\b",
            r"\b(?:nao|nunca|jamais) (?:o |a |os |as |lhe )?(?:autorizei|aprovei|consenti|"
            r"permiti|solicitei|contratei|aceitei)\b",
            r"\b(?:nao|nunca|jamais) dei (?:(?:nenhuma|nenhum|minha|meu|a|o|essa|esse) )?"
            r"(?:permissao|autorizacao|consentimento|aval)\b",
            r"\bnao autorizad[oa]s?\b",
        ),
    ),
    (
        "non_recognition",
        _rx(
            r"\b(?:no|tampoco) (?:lo |la |los |las )?(?:reconozco|reconoci|identifico)\b",
            r"\bdesconozco\b",
            r"\b(?:nao|tambem nao) (?:o |a |os |as )?(?:reconheco|reconheci|identifico)\b",
            r"\bdesconheco\b",
        ),
    ),
    (
        "negated_self",
        _rx(
            # es
            r"\bno fui yo\b",
            r"\byo no fui\b",
            r"\bno (?:soy|he sido) yo\b",
            r"\byo no\s*(?:[.,;!?]|$)",
            r"\b(?:no|nunca|jamas) (?:lo |la |los |las |le |me )?(?:hice|he hecho|realice|"
            r"he realizado|efectue|pedi|he pedido|compre|he comprado|saque|he sacado|retire|"
            r"he retirado|transferi|envie|use|he usado|toque|movi|gaste|he gastado|estuve|"
            r"he estado|entre|accedi|visite|di esos datos|di mis datos|comparti)\b",
            r"\bsin ningun (?:movimiento|retiro|gasto) mio\b",
            r"\b(?:lo|la|eso|esto) hizo otra persona\b",
            r"\b(?:fue|lo hizo) (?:otra persona|un tercero)\b",
            r"\bnadie (?:de (?:la casa|mi casa|mi familia)|en (?:la|mi) casa) "
            r"(?:lo |la |los |las )?(?:toco|uso|saco|hizo|movio|gasto)\b",
            # pt
            r"\bnao fui eu\b",
            r"\bnao sou eu\b",
            r"\bnao eu\s*(?:[.,;!?]|$)",
            r"\beu nao\s*(?:[.,;!?]|$)",
            r"\b(?:eu )?(?:nao|nunca|jamais) (?:o |a |os |as |lhe |me )?(?:fiz|tenho feito|"
            r"realizei|efetuei|pedi|comprei|saquei|tirei|transferi|enviei|usei|mexi|movi|"
            r"gastei|estive|entrei|acessei|visitei|passei|contratei)\b",
            r"\bsem nenhuma (?:movimentacao|operacao|transacao|acao) minha\b",
            r"\b(?:foi|quem fez foi) (?:outra pessoa|um terceiro)\b",
            r"\bninguem (?:de casa|da (?:minha )?familia|(?:aqui )?em casa) "
            r"(?:o |a |os |as )?(?:mexeu|usou|tirou|sacou|fez|gastou)\b",
        ),
    ),
)

# ------------------------------------------------------------- money / instrument

_FINANCIAL = _rx(
    r"\b(?:plata|platica|dinero|fondos?|saldos?|ahorros?|ahorrad[oa]s?|cuentas?|tarjetas?|"
    r"cupo|cdt|prima|nomina|cesantias|cargos?|cobros?|compras?|pagos?|debitos?|retiros?|"
    r"transferencias?|movimientos?|transacciones|transaccion|operaciones|operacion|"
    r"consumos?|avances?|suscripciones|suscripcion|credito|creditos|prestamos?|pesos|"
    r"cajero|extracto|pasajes|sueldo|salario|bono|cheque)\b",
    r"\b(?:dinheiro|grana|poupanca|contas?|cartao|cartoes|limite|cdb|salario|cobrancas?|"
    r"pagamentos?|saques?|pix|ted|boletos?|lancamentos?|movimentacao|movimentacoes|"
    r"transacao|transacoes|operacao|operacoes|assinaturas?|gastos?|emprestimos?|reais|"
    r"fatura|debito automatico|cheque especial)\b",
    r"\$",
)

# An account event somewhere in the message (outside the cue itself).
_EVENT = _rx(
    r"\b(?:cargos?|cobros?|compras?|pagos?|debitos?|retiros?|transferencias?|movimientos?|"
    r"transacciones|transaccion|operaciones|consumos?|avances?|suscripciones|suscripcion|"
    r"cobrancas?|pagamentos?|lancamentos?|transacao|transacoes|saques?|pix|ted|gastos?|"
    r"movimentacao|movimentacoes|assinaturas?|emprestimos?|pedidos|domicilios|delivery)\b",
    r"\b(?:sacaron|saco|sacando|sacaram|sacou|retiraron|retirado|tiraram|tirou|tirando|"
    r"cobraron|cobrando|cobraram|cobrou|debitaron|debitando|debitaram|debitou|descontaron|"
    r"descontaram|compraron|comprando|compraram|comprou|transfirieron|transfirio|"
    r"transferiram|transferiu|usaron|usando|usaram|usou|utilizaron|gastaron|gastaram|gastou|"
    r"pagando|pagaron|pagaram|pidiendo|pidieron|pediram|pedindo|hicieron|fizeram|fazendo|haciendo|hecha|hecho|"
    r"feita|feito|movieron|vaciaron|vaciada|vaciado|esvaziaram|esvaziou|esfumo|evaporo|"
    r"evaporado|evaporou|desaparecio|desaparecieron|desapareceu|sumiu|sumiram|zerou|"
    r"zerado|zerada|some|somem|sumindo|desaparece|desaparecen|aparecio|aparecieron|aparece|aparecen|apareceu|apareceram|aparecem|"
    r"salio|salieron|saiu|sairam|contrataron|clonaron|clonaram|robaron|roubaram|furtaram|"
    r"hackearon|hackearam|pegaram|tomaron|llevaron|levaram|entraron|entraram|accedieron|"
    r"acessaram|abrieron|abriram)\b",
    r"\b(?:ya no (?:esta|estaba|aparece|aparecia)|nao (?:esta|estava) mais)\b",
)
_INSTRUMENT_PHRASE = re.compile(
    r"\b(?:tarjeta (?:de )?(?:debito|credito)|cartao de (?:debito|credito))\b"
)

# ------------------------------------------------------------------ guard lexicons

_HYPOTHETICAL = _rx(
    r"\bsi\b(?!_afirm)",
    r"\ben caso de\b",
    r"\bpor ejemplo\b",
    r"\bsupongamos\b",
    r"\bimagin",
    r"\b(?:o que acontece|o que faco|e) se\b",
    r"\bse (?:um dia|alguem|eu|por acaso|algum|alguma|houver|aparecer)\b",
    r"\bse \w+rem\b",
    # conjunctional "caso" ("caso apareça ..."), not the noun ("abri um caso")
    r"(?<!\bo )(?<!\bel )(?<!\bun )(?<!\bum )(?<!\bmi )(?<!\bmeu )(?<!\beste )(?<!\besse )"
    r"(?<!\beste )(?<!\bnesse )(?<!\bneste )(?<!\bdo )(?<!\bdel )\bcaso (?!de\b)\w+",
    r"\bem caso de\b",
    r"\bpor exemplo\b",
)
_WORRY_OR_PURPOSE = _rx(
    r"\b(?:me da miedo|tengo miedo|temo que|me preocupa|quiero que|no quiero que|"
    r"para que|evitar que|evito que)\b",
    r"\b(?:tenho medo|receio|quero que|nao quero que|para que|evitar que|evito que)\b",
)
_PREVENTION_MARKERS = _rx(
    r"\b(?:evit\w*|proteg\w*|preven\w*|protec\w*|seguro|poliza|apolice|cubre|cobre|"
    r"reporta|reporto|reportar|se reporta|reclam\w*|denunci\w*|contest\w*|procedimiento|"
    r"procedimento|posible|possivel|puede|pueden|podria|pode|podem|cierto|verdad|certo|"
    r"taller|clase|aula|trabajo|trabalho|curso|tarea|escola|colegio|faculdade|significa|"
    r"devuelve|devolve|reembolsa|limite|reducir|reduzir|nadie|ninguem|deja|deixa|"
    r"permite|ativo|activo|bloqueo|bloquear)\b",
    r"\b(?:que es|o que e)\b",
)
_INTERFACE = _rx(
    r"\b(?:app|aplicacion|aplicativo|menu|pantalla|tela|diseno|layout|version|versao|"
    r"iconos?|icones?|boton|botao|interfaz|interface|seccion|secao|aba|opcion|opcao|"
    r"banca en linea|banca movil|internet banking|inicio|actualizacion|atualizacao|"
    r"contrasena|senha|token|usuario|login|visual)\b"
)
_ACTIVITY_NOUN = _rx(
    r"\b(?:cargos?|cobros?|compras?|pagos?|movimientos?|transacciones|transaccion|"
    r"operaciones|operacion|debitos?|retiros?|transferencias?|consumos?|avances?|"
    r"suscripcion|cobrancas?|pagamentos?|lancamentos?|transacao|transacoes|operacao|"
    r"operacoes|saques?|pix|ted|boletos?|gastos?|movimentacao|movimentacoes|assinaturas?|"
    r"emprestimos?|prestamos?)\b"
)
_LAWFUL_CAUSE = _rx(
    r"\b(?:embarg\w*|retencion judicial|orden judicial|ordem judicial|juzgado|juez|judicial|"
    r"dian|receita|impuestos?|impostos?|iof|gmf|cuatro por mil|4x1000|cuota de manejo|"
    r"comision|comisiones|intereses|interes|juros|mora|cobranza|cobro juridico|"
    r"contracargo|chargeback|deudas?|dividas?|penhor\w*|tarifas?|taxas?|multas?|"
    r"anualidad|anuidade|cheque especial)\b",
    r"\b(?:el banco|o banco) (?:me |nos )?(?:debito|cobro|desconto|descontou|retuvo|bloqueo|"
    r"congelo|debitou|cobrou|bloqueou|reteve|congelou)\b",
    r"\b(?:parcela|cuota) (?:do|del|de la|de) (?:emprestimo|prestamo|credito)\b",
)
_CLAUSE_BREAK = re.compile(
    r",|\b(?:pero|mas|porem|y ademas|ademas|e alem disso|alem disso|y tambien|e tambem|"
    r"e ainda|y encima)\b"
)
_ACTOR_OR_OUTFLOW = _rx(
    r"\b(?:alguien|alguem|un desconocido|um desconhecido|otra persona|outra pessoa|"
    r"un tercero|um terceiro|terceiros)\b",
    r"\b(?:sacaron|retiraron|hicieron|compraron|transfirieron|usaron|gastaron|fizeram|"
    r"tiraram|sacaram|compraram|transferiram|usaram|gastaram|apareceu|aparecio)\b",
)
_FAILURE_TO_ACT = _rx(
    r"\b(?:a tiempo|todavia no|aun no|olvid\w*|no pude|no tenia|no tengo|sin saldo|sin fondos|"
    r"fondos insuficientes|saldo insuficiente|mora|vencid\w*|atrasad\w*|hasta que hora|"
    r"puedo pagar|me quede sin)\b",
    r"\bporque (?:no tenia|no tengo|se me olvido|olvide|no pude|no me alcanzo|estaba sin)\b",
    r"\b(?:esqueci|ainda nao|ainda da|ainda posso|no prazo|nao consegui|nao tinha|nao tenho|sem saldo|falta de|"
    r"atras\w*|posso pagar|da tempo|multa)\b",
)
_OBLIGATION_OBJECT = _rx(
    r"^\s*(?:el |la |los |las |mi |o |a |os |as |minha |meu )?"
    r"(?:pago|pagos|cuota|cuotas|factura|facturas|pagamento|pagamentos|fatura|faturas|"
    r"boleto|boletos|parcela|parcelas|abono|recarga)\b"
)
_RETRACTION = _rx(
    r"\b(?:pero|mas|porem)\b.{0,80}\b(?:si_afirm lo hice|lo hice yo|si_afirm fui yo|fui yo|"
    r"fui eu|era mio|era mia|era meu|era minha|me acorde|lembrei|recorde|resulto ser|"
    r"eu mesmo|yo mismo|era de la|era da|era do|era el|era o)\b",
    r"\bya (?:me )?(?:lo |la )?(?:devolvieron|reembolsaron|resolvieron|aclararon|reversaron)\b",
    r"\bja (?:foi )?(?:estornad\w*|devolvid\w*|resolvid\w*)\b",
)
_PERMISSION = _rx(
    r"\bcon mi (?:permiso|autorizacion|consentimiento)\b",
    r"\bcom (?:a )?minha (?:permissao|autorizacao)\b",
    r"\bcomo (?:le |lo )?pedi\b",
    r"\b(?<!nao )eu autorizei\b",
    r"\b(?<!no )yo (?:lo |la )?autorice\b",
)
# "no autorizado" as a label: a declined own payment, or a definitional question.
_ADJECTIVAL_CUE = re.compile(r"\bnao autorizad|\bno autorizad")
_DECLINED_STATUS = _rx(
    r"\b(?:salio|sale|aparece|aparecio|figura|consta|saiu|apareceu|veio|vem|marcad[oa]) "
    r"como (?:no|nao) autorizad",
    r"\b(?:rechaz\w*|declin\w*|recus\w*|deneg\w*|negad[oa]s?|negaron|negaram)\b",
)
_DOUBLE_NEGATION = _rx(r"\bno es que no\b", r"\bnao e que nao\b")
_NO_TRANSACTION = _rx(
    r"\b(?:pero|mas)\b.{0,30}\bno (?:hicieron|han hecho|usaron|han usado) (?:ninguna|ningun|nada)\b",
    r"\b(?:pero|mas)\b.{0,30}\bnao (?:fizeram|usaram) (?:nenhuma|nenhum|nada)\b",
)
_RELATIVE = (
    r"(?:herman\w*|irma\w*|irmao|mama|mae|madre|papa|padre|pai|hij\w*|filh\w*|espos\w*|"
    r"marido|mulher|novi\w*|cunhad\w*|cunad\w*|prim\w*|ti[oa]s?|sobrin\w*|abuel\w*|"
    r"avo|avos|vecin\w*|vizinh\w*|amig\w*|socio|socia|jefe|chefe|companer\w*|colega)"
)
# The product's existing policy: an act attributed to a named relative or
# acquaintance is not an unknown-party report.
_NAMED_ACTOR = _rx(
    r"\bpor (?:mi|mis|meu|minha|meus|minhas|el|la|o|a) " + _RELATIVE + r"\b",
    r"\b(?:fue|foi) (?:mi|meu|minha) " + _RELATIVE + r"\b",
)
_HEARSAY = _rx(
    r"\b(?:dijo|me dijo|conto|me conto|disse|contou|noticias|lei|escuche|ouvi|vi en|vi na|"
    r"vi no)\b"
)
_THIRD_PARTY_POSSESSOR = _rx(
    r"\b(?:de|da|do|del) (?:mi|minha|meu) (?:vecin\w*|vizinh\w*|amig\w*|herman\w*|irma\w*|"
    r"mae|madre|padre|pai|hij\w*|filh\w*|espos\w*|marido|mulher|novi\w*|jefe|chefe|"
    r"cunhad\w*|cunad\w*|prim\w*|ti[oa]s?)\b",
    r"\b(?:dele|dela|deles|delas)\b",
)
_FIRST_PERSON_ASSET = _rx(
    r"\b(?:mi|mis) (?:\w+ )?(?:cuentas?|tarjetas?|plata|dinero|saldo|ahorros|fondos|cupo|cdt|"
    r"nomina|prima)\b",
    r"\b(?:meu|minha|meus|minhas) (?:\w+ )?(?:contas?|cartao|cartoes|dinheiro|saldo|poupanca|"
    r"salario|limite)\b",
)
_INCOMING = _rx(
    r"\b(?:me transfirieron|me consignaron|me depositaron|me abonaron|recibi|me llego|"
    r"me reembolsaron|me mandaron|me enviaron|recebi|caiu|me transferiram|me depositaram|"
    r"creditaram|me mandaram|me enviaram)\b"
)
_OUTFLOW = _rx(
    r"\b(?:sacaron|retiraron|debitaron|cobraron|compraron|gastaron|descontaron|tiraram|"
    r"sacaram|debitaram|cobraram|compraram|gastaram|descontaram|vaciaron|esvaziaram)\b"
)

_ASSERTION_FAMILIES = frozenset({"negated_self", "non_recognition"})


@dataclass(frozen=True, slots=True)
class FailsafeFinding:
    """One floor cue occurrence and the guard decision (for tests and audit)."""

    family: str
    cue: str
    segment_index: int
    fired: bool
    blocked_by: str | None


def _lawful_blocks(segment: str, start: int) -> bool:
    if not _LAWFUL_CAUSE.search(segment):
        return False
    # A genuine report in its own clause next to a lawful cause still escalates:
    # "me embargaron la cuenta y además hicieron una compra que yo no hice".
    bounds = [0, *(m.end() for m in _CLAUSE_BREAK.finditer(segment)), len(segment)]
    for left, right in zip(bounds, bounds[1:]):
        if left <= start < right:
            clause = segment[left:right]
            return bool(_LAWFUL_CAUSE.search(clause)) or not _ACTOR_OR_OUTFLOW.search(clause)
    return True


def _interface_blocks(segment: str, start: int, end: int) -> bool:
    after = segment[end:]
    window = " ".join(after.split()[:6])
    interface = _INTERFACE.search(window)
    activity = _ACTIVITY_NOUN.search(window)
    if interface and (activity is None or interface.start() < activity.start()):
        return True
    if activity is not None:
        return False
    before = segment[:start]
    return bool(_INTERFACE.search(before)) and not _ACTIVITY_NOUN.search(before)


def _guard(
    family: str,
    segments: list[_Segment],
    index: int,
    start: int,
    end: int,
    message: str,
    message_without_cue: str,
) -> str | None:
    segment = segments[index]
    text = segment.text
    before = text[:start]
    after_message = " ".join(s.text for s in segments[index:])[start:]

    if _DOUBLE_NEGATION.search(before):
        return "double_negation"
    if _HYPOTHETICAL.search(before):
        return "hypothetical"
    if _WORRY_OR_PURPOSE.search(before):
        return "worry_or_purpose"
    if segment.interrogative and _PREVENTION_MARKERS.search(text):
        return "prevention_question"
    if segment.interrogative and _HYPOTHETICAL.search(text):
        # "¿Es un uso no autorizado si uso la tarjeta en el exterior?"
        return "hypothetical"
    adjectival = _ADJECTIVAL_CUE.match(text[start:end]) is not None
    if adjectival and _DECLINED_STATUS.search(message):
        return "declined_own"
    if (
        segment.question_lead is not None
        and not _EVENT.search(text[:start] + " " + text[end:])
        and _PREVENTION_MARKERS.search(segment.question_lead)
    ):
        return "prevention_question"
    if family == "non_recognition" and _interface_blocks(text, start, end):
        return "interface"
    if _lawful_blocks(text, start):
        return "lawful_cause"
    if family == "negated_self" and (
        _FAILURE_TO_ACT.search(text) or _OBLIGATION_OBJECT.match(text[end:])
    ):
        return "failure_to_act"
    if _RETRACTION.search(after_message) or _RETRACTION.search(message):
        return "retraction"
    if _PERMISSION.search(message):
        return "permission"
    if _NO_TRANSACTION.search(message):
        return "no_transaction"
    if _NAMED_ACTOR.search(text):
        return "named_actor"
    if (_HEARSAY.search(before) or _THIRD_PARTY_POSSESSOR.search(text)) and not (
        _FIRST_PERSON_ASSET.search(text)
    ):
        return "hearsay"
    if _INCOMING.search(text) and not _OUTFLOW.search(text):
        return "incoming"
    if family in _ASSERTION_FAMILIES and not _EVENT.search(
        _INSTRUMENT_PHRASE.sub(" ", message_without_cue)
    ):
        return "no_event"
    return None


def failsafe_findings(text: str) -> tuple[FailsafeFinding, ...]:
    """Return every floor cue with its guard decision.

    Returns an empty tuple when the message has no money / instrument / account
    mention, because the floor's two-part trigger cannot be met.
    """

    normalized = _normalize(text)
    if not _FINANCIAL.search(_INSTRUMENT_PHRASE.sub(" tarjeta ", normalized)):
        return ()
    segments = _segments(normalized)
    findings: list[FailsafeFinding] = []
    for index, segment in enumerate(segments):
        for family, pattern in _CUES:
            for match in pattern.finditer(segment.text):
                cue_removed = segment.text[: match.start()] + " " + segment.text[match.end():]
                message_without_cue = " ".join(
                    [s.text for s in segments[:index]] + [cue_removed]
                    + [s.text for s in segments[index + 1:]]
                )
                blocked = _guard(
                    family,
                    segments,
                    index,
                    match.start(),
                    match.end(),
                    normalized,
                    message_without_cue,
                )
                findings.append(
                    FailsafeFinding(
                        family=family,
                        cue=match.group(0).strip(" .,;!?"),
                        segment_index=index,
                        fired=blocked is None,
                        blocked_by=blocked,
                    )
                )
    return tuple(findings)


def is_failsafe_escalation(text: str) -> bool:
    """True when the floor alone would escalate this message.

    Callers must consult this only when the authoritative detector is silent;
    the floor never lowers an existing escalation.
    """

    return any(finding.fired for finding in failsafe_findings(text))
