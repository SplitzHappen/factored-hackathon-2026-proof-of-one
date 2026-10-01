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
   items, and emphatic/elliptical agency denial. RF1O adds report families the
   resolver is also silent on, each bound to an existing referent: set-up /
   initiation / enrollment denial over an existing item, observed activity located
   where the customer has never been, household-wide denial, intrusion into the
   customer's own account by an unnamed party, account-provenance denial ("no es
   de mi cuenta"), and a named relative's denial relayed by the customer. RF1Q
   adds product-anchored families (a product opened in the customer's name, a
   denied product origination, a product in the customer's records disowned) and
   a relative's denial relayed through reported speech. RF1S adds active own-account
   compromise families (an unnamed party's activity tied to the customer's account,
   impersonation in a banking context, a disowned credential change) and widens
   existing ones structurally: observed items heading a relative clause across a
   modifier chain, items located in the customer's financial records, more product
   heads, and relays by someone acting for the account holder.
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
   compré ..."). RF1O families read conditional scope over the whole sentence and
   never use the why-question exception, so hypothetical advice questions built on
   them stay unlicensed. RF1Q blocks every family when the message says the item
   was resolved, refunded, or (after an initial non-recognition) recalled. RF1S
   adds a resolution earlier in the same sentence with no fresh event after it, and
   a past non-recognition later attributed to a known relative.
5. Structural demotion. ``structural_assertion_demotion`` names the shapes the
   resolver asserts that are not active reports: an embedded indefinite-future
   protasis in an advice question and a same-message resolution (RF1Q), plus a
   resolution earlier in the sentence, a later attribution to a known relative,
   and the customer's own declined attempt labelled "no autorizado" (RF1S). The
   caller then lets this layer decide instead.

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

# RF1O set-up denials: initiating, scheduling, subscribing to, contracting, or
# enrolling something (a payee, a recurring debit). Like money movement, "no
# programé el pago" is usually a failure to act, so the verb must point back at an
# item that already exists: a relative clause on it ("... que yo nunca agregué"),
# a demonstrative object ("nunca me suscribí a eso"), or an object clitic with an
# explicit first-person subject ("yo no lo programé"). Normalization drops the
# accent that separates "programé" from subjunctive "programe", so a Spanish
# relative clause needs an explicit "yo" or "nunca/jamás".
_ES_NEG = r"(?:no|nunca|jamas|tampoco)"
_PT_NEG = r"(?:nao|nunca|jamais|tambem nao)"
_ES_SETUP_VERBS = (
    r"(?:inicie|he iniciado|programe|he programado|agende|he agendado|suscribi|he suscrito|"
    r"contrate|he contratado|active|he activado|configure|he configurado|inscribi|"
    r"he inscrito|registre|he registrado|agregue|he agregado|anadi|he anadido|di de alta|"
    # RF1S: consenting to a recurring item is setting it up.
    r"acepte|he aceptado)"
)
_PT_SETUP_VERBS = (
    r"(?:iniciei|programei|agendei|assinei|contratei|ativei|configurei|cadastrei|registrei|"
    r"adicionei|inscrevi|aceitei)"
)
_ES_DEMONSTRATIVE_OBJECT = (
    r"(?:(?:a|en|de|para)\s+)?(?:ese|esa|eso|esto|este|esta|esos|esas|estos|estas|"
    r"aquel|aquella|aquello)"
)
_PT_DEMONSTRATIVE_OBJECT = (
    r"(?:(?:(?:a|em|de|para)\s+)?(?:essa|esse|esta|este|essas|esses|isso|isto|aquilo|"
    r"aquele|aquela)|nisso|nisto|nesse|nessa|neste|nesta|disso|desse|dessa|deste|desta|"
    r"naquilo|daquilo)"
)
# Back-referring set-up denials: a demonstrative object, or an object clitic with
# an explicit first-person subject (PT: a null object closing the sentence).
_ES_SETUP_BACKREF = (
    r"\b" + _ES_NEG + r"\s+" + _ES_CLITICS + _ES_SETUP_VERBS + r"\s+"
    + _ES_DEMONSTRATIVE_OBJECT + r"\b"
    + r"|\byo\s+" + _ES_NEG + r"\s+(?:(?:me|le|les|se)\s+)?(?:lo|la|los|las)\s+"
    + _ES_SETUP_VERBS + r"\b"
    + r"|\b" + _ES_NEG + r"\s+(?:(?:me|le|les|se)\s+)?(?:lo|la|los|las)\s+"
    + _ES_SETUP_VERBS + r"\s+yo\b"
)
_PT_SETUP_BACKREF = (
    r"\b" + _PT_NEG + r"\s+" + _PT_CLITICS + _PT_SETUP_VERBS + r"\s+"
    + _PT_DEMONSTRATIVE_OBJECT + r"\b"
    + r"|\beu\s+" + _PT_NEG + r"\s+(?:(?:o|a|os|as)\s+)?" + _PT_SETUP_VERBS + _SENTENCE_END
)
_SETUP_BACKREF = _rx(_ES_SETUP_BACKREF + r"|" + _PT_SETUP_BACKREF)
_RELATIVIZER = r"(?:que|el cual|la cual|los cuales|las cuales|o qual|a qual)"
_RELATIVIZER_START = _rx(r"^" + _RELATIVIZER + r"\b")
# A relative-clause set-up denial needs a nominal head just before it; otherwise
# "que" is a complementizer ("le confirmo que no programé nada").
_RELATIVE_HEAD = _rx(
    r"\b(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|"
    r"operacion|operaciones|transaccion|transacciones|transferencia|transferencias|"
    r"debito|debitos|retiro|retiros|giro|giros|consumo|consumos|cobranca|cobrancas|"
    r"pagamento|pagamentos|lancamento|lancamentos|operacao|operacoes|transacao|transacoes|"
    r"pix|saque|saques|gasto|gastos|boleto|boletos|destinatario|destinatarios|"
    r"beneficiario|beneficiarios|favorecido|favorecidos|contacto|contactos|contato|"
    r"contatos|suscripcion|suscripciones|assinatura|assinaturas|domiciliacion|"
    r"recorrencia)\b(?:\s+[^\s,]+){0,4}\s+$"
)
# RF1S: an item the customer observes ("veo un cobro mensual de una app de música
# que nunca agregué") can head a relative clause across a longer modifier chain,
# because the observation frame fixes the referent.
_OBSERVED_RELATIVE_HEAD = _rx(
    r"\b(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|"
    r"operacion|operaciones|transaccion|transacciones|transferencia|transferencias|"
    r"debito|debitos|retiro|retiros|giro|giros|consumo|consumos|avance|avances|cobranca|"
    r"cobrancas|pagamento|pagamentos|lancamento|lancamentos|operacao|operacoes|transacao|"
    r"transacoes|pix|saque|saques|gasto|gastos|boleto|boletos|suscripcion|suscripciones|"
    r"assinatura|assinaturas|domiciliacion|recorrencia)\b(?:\s+[^\s,]+){0,8}\s+$"
)
# Enrolled payees and recurring set-ups are account activity for set-up denials.
_ITEM_ANCHOR = _rx(
    r"\b(?:destinatario|destinatarios|beneficiario|beneficiarios|favorecido|favorecidos|"
    r"suscripcion|suscripciones|domiciliacion|domiciliaciones|assinatura|assinaturas|"
    r"recorrencia|debito automatico|cobro recurrente|cobranca recorrente)\b"
)
# Money leaving or vanishing from an account. Used only by the RF1O families, so
# the older families keep their anchor set unchanged.
_MONEY = r"(?:plata|platica|dinero|fondos|dinheiro|grana)"
_MONEY_FLOW_ANCHOR = _rx(
    r"\b" + _MONEY + r"\s+(?:[a-z]+\s+){0,2}?(?:de|desde|da|do)\s+"
    r"(?:(?:mi|la|su|minha|sua|nuestra|nossa)\s+)?(?:cuenta|conta)\b"
    r"|\b(?:desapareciendo|desaparecio|desaparecieron|ha desaparecido|han desaparecido|"
    r"sumindo|sumiu|sumiram|desapareceu|desapareceram)\s+(?:[a-z]+\s+){0,3}?" + _MONEY + r"\b"
    r"|\b" + _MONEY + r"\s+(?:[a-z]+\s+){0,3}?(?:desaparecio|ha desaparecido|ya no estaba|"
    r"tinha sumido|sumiu|desapareceu|nao estava mais)\b"
)
# RF1S: an amount taken from or vanished out of an account is a money flow too
# ("de su cuenta salieron 900 mil", "sumiram 300 reais").
_AMOUNT = (
    r"(?:\$\s*)?(?:\d+(?:[.,]\d+)*\s*(?:mil|millones|millon|pesos|reais|dolares|euros)|"
    r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d{3,})"
    r"|(?:un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|cien|quinientos|um|dois|"
    r"quatro|cem|quinhentos)\s+(?:mil|millones|millon|pesos|reais)"
)
_AMOUNT_FLOW_ANCHOR = _rx(
    r"\b(?:desaparecieron|desaparecio|han desaparecido|ha desaparecido|salieron|salio|"
    r"sairam|saiu|sacaron|saco|"
    r"retiraron|retiro|transfirieron|transfirio|robaron|robo|quitaron|descontaron|"
    r"sumiram|sumiu|desapareceram|desapareceu|tiraram|tirou|sacaram|sacou|transferiram|"
    r"transferiu|roubaram|roubou|levaram|levou)\s+(?:\S+\s+){0,2}?(?:" + _AMOUNT + r")(?!\w)"
)
# Third-party reports: a relative's denial, relayed by the customer. The ticket
# stays bound to the reporting session; no third-party account is looked up.
_KIN = (
    r"(?:papa|mama|padre|madre|abuelo|abuela|abuelito|abuelita|hijo|hija|esposo|esposa|"
    r"marido|mujer|hermano|hermana|tio|tia|suegro|suegra|pai|mae|avo|filho|filha|"
    r"mulher|irmao|irma|sogro|sogra|"
    # RF1Q: partners and the wider household relay reports too.
    r"pareja|novio|novia|companero|companera|nieto|nieta|padres|papas|hijos|"
    r"companheiro|companheira|namorado|namorada|neto|neta|filhos)"
)
_KIN_POSSESSED = _rx(r"\b(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\b")
# RF1S: a relay may also come from someone acting for the account holder: a
# caregiver, legal representative, or anyone writing on a named person's behalf.
_REPRESENTED_PRINCIPAL = _rx(
    r"\b(?:soy|somos|sou|somos)\s+(?:(?:el|la|los|las|o|a|os|as|su|sua)\s+)?"
    r"(?:cuidador|cuidadora|cuidadores|apoderado|apoderada|tutor|tutora|representante|"
    r"curador|curadora|acudiente|enfermero|enfermera|procurador|procuradora|responsavel)"
    r"(?:\s+legal)?\s+(?:de|del|da|do|das|dos)\b"
    r"|\b(?:de parte de|en nombre de|em nome de|da parte de|a pedido de|a pedido do|"
    r"a pedido da)\s+(?:mi|mis|meu|minha|meus|minhas|don|dona|senor|senora|seu|sr|sra)\b"
)
_ES_THIRD_VERBS = (
    r"(?:hizo|ha hecho|realizo|efectuo|saco|ha sacado|retiro|ha retirado|autorizo|"
    r"ha autorizado|aprobo|compro|envio|mando|transfirio|pidio|solicito|inicio|programo|"
    r"reconoce|reconocio|ha reconocido)"
)
_PT_THIRD_VERBS = (
    r"(?:fez|realizou|efetuou|sacou|retirou|autorizou|aprovou|comprou|enviou|mandou|"
    r"transferiu|pediu|solicitou|iniciou|programou|reconhece|reconheceu)"
)
_ELLIPTICAL_AGENCY = _rx(r"\b(?:fue|ha sido|foi)\b")
_KIN_PERFORMED = _rx(
    r"(?<!no )(?<!nao )\b(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\s+(?:me\s+)?"
    r"(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:hizo|realizo|compro|pago|saco|retiro|transfirio|"
    r"uso|fez|realizou|comprou|pagou|sacou|transferiu|usou)\b"
    r"|\b(?:lo|la|los|las|o|a|os|as)\s+(?:hizo|realizo|compro|pago|saco|fez|realizou|comprou|"
    r"pagou|sacou)\s+(?:mi|meu|minha)\s+" + _KIN + r"\b"
)
_LATER_ATTRIBUTION = _rx(r"(?<!no )(?<!nao )\b(?:fue el|fue ella|foi ele|foi ela)\b")
# Intrusion into the customer's own account or app by an unnamed party. Plural
# forms are impersonal ("entraron a mi cuenta"); singular forms need an explicit
# unnamed subject, so "mi esposa entró a mi cuenta" is not a report.
_ES_INTRUSION_OBJECT = (
    r"(?:(?:a|en|de|con)\s+)?(?:mi|mis)\s+(?:cuenta|cuentas|app|aplicacion|banca|perfil|"
    r"usuario|sesion|clave)\b"
)
_PT_INTRUSION_OBJECT = (
    r"(?:(?:na|no|nas|nos|em|a|o|da|do)\s+)?(?:minha|meu|minhas|meus)\s+(?:conta|contas|"
    r"app|aplicativo|perfil|usuario|senha|cadastro|internet banking)\b"
)
_ES_INTRUSION_PLURAL = (
    r"(?:entraron|han entrado|accedieron|han accedido|se metieron|se han metido|"
    r"invadieron|han invadido|hackearon|han hackeado|jaquearon|vulneraron|han vulnerado|"
    r"se apoderaron|tomaron (?:el )?control)"
)
_ES_INTRUSION_SINGULAR = (
    r"(?:entro|ha entrado|accedio|ha accedido|se metio|se ha metido|invadio|ha invadido|"
    r"hackeo|ha hackeado|vulnero|se apodero|tomo (?:el )?control)"
)
_PT_INTRUSION_PLURAL = (
    r"(?:entraram|acessaram|invadiram|hackearam|raquearam|se meteram|meteram-se|mexeram|"
    r"tomaram (?:o )?controle)"
)
_PT_INTRUSION_SINGULAR = (
    r"(?:entrou|acessou|invadiu|hackeou|raqueou|se meteu|meteu-se|mexeu|tomou (?:o )?controle)"
)
_INTRUSION_SINGULAR_CUE = _rx(
    r"^(?:" + _ES_INTRUSION_SINGULAR + r"|" + _PT_INTRUSION_SINGULAR + r")\b"
)
_UNNAMED_SUBJECT = (
    r"(?:alguien|alguem|desconocidos|desconhecidos|hackers|ladrones|ladroes|terceros|"
    r"terceiros|estafadores|golpistas|delincuentes|bandidos|criminales|criminosos)"
    r"(?:\s+(?:mas|mais))?"
)
# What may stand before an impersonal plural intrusion verb in its clause: nothing,
# a belief/perception complementizer ("creo que"), a time adverb, or an unnamed
# subject. A coordinator or a bare relative "que" could carry a named subject.
_INTRUSION_PLURAL_SLOT = _rx(
    r"(?:^|\b(?:creo|pienso|sospecho|temo|parece|me parece|se|me di cuenta|descubri|note|"
    r"estoy seguro|estoy segura|acho|penso|suspeito|desconfio|sei|percebi|descobri|notei|"
    r"tenho certeza)\s+que|\b(?:anoche|ayer|hoy|ontem|hoje|ya|ja|recien|de nuevo|otra vez|"
    r"de novo|outra vez|esta manana|hoje cedo|de madrugada)|\b" + _UNNAMED_SUBJECT + r")"
    r"\s*(?:me\s+)?$"
)
_INTRUSION_SINGULAR_SLOT = _rx(r"\b" + _UNNAMED_SUBJECT + r"\s*(?:me\s+)?$")
# Belief verbs report a suspected intrusion; the structural grammar asserts the
# same compromise reports ("acho que invadiram minha conta"), so only genuine
# uncertainty hedges block an intrusion report.
_INTRUSION_HEDGE_TAIL = _rx(
    r"\b(?:quizas|quiza|tal vez|talvez|puede que|pode ser que|no se si|nao sei se)\s+"
    r"(?:que\s+)?$"
)
# Presence denial: observed account activity located where the customer has
# never been ("... retiros en una ciudad donde nunca he estado").
_ES_PRESENCE_VERBS = (
    r"(?:he estado|estuve|habia estado|he ido|fui|habia ido|he viajado|viaje|he pisado|"
    r"pise|he visitado|visite)"
)
_PT_PRESENCE_VERBS = r"(?:estive|tinha estado|fui|tinha ido|viajei|pisei|visitei)"
_OBSERVED_ACTIVITY = _rx(
    r"\b(?:vi|veo|aparece|aparecen|aparecio|aparecieron|hay|habia|hubo|tengo|tenia|"
    r"sale|salen|salio|salieron|figura|figuran|registra|registran|cobraron|hicieron|"
    r"llego|llegaron|vejo|apareceu|apareceram|aparecem|tem|tinha|houve|consta|constam|"
    r"caiu|cairam|fizeram|chegou|chegaram|recebi)\b"
)
_PLANNED_ACTIVITY = _rx(
    r"\b(?:quiero|quisiera|voy a|vamos a|planeo|pienso|puedo|podria|necesito|debo|"
    r"quero|queria|vou|pretendo|posso|poderia|preciso|planejo|devo)\b"
)
# First-person performance of the activity, not under negation. "saque"/"retire"/
# "use" need an explicit "yo": bare "saque" is also the Portuguese noun.
_SELF_PERFORMED_ACTIVITY = _rx(
    r"(?<!no )(?<!nao )(?<!nunca )(?<!jamas )(?<!jamais )(?<!tampoco )"
    r"\b(?:hice|realice|compre|pague|fiz|realizei|comprei|saquei|retirei|paguei|usei|"
    r"yo (?:saque|retire|use))\b"
)
_KNOWN_PERSON_ATTRIBUTION = _rx(
    r"\b(?:era|fue|foi|eran|eram)\s+(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\b"
)
# "no es de mi cuenta, es de la de mi esposa" re-attributes the item to a named
# owner; that is a correction, not a non-ownership report.
_CORRECTIVE_REATTRIBUTION = _rx(
    r"^\s*,?\s*(?:sino|si no|es de|era de|e de|e da|e do|era da|era do|mas sim|e sim)\b"
)
# Household and relayed denials must point at an existing item: a relative clause
# on it, an object clitic, a demonstrative object, a definite debit event, or a
# verb closing its clause. "nadie hizo compras" / "mi esposo no hizo el pago"
# describe activity that did not happen, not activity being disowned.
_REFERENCE_BEFORE = _rx(r"\bque\s+$")  # only with a nominal head (see _RELATIVE_HEAD)
_REFERENCE_CLITIC = _rx(r"\s(?:lo|la|los|las|o|a|os|as)\s+\S+$")
_REFERENCE_AFTER = _rx(
    r"\s*(?:[,;]|$)|\s+(?:tampoco|tampouco|y|e|pero|mas|nem|ni)\b"
    r"|\s+(?:ese|esa|esos|esas|este|esta|estos|estas|eso|esto|esse|essa|esses|essas|"
    r"isso|isto|aquele|aquela)\b"
    r"|\s+(?:el|la|los|las|o|a|os|as)\s+(?:cargo|cargos|cobro|cobros|compra|compras|"
    r"retiro|retiros|consumo|consumos|debito|debitos|saque|saques|gasto|gastos|cobranca|"
    r"cobrancas|lancamento|lancamentos|movimiento|movimientos|movimentacao|transaccion|"
    r"transacciones|transacao|transacoes|operacion|operaciones|operacao|operacoes)\b"
)
# Not recognizing or not authorizing presupposes that the activity exists.
_PRESUPPOSING_VERB = _rx(
    r"\b(?:reconoce|reconocio|ha reconocido|reconocemos|reconocimos|reconhece|reconheceu|"
    r"reconhecemos|autorizo|ha autorizado|aprobo|autorizou|aprovou|autorizamos)\b"
)
_PROVENANCE_CUE = _rx(r"^(?:no|nao)\s+\S+\s+d(?:e|a|o|as|os)\s")
# "entraron a mi cuenta de Netflix" is not the customer's bank account.
_NON_BANK_ACCOUNT_AFTER = _rx(
    r"^\s+(?:de|del|do|da)\s+(?!(?:ahorro|ahorros|banco|cheques|corriente|nomina|"
    r"poupanca|salario|pix|la|el|mi)\b)[a-z]+"
)

# ---------------------------------------------------------------- RF1Q families
# Banking products that can be opened, requested, or held in the customer's name.
_PRODUCT_HEAD = (
    r"(?:tarjeta|tarjetas|cuenta|cuentas|credito|creditos|prestamo|prestamos|chequera|"
    r"cartao|cartoes|conta|contas|emprestimo|emprestimos|financiamento|cheque especial|"
    # RF1S: deposits, insurance, and credit lines held in the customer's name.
    # "seguro" is the product only when not the adjective ("estoy seguro", "seguro que").
    r"cdt|cdts|cdb|cdbs|libranza|microcredito|microcreditos|sobregiro|sobregiros|"
    r"poliza|polizas|apolice|apolices|(?<!estoy )(?<!estaba )(?<!estamos )(?<!muy )"
    r"seguro(?!\s+(?:de\s+)?que\b)|seguros|consorcio|"
    r"inversion|inversiones|investimento|investimentos)"
)
_PRODUCT_ANCHOR = _rx(r"\b" + _PRODUCT_HEAD + r"\b")
# Identity misuse: a product opened in the customer's name. The opener must be an
# unnamed party ("alguien abrió una tarjeta a mi nombre"); an impersonal plural
# alone is also how a branch describes a legitimate opening ("me abrieron una
# cuenta a mi nombre"), so it counts only with an explicit lack of authorization.
_ES_OPEN_SINGULAR = (
    r"(?:abrio|ha abierto|saco|ha sacado|solicito|ha solicitado|pidio|ha pedido|tramito|"
    r"ha tramitado|contrato|ha contratado|emitio|ha emitido|creo|ha creado|dio de alta)"
)
_ES_OPEN_PLURAL = (
    r"(?:abrieron|han abierto|sacaron|han sacado|solicitaron|han solicitado|pidieron|"
    r"han pedido|tramitaron|han tramitado|contrataron|han contratado|emitieron|han emitido|"
    r"crearon|han creado|dieron de alta)"
)
_ES_OPEN_IMPERSONAL = (
    r"(?:se (?:abrio|abrieron|ha abierto|han abierto|emitio|emitieron|solicito|solicitaron|"
    r"creo|crearon|contrato|contrataron|tramito|tramitaron)|(?:fue|fueron|ha sido|han sido)\s+"
    r"(?:abiert|emitid|solicitad|cread|contratad|tramitad)[oa]s?)"
)
_PT_OPEN_SINGULAR = (
    r"(?:abriu|fez|tirou|solicitou|pediu|contratou|emitiu|criou|cadastrou)"
)
_PT_OPEN_PLURAL = (
    r"(?:abriram|fizeram|tiraram|solicitaram|pediram|contrataram|emitiram|criaram|cadastraram)"
)
_PT_OPEN_IMPERSONAL = (
    r"(?:(?:foi|foram)\s+(?:abert|feit|emitid|solicitad|criad|contratad|cadastrad)[oa]s?)"
)
_IN_MY_NAME = (
    r"(?:(?:a|en)\s+mi\s+nombre|a\s+nombre\s+mio|con\s+mis\s+datos|usando\s+mis\s+datos|"
    r"(?:no|em)\s+(?:meu\s+)?nome(?:\s+meu)?|com\s+(?:os\s+)?meus\s+dados|"
    r"usando\s+(?:os\s+)?meus\s+dados|com\s+(?:o\s+)?meu\s+cpf)"
)
_WITHOUT_MY_AUTHORIZATION = (
    r"(?:sin\s+(?:mi\s+)?(?:autorizacion|permiso|consentimiento|conocimiento)|"
    r"sin\s+que\s+yo\s+(?:lo\s+|la\s+)?(?:supiera|pidiera|autorizara|solicitara)|"
    r"sem\s+(?:a\s+)?(?:minha\s+)?(?:autorizacao|permissao|consentimento|conhecimento)|"
    r"sem\s+(?:que\s+)?eu\s+(?:saber|soubesse|pedir|pedisse|autorizar|autorizasse))"
)
_OPEN_ANY = (
    r"(?:" + _ES_OPEN_SINGULAR + r"|" + _ES_OPEN_PLURAL + r"|" + _ES_OPEN_IMPERSONAL + r"|"
    + _PT_OPEN_SINGULAR + r"|" + _PT_OPEN_PLURAL + r"|" + _PT_OPEN_IMPERSONAL + r")"
)
_PRODUCT_IN_MY_NAME = (
    r"(?:(?:\S+\s+){0,3}?" + _PRODUCT_HEAD + r"\b(?:\s+[^\s,]+){0,3}?\s+" + _IN_MY_NAME
    + r"|" + _IN_MY_NAME + r"\s+(?:\S+\s+){0,3}?" + _PRODUCT_HEAD + r")\b"
)
# Denial of having opened or requested an existing product ("una tarjeta que yo
# nunca solicité", "yo no la pedí", "nunca abrí esa cuenta", PT "..., nunca abri").
# Activation is not origination: "no la activé" describes a card not yet in use.
_ES_PRODUCT_ORIGIN_VERBS = (
    r"(?:abri|he abierto|solicite|he solicitado|pedi|he pedido|tramite|he tramitado|"
    r"contrate|he contratado|firme|he firmado|saque|he sacado|"
    # RF1S: accepting a product (an insurance policy, an offer) is origination too.
    r"acepte|he aceptado)"
)
_PT_PRODUCT_ORIGIN_VERBS = r"(?:abri|solicitei|pedi|contratei|assinei|tirei|aceitei)"
_PRODUCT_RELATIVE_HEAD = _rx(r"\b" + _PRODUCT_HEAD + r"\b(?:\s+[^\s,]+){0,4}\s+$")
_OBSERVED_PRODUCT_HEAD = _rx(r"\b" + _PRODUCT_HEAD + r"\b(?:\s+[^\s,]+){0,8}\s+$")
# RF1S: the customer's financial records. Whatever they show was opened, contracted,
# or charged in the customer's name, so a relative-clause origination denial over
# an item located there names an existing product even without a product noun.
_RECORD_LOCATION = _rx(
    r"\b(?:en|de|del|no|na|do|da)\s+(?:(?:el|la|los|las|mi|mis|o|a|meu|minha|meus|minhas)\s+)?"
    r"(?:extracto|extractos|estado de cuenta|estados de cuenta|cartola|historial|"
    r"historial crediticio|central de riesgo|centrales de riesgo|reporte de credito|"
    r"extrato|extratos|fatura|historico|cadastro positivo)\b"
    r"|\b(?:el|mi|del)\s+resumen\b"
)
# A displayed product whose ownership is denied must be presented as existing in
# the customer's records: a relative or locative tying it to what the customer
# sees. A bare "esse cartão não é meu" is about a physical card, not a report.
_ES_PRODUCT_EXISTS = (
    r"(?:que\s+(?:me\s+)?(?:aparece|aparecen|aparecio|sale|salen|figura|figuran|consta|"
    r"esta|estan|veo|tengo|hay)|(?:en|de)\s+mi\s+(?:perfil|app|aplicacion|banca|estado de cuenta|"
    r"resumen|extracto|cuenta))"
)
_PT_PRODUCT_EXISTS = (
    r"(?:que\s+(?:me\s+)?(?:aparece|aparecem|apareceu|consta|constam|esta|estao|vejo|tenho|ha)|"
    r"(?:no|na|em|do|da)\s+(?:meu|minha)\s+(?:cadastro|perfil|app|aplicativo|extrato|conta|"
    r"internet banking))"
)
# "no la pedí yo, la pidió mi esposa" attributes the origination to a named
# relative; without a lack-of-authorization marker that is not a report.
_KIN_ORIGINATION = _rx(
    r"\b(?:(?:la|lo|las|los|o|a|os|as)\s+)?(?:pidio|solicito|abrio|tramito|contrato|saco|"
    r"pediu|solicitou|abriu|contratou|tirou)\s+(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\b"
    r"|\b(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\s+(?:me\s+)?(?:(?:la|lo|las|los|o|a|os|as)\s+)?"
    r"(?:pidio|solicito|abrio|tramito|contrato|saco|pediu|solicitou|abriu|contratou|tirou)\b"
)
_WITHOUT_AUTHORIZATION = _rx(_WITHOUT_MY_AUTHORIZATION)
# "esa tarjeta no es mía, es la de mi esposo" re-attributes the product to a named
# owner; that is a correction, not a non-ownership report.
_PRODUCT_REATTRIBUTION = _rx(
    r"^\s*,?\s*(?:sino|si no|es de|es la de|es el de|son de|era de|pertenece a|e de|e da|e do|"
    r"e a de|e o de|era da|era do|pertence a|mas sim)\b"
)

# ---------------------------------------------------------------- RF1S families
# Unnamed-actor activity: an unnamed party performed account activity ("un tercero
# retiró dinero de mi cuenta"). The actor must be unnamed; a named person acting
# is a household or permission matter handled elsewhere.
_UNNAMED_ACTOR = (
    r"(?:" + _UNNAMED_SUBJECT + r"|una persona|otra persona|un tercero|una tercera persona|"
    r"un desconocido|una desconocida|uma pessoa|outra pessoa|um terceiro|um desconhecido|"
    r"uma desconhecida)"
)
_ES_ACTOR_VERBS = (
    r"(?:hizo|ha hecho|realizo|ha realizado|efectuo|ha efectuado|saco|ha sacado|retiro|"
    r"ha retirado|transfirio|ha transferido|compro|ha comprado|pago|ha pagado|gasto|"
    r"ha gastado|uso|ha usado|utilizo|ha utilizado|cobro|movio|ha movido|vacio|ha vaciado|"
    r"envio|ha enviado|mando|ha mandado|hicieron|han hecho|realizaron|han realizado|"
    r"efectuaron|sacaron|han sacado|retiraron|han retirado|transfirieron|han transferido|"
    r"compraron|han comprado|pagaron|han pagado|gastaron|han gastado|usaron|han usado|"
    r"utilizaron|movieron|vaciaron|enviaron|mandaron|"
    r"(?:esta|estan|ha estado|han estado)\s+(?:usando|utilizando|haciendo|sacando|retirando|"
    r"comprando|gastando|pagando|transfiriendo)|"
    r"(?:volvio|volvieron|ha vuelto|han vuelto)\s+a\s+(?:usar|utilizar|hacer|sacar|retirar|"
    r"comprar|gastar|pagar|transferir|cobrar))"
)
_PT_ACTOR_VERBS = (
    r"(?:fez|realizou|efetuou|sacou|retirou|transferiu|comprou|pagou|gastou|usou|utilizou|"
    r"movimentou|enviou|mandou|fizeram|realizaram|efetuaram|sacaram|retiraram|transferiram|"
    r"compraram|pagaram|gastaram|usaram|utilizaram|movimentaram|enviaram|mandaram|"
    r"(?:esta|estao|tem)\s+(?:usado|usando|utilizando|fazendo|sacando|comprando|gastando)|"
    r"(?:voltou|voltaram)\s+a\s+(?:usar|utilizar|fazer|sacar|retirar|comprar|gastar|pagar|"
    r"transferir|cobrar))"
)
# Someone sending money to the customer is incoming, not unauthorized activity:
# a dative "me" with a send/pay verb, or the customer's account as destination.
_INCOMING_DATIVE = _rx(
    r"^(?:me|lhe)\s+(?:transfirio|transfirieron|envio|enviaron|mando|mandaron|pago|pagaron|"
    r"deposito|depositaron|consigno|consignaron|giro|giraron|transferiu|transferiram|enviou|"
    r"enviaram|mandou|mandaram|pagou|pagaram|depositou|depositaram)\b"
    r"|^(?:me|lhe)\s+(?:hizo|ha hecho|hicieron|fez|fizeram)\s+(?:(?:un|una|um|uma)\s+)?"
    r"(?:transferencia|deposito|consignacion|giro|pago|abono|pix|pagamento)\b"
)
_TO_MY_ACCOUNT = _rx(
    r"\b(?:a|hacia|para|en)\s+mi\s+(?:cuenta|tarjeta)\b|\b(?:na|para a|pra)\s+minha\s+conta\b"
)
_FROM_MY_ACCOUNT = _rx(
    r"\b(?:de|desde|con|del)\s+(?:mi|mis)\s+(?:cuenta|cuentas|tarjeta|tarjetas|datos|clave|app)\b"
    r"|\b(?:da|de|com|do|dos|das)\s+(?:minha|meu|minhas|meus)\s+(?:conta|contas|cartao|"
    r"cartoes|dados|senha)\b"
)
# The activity must be tied to the customer's account: the account, card, or data
# as source, instrument, or location, or an observation of the customer's own
# records ("me di cuenta de que alguien ..."). A bare "alguien hizo una compra" stays
# outside, as the structural grammar decides for performance without an instrument.
_ACCOUNT_TIE = _rx(
    r"\b(?:de|desde|con|del|en)\s+(?:mi|mis)\s+(?:cuenta|cuentas|tarjeta|tarjetas|datos|clave|"
    r"app|aplicacion|banca)\b"
    r"|\b(?:da|de|com|do|dos|das|na|no|em)\s+(?:minha|meu|minhas|meus)\s+(?:conta|contas|"
    r"cartao|cartoes|dados|senha|app|aplicativo)\b"
    r"|\b(?:usando|usaron|uso|usar|utilizaron|utilizando|utilizo|utilizar|usou|usaram|utilizou|"
    r"utilizaram)\s+(?:mi|mis|minha|minhas|meu|meus)\s+(?:tarjeta|tarjetas|cuenta|cartao|cartoes|"
    r"conta|datos|dados)\b"
)
_OBSERVATION_FRAME = _rx(
    r"\b(?:vi|veo|vimos|vemos|note|notamos|me di cuenta(?: de)?|nos dimos cuenta(?: de)?|"
    r"descubri|descubrimos|me entere(?: de)?|aparece|aparecio|sale|salio|vejo|percebi|"
    r"notei|descobri|reparei|apareceu)\s+que\b"
)
# What was observed must be the customer's own records or a bank notice, not a
# stranger seen at a cash machine.
_RECORDS_CONTEXT = _rx(
    r"\b(?:app|aplicacion|aplicativo|banca|extracto|extrato|movimientos|movimentacoes|"
    r"historial|historico|estado de cuenta|resumen|fatura|notificacion|notificacao|alerta|"
    r"mi cuenta|minha conta)\b"
)
# The customer asked the actor to do it ("hizo el pago por mí, como le encargué").
_DELEGATED_FOR_ME = _rx(
    r"(?<!pasar )(?<!passar )\bpor\s+(?:mi|mim)\b(?!\s+(?:cuenta|conta|tarjeta|cartao))"
)
_DELEGATED_REQUEST = _rx(
    r"\b(?:como|que)\s+(?:yo\s+|eu\s+)?(?:le|les|lhe|lhes)\s+(?:pedi|encargue|solicite)\b"
    r"|\b(?:a mi pedido|a pedido mio|a pedido meu|por encargo mio)\b"
)
# Impersonation / identity theft: an unnamed party posing as the customer. The
# customer is the referent, so the cue anchors itself, but only in a banking
# context (an account, product, credential, or the bank itself is mentioned).
_ES_IMPERSONATION = (
    r"(?:se\s+(?:esta|estan|ha|han|hizo|hicieron|hace|hacen)\s+(?:estado\s+)?"
    r"(?:haciendo\s+|hecho\s+)?|(?:esta|estan)\s+haciendose\s+)pasar\s+por\s+mi\b"
    r"|\bme\s+(?:suplantaron|han suplantado|estan suplantando|suplanto|ha suplantado|"
    r"esta suplantando)\b"
    r"|\b(?:suplantaron|robaron|usurparon|han suplantado|han robado|han usurpado|"
    r"estan suplantando)\s+(?:mi|la)\s+identidad\b"
    r"|\bme\s+(?:robaron|han robado)\s+(?:la|mi)\s+identidad\b"
    r"|\b(?:usaron|han usado|estan usando|utilizaron|han utilizado)\s+"
    r"(?:mi|mis)\s+(?:cedula|identidad|datos|documento|documentos)\b"
)
_PT_IMPERSONATION = (
    r"(?:se\s+passou|se\s+passaram|(?:esta|estao)\s+se\s+passando|(?:esta|estao)\s+"
    r"passando-se)\s+por\s+mim\b"
    r"|\b(?:roubaram|usurparam|clonaram)\s+(?:a\s+)?minha\s+identidade\b"
    r"|\b(?:usaram|estao usando|utilizaram)\s+(?:o\s+|os\s+|a\s+)?(?:meu|meus|minha)\s+"
    r"(?:cpf|identidade|dados|documento|documentos|rg)\b"
)
_BANK_CONTEXT = _rx(
    r"\b(?:banco|cuenta|cuentas|tarjeta|tarjetas|perfil|clave|contrasena|app|aplicacion|"
    r"credito|creditos|prestamo|prestamos|oficina|sucursal|linea|plata|dinero|conta|contas|"
    r"cartao|cartoes|senha|aplicativo|emprestimo|agencia|dinheiro|pix)\b"
)
_NON_BANK_PLATFORM = _rx(
    r"\b(?:en|no|na|por)\s+(?:instagram|facebook|whatsapp|tiktok|twitter|redes sociales|"
    r"redes sociais|linkedin|telegram)\b"
)
# Credential takeover: the customer's access credentials or contact data were
# changed, and the change is disowned. The change itself is the cue; the
# customer's own credential is the anchor.
_CREDENTIAL = (
    r"(?:(?:la|el|las|los|mi|mis|o|a|os|as|meu|minha|meus|minhas)\s+)"
    r"(?:contrasena|contrasenas|clave|claves|clave de acceso|clave dinamica|pin|"
    r"correo(?: electronico)?|email|e-mail|celular|numero de celular|numero de telefono|"
    r"telefono|usuario|token|datos de contacto|senha|senhas|telefone|numero de telefone|"
    r"dados cadastrais)\b"
)
_ES_CHANGE_SINGULAR = (
    r"(?:cambio|ha cambiado|modifico|ha modificado|actualizo|ha actualizado|restablecio|"
    r"reseteo|altero|ha alterado)"
)
_ES_CHANGE_PLURAL = (
    r"(?:cambiaron|han cambiado|modificaron|han modificado|actualizaron|han actualizado|"
    r"restablecieron|resetearon|alteraron|han alterado)"
)
_PT_CHANGE_SINGULAR = r"(?:mudou|alterou|trocou|redefiniu|modificou)"
_PT_CHANGE_PLURAL = r"(?:mudaram|alteraram|trocaram|redefiniram|modificaram)"
_CREDENTIAL_CHANGE = (
    r"\b" + _UNNAMED_ACTOR + r"\s+(?:me\s+|le\s+)?(?:" + _ES_CHANGE_SINGULAR + r"|"
    + _ES_CHANGE_PLURAL + r"|" + _PT_CHANGE_SINGULAR + r"|" + _PT_CHANGE_PLURAL + r")\s+"
    r"(?:\S+\s+){0,2}?" + _CREDENTIAL
    + r"|(?<!\byo )(?<!\beu )\b(?:me\s+|le\s+)?(?:" + _ES_CHANGE_PLURAL + r"|" + _PT_CHANGE_PLURAL
    + r"|se\s+(?:cambio|modifico|actualizo|restablecio))\s+(?:\S+\s+){0,2}?" + _CREDENTIAL
    + r"|\b" + _CREDENTIAL + r"(?:\s+\S+){0,4}?\s+(?:fue|ha sido|foi)\s+"
    r"(?:cambiad|modificad|actualizad|restablecid|alterad|trocad|mudad|redefinid)[oa]\b"
)
_UNNAMED_CHANGE = _rx(r"^" + _UNNAMED_ACTOR + r"\b")
# Disowning the change: a first-person denial of making it, an agency denial, or
# an explicit lack of authorization anywhere in the message.
_CHANGE_DISOWNED = _rx(
    r"\b(?:yo|eu)\s+(?:no|nunca|jamas|nao|jamais)\s+(?:(?:la|lo|las|los|a|o|as|os|me|le)\s+)?"
    r"(?:cambie|he cambiado|modifique|actualice|restableci|pedi|solicite|hice|mudei|troquei|"
    r"alterei|redefini|solicitei|fiz)\b"
    r"|\b(?:no|nunca|nao)\s+(?:(?:la|lo|a|o)\s+)?(?:cambie|modifique|mudei|troquei|alterei)\s+"
    r"(?:yo|eu)\b"
    r"|\b(?:no|nunca|nao)\s+(?:hice|he hecho|solicite|pedi|autorice|fiz|solicitei|pedi|"
    r"autorizei)\s+(?:ese|esa|esos|esas|ningun|ninguna|esse|essa|nenhum|nenhuma)\s+"
    r"(?:cambio|cambios|mudanca|alteracao)\b"
    r"|\b(?:no fui yo|yo no fui|nao fui eu|eu nao fui)\b"
    r"|" + _WITHOUT_MY_AUTHORIZATION
)
# The customer asked for the change ("me restablecieron el PIN como solicité").
_CUSTOMER_REQUESTED = _rx(
    r"\b(?:como|que)\s+(?:yo\s+|eu\s+)?(?:lo\s+|la\s+|o\s+|a\s+)?(?:pedi|solicite|habia pedido|"
    r"habia solicitado|solicitei|tinha pedido)\b|\b(?:a peticion mia|a mi pedido|a pedido meu)\b"
)

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
    # RF1O: account provenance denial ("no es de mi cuenta"). The account noun must
    # close its clause, so "no es de mi cuenta corriente sino ..." is not a match.
    (
        "ownership_denial",
        _rx(
            r"\bno\s+(?:es|son|era|eran|fue|fueron)\s+de\s+(?:mi|mis)\s+"
            r"(?:cuenta|cuentas|tarjeta|tarjetas)(?=\s*(?:,|$)|\s+(?:y|pero|ni)\b)"
        ),
    ),
    (
        "ownership_denial",
        _rx(
            r"\bnao\s+(?:e|sao|era|eram|foi|foram)\s+d(?:a|o|as|os)\s+(?:minha|meu|minhas|meus)\s+"
            r"(?:conta|contas|cartao|cartoes)(?=\s*(?:,|$)|\s+(?:e|mas|nem)\b)"
        ),
    ),
    # RF1O: set-up / initiation / enrollment denial over an existing item.
    (
        "non_origination",
        _rx(
            r"\b" + _RELATIVIZER + r"\s+(?:yo\s+" + _ES_NEG + r"|nunca|jamas)\s+" + _ES_CLITICS
            + _ES_SETUP_VERBS + r"\b|" + _ES_SETUP_BACKREF
        ),
    ),
    (
        "non_origination",
        _rx(
            r"\b" + _RELATIVIZER + r"\s+(?:eu\s+)?" + _PT_NEG + r"\s+" + _PT_CLITICS
            + _PT_SETUP_VERBS + r"\b|" + _PT_SETUP_BACKREF
        ),
    ),
    # RF1O: observed activity located where the customer has never been.
    (
        "presence_denial",
        _rx(
            r"\b(?:donde|adonde|en (?:el|la) que|en que)\s+(?:yo\s+)?(?:nunca|jamas|no)\s+"
            + _ES_PRESENCE_VERBS + r"\b"
            + r"|\b(?:onde|aonde|em que)\s+(?:eu\s+)?(?:nunca|jamais|nao)\s+"
            + _PT_PRESENCE_VERBS + r"\b"
        ),
    ),
    # RF1O: nobody in the customer's household recognizes or made the activity.
    (
        "household_denial",
        _rx(
            r"\bnadie\s+(?:mas\s+)?(?:en|de)\s+(?:mi|la)\s+(?:casa|familia|hogar)\s+"
            r"(?:(?:lo|la|los|las|me|le)\s+)?"
            r"(?:reconoce|reconocio|hizo|ha hecho|realizo|autorizo|aprobo|uso|pidio|"
            r"solicito|compro)\b"
            r"|\bni\s+yo\s+ni\s+(?:mi|mis)\s+[a-z]+(?:\s+[a-z]+)?\s+(?:(?:lo|la|los|las)\s+)?"
            r"(?:reconocemos|reconocimos|hicimos|realizamos|autorizamos|pedimos|compramos)\b"
        ),
    ),
    (
        "household_denial",
        _rx(
            r"\bninguem\s+(?:mais\s+)?(?:aqui\s+)?(?:de|da|na|em)\s+(?:minha\s+)?(?:casa|familia)\s+"
            r"(?:(?:o|a|os|as|me)\s+)?"
            r"(?:reconhece|reconheceu|fez|realizou|autorizou|aprovou|usou|pediu|solicitou|"
            r"comprou)\b"
            r"|\bnem\s+eu\s+nem\s+(?:(?:a|o)\s+)?(?:minha|meu|minhas|meus)\s+[a-z]+(?:\s+[a-z]+)?\s+"
            r"(?:(?:o|a|os|as)\s+)?"
            r"(?:reconhecemos|fizemos|realizamos|autorizamos|pedimos|compramos)\b"
        ),
    ),
    # RF1O: an unnamed party got into the customer's own account or app.
    (
        "account_intrusion",
        _rx(
            r"\b(?:" + _ES_INTRUSION_PLURAL + r"|" + _ES_INTRUSION_SINGULAR + r")\s+"
            + _ES_INTRUSION_OBJECT
            + r"|\b(?:" + _PT_INTRUSION_PLURAL + r"|" + _PT_INTRUSION_SINGULAR + r")\s+"
            + _PT_INTRUSION_OBJECT
        ),
    ),
    # RF1O: a relative's denial relayed by the customer (third-party report).
    (
        "third_party_denial",
        _rx(
            r"\b(?:el|ella|(?:mi|mis)\s+" + _KIN + r")\s+(?:no|nunca|jamas)\s+"
            + _ES_CLITICS + _ES_THIRD_VERBS + r"\b"
            + r"|\b(?:ele|ela|(?:meu|minha|meus|minhas)\s+" + _KIN + r")\s+(?:nao|nunca|jamais)\s+"
            + r"(?:(?:o|a|os|as|lhe|me)\s+)?" + _PT_THIRD_VERBS + r"\b"
            # RF1S: the relayed elliptical agency denial ("..., y no fue ella").
            + r"|\b(?:no|nunca)\s+(?:fue|ha sido)\s+(?:el|ella)" + _CLAUSE_END
            + r"|\b(?:el|ella)\s+no\s+(?:fue|ha sido)" + _CLAUSE_END
            + r"|\b(?:nao|nunca)\s+foi\s+(?:ele|ela)" + _CLAUSE_END
            + r"|\b(?:ele|ela)\s+nao\s+foi" + _CLAUSE_END
        ),
    ),
    # RF1Q: a relative's denial relayed through their own words ("mi esposo dice
    # que no reconoce los cargos"). The cue starts at the named relative, so the
    # third-party checks (named relative, existing item, self-performed) apply.
    (
        "relayed_denial",
        _rx(
            r"\b(?:mi|mis)\s+" + _KIN + r"\s+(?:me\s+)?"
            r"(?:dice|dicen|dijo|dijeron|asegura|aseguran|aseguro|afirma|afirmo|comenta|"
            r"comento|cuenta|conto|jura|juro|insiste|insistio)\s+que\s+"
            r"(?:(?:el|ella|ellos|ellas)\s+)?(?:no|nunca|jamas)\s+" + _ES_CLITICS
            + r"(?:" + _ES_THIRD_VERBS + r"|reconocen|hicieron|realizaron|autorizaron|sacaron|"
            r"compraron|pidieron|solicitaron)\b"
            r"|\b(?:meu|minha|meus|minhas)\s+" + _KIN + r"\s+(?:me\s+)?"
            r"(?:diz|dizem|disse|disseram|afirma|afirmou|garante|garantiu|jura|jurou|conta|contou|"
            r"insiste)\s+que\s+(?:(?:ele|ela|eles|elas)\s+)?(?:nao|nunca|jamais)\s+"
            r"(?:(?:o|a|os|as|lhe|me)\s+)?"
            r"(?:" + _PT_THIRD_VERBS + r"|reconhecem|fizeram|realizaram|autorizaram|sacaram|"
            r"compraram|pediram|solicitaram)\b"
        ),
    ),
    # RF1Q: a product opened in the customer's name by an unnamed party, or by
    # anyone when the customer says it was without their authorization.
    (
        "identity_misuse",
        _rx(
            r"\b" + _UNNAMED_SUBJECT + r"\s+(?:me\s+)?(?:" + _ES_OPEN_SINGULAR + r"|"
            + _ES_OPEN_PLURAL + r"|" + _PT_OPEN_SINGULAR + r"|" + _PT_OPEN_PLURAL + r")\s+"
            + _PRODUCT_IN_MY_NAME
            + r"|\b" + _OPEN_ANY + r"\s+" + _PRODUCT_IN_MY_NAME + r"(?:\s+[^\s,]+){0,4}?,?\s+"
            + _WITHOUT_MY_AUTHORIZATION
        ),
    ),
    # RF1Q: the customer denies opening or requesting an existing product.
    (
        "product_origination_denial",
        _rx(
            r"\b" + _RELATIVIZER + r"\s+(?:yo\s+" + _ES_NEG + r"|nunca|jamas)\s+" + _ES_CLITICS
            + _ES_PRODUCT_ORIGIN_VERBS + r"\b"
            + r"|\byo\s+" + _ES_NEG + r"\s+(?:me\s+)?(?:lo|la|los|las)\s+"
            + _ES_PRODUCT_ORIGIN_VERBS + r"\b"
            + r"|\b" + _ES_NEG + r"\s+(?:me\s+)?(?:lo|la|los|las)\s+" + _ES_PRODUCT_ORIGIN_VERBS
            + r"\s+yo\b"
            + r"|\b(?:nunca|jamas)\s+(?:me\s+)?(?:lo|la|los|las)\s+" + _ES_PRODUCT_ORIGIN_VERBS + r"\b"
            + r"|\b" + _ES_NEG + r"\s+" + _ES_PRODUCT_ORIGIN_VERBS + r"\s+"
            + r"(?:ese|esa|esos|esas|este|esta|estos|estas|aquel|aquella)\s+" + _PRODUCT_HEAD + r"\b"
            + r"|\b" + _RELATIVIZER + r"\s+(?:eu\s+)?" + _PT_NEG + r"\s+(?:(?:o|a|os|as)\s+)?"
            + _PT_PRODUCT_ORIGIN_VERBS + r"\b"
            + r"|\b(?:eu\s+)?(?:nao|nunca|jamais)\s+(?:(?:o|a|os|as)\s+)?"
            + _PT_PRODUCT_ORIGIN_VERBS + _CLAUSE_END
            + r"|\b" + _PT_NEG + r"\s+" + _PT_PRODUCT_ORIGIN_VERBS + r"\s+"
            + r"(?:essa|esse|esta|este|essas|esses|aquela|aquele)\s+" + _PRODUCT_HEAD + r"\b"
        ),
    ),
    # RF1Q: a product shown in the customer's records that they say is not theirs.
    (
        "product_disownment",
        _rx(
            r"\b(?:esa|ese|esta|este|esas|esos|estas|estos|aquella|aquel|la|el|las|los|una|un)\s+"
            + _PRODUCT_HEAD + r"\b(?:\s+[^\s,]+){0,2}?\s+" + _ES_PRODUCT_EXISTS
            + r"(?:\s+[^\s,]+){0,4}?\s+(?:no|tampoco)\s+"
            + r"(?:(?:es|son|era|eran)\s+(?:mia|mio|mias|mios)|me\s+pertenecen?)\b"
            + r"|\b(?:essa|esse|esta|este|essas|esses|aquela|aquele|a|o|as|os|uma|um)\s+"
            + _PRODUCT_HEAD + r"\b(?:\s+[^\s,]+){0,2}?\s+" + _PT_PRODUCT_EXISTS
            + r"(?:\s+[^\s,]+){0,4}?\s+(?:nao|tambem nao)\s+"
            + r"(?:(?:e|sao|era|eram)\s+(?:minha|meu|minhas|meus)|me\s+pertencem?)\b"
        ),
    ),
    # RF1S: an unnamed party performed activity tied to the customer's account.
    (
        "unnamed_actor_activity",
        _rx(
            r"\b" + _UNNAMED_ACTOR + r"\s+(?:(?:me|le|lhe|nos)\s+)?(?:" + _ES_ACTOR_VERBS + r"|"
            + _PT_ACTOR_VERBS + r")\b"
        ),
    ),
    # RF1S: an unnamed party is posing as the customer or using their identity.
    ("impersonation", _rx(r"\b(?:" + _ES_IMPERSONATION + r"|" + _PT_IMPERSONATION + r")")),
    # RF1S: the customer's credentials or contact data were changed, and disowned.
    ("credential_takeover", _rx(_CREDENTIAL_CHANGE)),
)

_RF1O_FAMILIES = frozenset(
    {
        "non_origination",
        "presence_denial",
        "household_denial",
        "account_intrusion",
        "third_party_denial",
    }
)
_RF1Q_FAMILIES = frozenset(
    {
        "relayed_denial",
        "identity_misuse",
        "product_origination_denial",
        "product_disownment",
    }
)
_RF1S_FAMILIES = frozenset({"unnamed_actor_activity", "impersonation", "credential_takeover"})
# Families whose cue may borrow an anchor from the preceding sentence when the cue
# carries its own back-reference (demonstrative or clitic object) or opens a short
# coordinated clause.
_BACK_REFERENCE = _rx(
    r"\b(?:lo|la|los|las|o|a|os|as|eso|esto|ese|esa|este|esta|isso|isto|esse|essa|"
    r"nisso|nisto|nesse|nessa|disso|desse|dessa|aquello|aquilo)\b"
)

# ---------------------------------------------------------------- activity anchors
_ANCHORS: tuple[re.Pattern[str], ...] = (
    _rx(
        r"\b(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|"
        r"operacion|operaciones|transaccion|transacciones|transferencia|transferencias|"
        r"debito|debitos|retiro|retiros|consumo|consumos|giro|giros|"
        # RF1S: a cash advance is money disbursed from the customer's credit line.
        r"avance|avances)\b"
    ),
    _rx(
        r"\b(?:cobranca|cobrancas|pagamento|pagamentos|lancamento|lancamentos|operacao|"
        r"operacoes|transacao|transacoes|pix|saque|saques|gasto|gastos|ted|boleto|boletos|"
        r"movimentacao|movimentacoes)\b"
    ),
    _rx(
        r"\b(?:cobraron|cobraban|han cobrado|cargaron|han cargado|debitaron|han debitado|"
        r"sacaron|retiraron|transfirieron|cobraram|cobrou|debitaram|debitou|tiraram|"
        r"sacaram|transferiram|levaram|vaciaron|han vaciado|esvaziaram|zeraram|"
        r"descontaron|han descontado|descontaram)\b"
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
    r"imagine que|(?:se|caso) (?=eu\b|nao\b|voce\b|alguem\b|algum\b|alguma\b|a gente\b"
    # RF1O: indefinite-future frames ("se um dia aparecer ...") are hypothetical too.
    r"|um dia\b|por acaso\b|aparecer\b|aparecerem\b|houver\b|tiver\b|acontecer\b|vier\b)"
    # RF1Q: "caso" with a present subjunctive ("caso apareça ...") is hypothetical too.
    # Forms that normalize to a Spanish preterite ("noté", "encontré") are left out.
    r"|caso (?=apareca\b|aparecam\b|haja\b|tenha\b|surja\b|surjam\b|veja\b))"
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
# RF1Q: the customer says the item was already resolved, refunded, recognized,
# or is no longer suspicious, so it is not an active unauthorized-activity report.
_RESOLVED_AFTER = _rx(
    r"(?<!no )(?<!nao )(?<!nunca )\b(?:ya|ja)\s+(?:me\s+|se\s+)?(?:(?:lo|la|los|las|o|a|os|as)\s+)?"
    r"(?:devolvieron|reembolsaron|reintegraron|reversaron|revirtieron|anularon|resolvieron|"
    r"solucionaron|aclararon|resolvio|soluciono|aclaro|resolvi|solucione|aclare|"
    r"devolveram|estornaram|reembolsaram|resolveram|esclareceram|resolveu|esclareceu|"
    r"resolvi|esclareci)\b"
    r"|\b(?:ya|ja)\s+(?:esta|estan|quedo|quedaron|fue|foi|foram|ficou|ficaram)\s+"
    r"(?:resuelt|solucionad|aclarad|reembolsad|devuelt|resolvid|esclarecid|estornad|devolvid)"
    r"[oa]s?\b"
    r"|\b(?:ya|ja)\s+no\s+(?:es|son|me parece|parece|e|sao)\s+(?:sospechos|rar|extran|suspeit|"
    r"estranh)[oa]s?\b"
    r"|\bresult(?:o|ou)\s+(?:que\s+)?(?:ser|era|fue|foi)\s+(?:mio|mia|meu|minha|mi|de mi|"
    r"da minha|do meu)\b"
)
# A later recall resolves only a non-recognition told in the past or framed as
# initial ("no reconocí ... al principio, pero ya me acordé"); "no reconozco este
# cargo, pero ya me acordé de bloquear la tarjeta" stays a report, and so does a
# recall of something to do ("me acordé de llamar").
_PAST_OR_INITIAL_DENIAL = _rx(
    r"\b(?:reconoci|reconocia|reconocimos|reconocio|identifique|identificaba|reconheci|"
    r"reconhecia|reconheceu|identifiquei|identificava)\b"
    r"|\b(?:al principio|al inicio|en un principio|en un primer momento|inicialmente|"
    r"a principio|no principio|no inicio|de inicio|no comeco|num primeiro momento)\b"
)
_RECALLED_AFTER = _rx(
    r"(?<!no )(?<!nao )\b(?:ya|ja|despues|luego|depois|logo)\s+(?:me\s+|se\s+)?"
    r"(?:(?:lo|la|o|a)\s+)?"
    r"(?:acorde|acordo|recorde|recordo|lembrei|lembrou|identifique|identifiquei|"
    r"(?:reconoci|reconheci)(?!\s+que\b))\b(?!\s+(?:de|da|do)\s+(?!que\b)\S+(?:ar|er|ir)\b)"
    r"|\b(?:ya|ja|despues|luego|depois)\s+vi\s+que\s+(?:era|fue|es|e|foi)\b"
)


# RF1S: the item turned out to belong to a known relative ("era una compra de mi
# hija", "fue mi esposa"), which resolves an earlier non-recognition.
_RECOGNIZED_ATTRIBUTION = _rx(
    r"(?<!no )(?<!nao )(?<!nunca )"
    r"\b(?:era|eran|fue|fueron|resulto ser|resultaron ser|foi|foram|eram)\s+"
    r"(?:(?:un|una|unos|unas|el|la|los|las|o|a|os|as|um|uma)\s+(?:[^\s,.]+\s+){0,3}?"
    r"(?:de|del|da|do|das|dos)\s+|(?:de|del|da|do)\s+)?"
    r"(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\b"
)
_UNAUTHORIZED_USE = _rx(
    _WITHOUT_MY_AUTHORIZATION
    + r"|\bsin\s+(?:mi\s+)?(?:permiso|autorizacion|consentimiento)\b"
    + r"|\bsem\s+(?:a\s+)?(?:minha\s+)?(?:permissao|autorizacao|consentimento)\b"
)


_FRESH_EVENT = _rx(
    r"\b(?:pero|mas|ahora|agora|hoy|hoje|otra vez|de nuevo|nuevamente|outra vez|de novo|"
    r"novamente|volvio|volvieron|voltou|voltaram|otro|otra|otros|otras|outro|outra|outros|"
    r"outras|nuevo|nueva|nuevos|nuevas|novo|nova|novos|novas)\b"
)


def _resolved_earlier_in_sentence(sentence_text: str, start: int) -> bool:
    """RF1S: a resolution before ``start`` in the same sentence, with no fresh event after it."""

    resolution = _RESOLVED_AFTER.search(sentence_text[:start])
    return bool(resolution and not _FRESH_EVENT.search(sentence_text[resolution.end() :]))


def _resolution_blocker(sentence_text: str, message_tail: str, start: int = 0) -> str | None:
    """RF1Q: the item was resolved, or recalled after an initial non-recognition.

    RF1S: the item is also resolved when the resolution comes first in the same
    sentence ("ya se aclaró lo del débito que no reconocía") with no fresh event
    after it, or when a non-recognition told in the past or framed as initial is
    later attributed to a known relative ("resultó ser de mi esposa"), unless the
    message says that use was unauthorized.
    """

    past_or_initial = _PAST_OR_INITIAL_DENIAL.search(sentence_text)
    recalled = _RECALLED_AFTER.search(message_tail) and past_or_initial
    if _RESOLVED_AFTER.search(message_tail) or recalled:
        return "resolved_or_recognized"
    if _resolved_earlier_in_sentence(sentence_text, start):
        return "resolved_or_recognized"
    if (
        past_or_initial
        and _RECOGNIZED_ATTRIBUTION.search(message_tail)
        and not _UNAUTHORIZED_USE.search(sentence_text + " " + message_tail)
    ):
        return "resolved_or_recognized"
    return None


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


def _opens_short_clause(text: str, start: int, end: int) -> bool:
    """True when the cue opens a coordinated clause of at most eight tokens."""

    clause_start = 0
    for brk in _CLAUSE_BREAK.finditer(text, 0, start + 1):
        if brk.end() <= start + 1:
            clause_start = brk.end()
    if len(text[clause_start:start].split()) > 1:
        return False
    clause_break = _CLAUSE_BREAK.search(text, end)
    clause = text[clause_start : clause_break.start()] if clause_break else text[clause_start:]
    return len(clause.split()) <= _ANAPHORIC_MAX_TOKENS


def _rf1o_anchor(text: str, family: str) -> str | None:
    anchor = _anchor(text)
    if anchor is None:
        flow = _MONEY_FLOW_ANCHOR.search(text) or _AMOUNT_FLOW_ANCHOR.search(text)
        anchor = flow.group(0) if flow else None
    if anchor is None and family == "non_origination":
        item = _ITEM_ANCHOR.search(text)
        anchor = item.group(0) if item else None
    return anchor


_NOUN_PHRASE_TAIL = _rx(
    r"\b(?:un|una|unos|unas|el|la|los|las|um|uma|uns|umas|o|a|os|as)\s+[^\s,]+"
    r"(?:\s+[^\s,]+){0,6}\s+$"
)


def _observed_head(before: str, head: re.Pattern[str]) -> bool:
    """RF1S: a relative-clause head reached across a modifier chain in an observation."""

    match = head.search(before)
    return bool(match and _OBSERVED_ACTIVITY.search(before[: match.start()]))


def _activity_relative_head(before: str) -> bool:
    return bool(_RELATIVE_HEAD.search(before)) or _observed_head(before, _OBSERVED_RELATIVE_HEAD)


def _product_relative_anchor(before: str) -> str | None:
    """Anchor for a relative-clause origination denial, or None.

    The head is a product noun, possibly behind a modifier chain inside an
    observation (RF1S), or any noun phrase the customer observes in their
    financial records ("en la central de riesgo figura un ... que nunca solicité").
    """

    if _PRODUCT_RELATIVE_HEAD.search(before) or _observed_head(before, _OBSERVED_PRODUCT_HEAD):
        product = _PRODUCT_ANCHOR.search(before)
        return product.group(0) if product else None
    noun_phrase = _NOUN_PHRASE_TAIL.search(before)
    record = _RECORD_LOCATION.search(before)
    if (
        noun_phrase
        and record
        and _OBSERVED_ACTIVITY.search(before[: noun_phrase.start()])
    ):
        return record.group(0)
    return None


def _rf1o_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF1O cue, or None when the cue is not tied to activity."""

    text = sentences[index].text
    cue = text[start:end]
    if family == "account_intrusion":
        # The customer's own account or app is the anchor.
        return cue
    if family == "presence_denial":
        # The located activity must precede the place relative clause.
        return _anchor(text[:start])
    if family == "non_origination" and _RELATIVIZER_START.match(cue):
        if _activity_relative_head(text[:start]):
            # A relative clause is anchored by its own head, never by another sentence.
            return _rf1o_anchor(text[:start], family)
        # Without a nominal head "que" is a complementizer ("le confirmo que no
        # programé nada"); only a back-referring form inside it can still license.
        backref = _SETUP_BACKREF.search(text, start)
        if backref is None or backref.start() >= end:
            return None
        start, end = backref.start(), backref.end()
        cue = text[start:end]
    anchor = _rf1o_anchor(text, family)
    if anchor is not None or index == 0:
        return anchor
    if (
        len(text.split()) <= _ANAPHORIC_MAX_TOKENS
        or _BACK_REFERENCE.search(cue)
        or _opens_short_clause(text, start, end)
    ):
        previous = sentences[index - 1].text
        return _rf1o_anchor(previous, family)
    return None


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

    if family in _RF1S_FAMILIES:
        return _rf1s_blocker(sentence, start, end, family, message_tail, message_head)
    if family in _RF1Q_FAMILIES:
        return _rf1q_blocker(sentence, start, end, family, message_tail, message_head)
    if family in _RF1O_FAMILIES:
        return _rf1o_blocker(sentence, start, end, family, message_tail, message_head)
    if (
        family == "ownership_denial"
        and _PROVENANCE_CUE.match(text[start:end])
        and _CORRECTIVE_REATTRIBUTION.search(text[end:])
    ):
        return "corrective_reattribution"
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
    resolution = _resolution_blocker(text, message_tail, start)
    if resolution is not None:
        return resolution
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


def _sentence_protasis(before: str) -> bool:
    """A conditional anywhere earlier in the sentence (not an affirmative "sí,")."""

    return any(
        not before[match.end() :].lstrip().startswith(",")
        for match in _PROTASIS.finditer(before)
    )


def _rf1o_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1O families.

    They reuse the shared blockers, but read conditional scope over the whole
    sentence (a comma must not hide "si ..."), and each family adds the checks
    that keep it a report rather than a description, plan, or question.
    """

    text = sentence.text
    before = text[:start]
    after = text[end:]
    cue = text[start:end]
    prefix = _clause_prefix(text, start)
    presupposed_relative = bool(_RELATIVIZER_TAIL.search(prefix)) or bool(
        _RELATIVIZER_START.match(cue) and _activity_relative_head(before)
    )

    if _DOUBLE_NEGATION.search(before):
        return "double_negation"
    if _PRIOR_BELIEF.search(before):
        return "prior_belief"
    if family != "third_party_denial" and _REPORTED_SPEECH.search(before):
        # A relayed denial is what a third-party report is made of.
        return "reported_speech"
    hedge = _INTRUSION_HEDGE_TAIL if family == "account_intrusion" else _HEDGE_TAIL
    if hedge.search(prefix):
        return "uncertainty_hedge"
    if _LATER_RECOGNITION.search(message_tail):
        return "later_recognition"
    resolution = _resolution_blocker(text, message_tail, start)
    if resolution is not None:
        return resolution
    if _PERMISSION_GRANTED.search(_NEGATED_GRANT.sub(" ", message_tail)):
        return "authorized_third_party"
    if _sentence_protasis(before):
        return "conditional_protasis"
    in_question = sentence.question_start is not None and start >= sentence.question_start
    if in_question and not presupposed_relative:
        return "interrogative_scope"

    if family == "account_intrusion":
        singular = _INTRUSION_SINGULAR_CUE.match(cue)
        slot = _INTRUSION_SINGULAR_SLOT if singular else _INTRUSION_PLURAL_SLOT
        if not slot.search(prefix):
            return "named_or_negated_subject"
        if _NON_BANK_ACCOUNT_AFTER.match(after):
            return "non_bank_account"
        return None
    if family == "presence_denial":
        if not _OBSERVED_ACTIVITY.search(before):
            return "activity_not_observed"
        if _PLANNED_ACTIVITY.search(before):
            return "planned_activity"
        if _SELF_PERFORMED_ACTIVITY.search(before):
            return "self_performed_activity"
        if _KNOWN_PERSON_ATTRIBUTION.search(message_tail):
            return "authorized_third_party"
        return None
    if family == "third_party_denial":
        relay_context = message_head + " " + cue
        if not (
            _KIN_POSSESSED.search(relay_context) or _REPRESENTED_PRINCIPAL.search(relay_context)
        ):
            return "no_named_relative"
        if _LATER_ATTRIBUTION.search(message_tail):
            return "later_recognition"
        # RF1S: "no fue él" only says who did not do it; when the message names the
        # relative who did ("la hizo mi esposa; no fue él"), nobody disowns it.
        if _ELLIPTICAL_AGENCY.search(cue) and _KIN_PERFORMED.search(
            message_head + " " + cue + " " + message_tail
        ):
            return "attributed_to_named_relative"
        # "mi hijo no la hizo, la hice yo" / "yo hice la compra y mi esposa no la
        # aprobó": the customer performed the activity, so nobody is disowning it.
        if _SELF_PERFORMED_ACTIVITY.search(message_head) or _SELF_PERFORMED_ACTIVITY.search(
            message_tail
        ):
            return "self_performed_activity"
    relative = _REFERENCE_BEFORE.search(before)
    if family in {"household_denial", "third_party_denial"} and not (
        _PRESUPPOSING_VERB.search(cue)
        or (relative and _RELATIVE_HEAD.search(before[: relative.start()]))
        or _REFERENCE_CLITIC.search(cue)
        or _REFERENCE_AFTER.match(after)
    ):
        return "no_existing_item"
    if family == "non_origination" and (
        _FORGOT_TO_ACT.search(message_head) or _FORGOT_TO_ACT.search(message_tail)
    ):
        return "not_yet_or_causal"
    if (
        _NOT_YET_BEFORE.search(before)
        or _NOT_YET_OR_CAUSAL_AFTER.search(after)
        or _SYSTEM_FAILURE.search(text)
    ):
        return "not_yet_or_causal"
    return None


def _rf1q_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF1Q cue, or None when the cue is not tied to a referent."""

    text = sentences[index].text
    cue = text[start:end]
    if family == "relayed_denial":
        return _rf1o_licensed_anchor(sentences, index, start, end, "third_party_denial")
    if family in {"identity_misuse", "product_disownment"}:
        # The product the cue names is the anchor.
        product = _PRODUCT_ANCHOR.search(cue)
        return product.group(0) if product else None
    # product_origination_denial
    if _RELATIVIZER_START.match(cue):
        # A relative clause is anchored by its own product head only.
        return _product_relative_anchor(text[:start])
    # The product must be named in the cue or before it ("nunca pedí, ¿cómo
    # solicito una tarjeta?" names a product it has not been given).
    product = _PRODUCT_ANCHOR.search(text[:end])
    if product is not None:
        return product.group(0)
    if index > 0 and (
        len(text.split()) <= _ANAPHORIC_MAX_TOKENS
        or _BACK_REFERENCE.search(cue)
        or _opens_short_clause(text, start, end)
    ):
        previous = _PRODUCT_ANCHOR.search(sentences[index - 1].text)
        return previous.group(0) if previous else None
    return None


_ACCEPTANCE = _rx(r"\b(?:acepte|he aceptado|aceitei)\b")
_CHARGED_ITEM = _rx(
    r"\b(?:cobrad|debitad|descontad|cargad|facturad)[oa]s?\b"
    r"|\b(?:me|lo|la|los|las|o|a)\s+(?:cobran|cobraron|descuentan|descontaron|debitan|debitaron|"
    r"cobram|cobraram|descontam|debitam)\b"
    r"|\b(?:cobro|cobros|cargo|cargos|debito|debitos|cobranca|cobrancas|descuento|descuentos|"
    r"desconto|descontos)\b"
)
_EMPHATIC_ORIGIN_DENIAL = _rx(r"\b(?:yo|eu|nunca|jamas|jamais)\b")
_NOT_YET_AFTER = _rx(r"^\W*(?:[a-z0-9-]+\s+){0,3}?(?:todavia|aun|ainda)\b")


def _rf1q_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1Q families.

    The relay family is the RF1O third-party family reached through reported
    speech, so it takes the third-party checks unchanged. The product families
    take the shared RF1O scope checks (whole-sentence protasis, question scope,
    hedges, retraction, resolution, permission) plus their own.
    """

    if family == "relayed_denial":
        return _rf1o_blocker(
            sentence, start, end, "third_party_denial", message_tail, message_head
        )
    text = sentence.text
    before = text[:start]
    after = text[end:]
    cue = text[start:end]
    prefix = _clause_prefix(text, start)
    presupposed_relative = bool(
        _RELATIVIZER_START.match(cue) and _product_relative_anchor(before) is not None
    )

    if _DOUBLE_NEGATION.search(before):
        return "double_negation"
    if _PRIOR_BELIEF.search(before):
        return "prior_belief"
    if _REPORTED_SPEECH.search(before):
        return "reported_speech"
    hedge = _INTRUSION_HEDGE_TAIL if family == "identity_misuse" else _HEDGE_TAIL
    if hedge.search(prefix):
        return "uncertainty_hedge"
    if _LATER_RECOGNITION.search(message_tail):
        return "later_recognition"
    resolution = _resolution_blocker(text, message_tail, start)
    if resolution is not None:
        return resolution
    if _PERMISSION_GRANTED.search(_NEGATED_GRANT.sub(" ", message_tail)):
        return "authorized_third_party"
    if _sentence_protasis(before):
        return "conditional_protasis"
    in_question = sentence.question_start is not None and start >= sentence.question_start
    if in_question and not presupposed_relative:
        return "interrogative_scope"
    if family == "product_disownment" and _PRODUCT_REATTRIBUTION.search(after):
        return "corrective_reattribution"
    if family == "product_origination_denial":
        if _FORGOT_TO_ACT.search(message_head) or _FORGOT_TO_ACT.search(message_tail):
            return "not_yet_or_causal"
        if _NOT_YET_BEFORE.search(before) or _NOT_YET_AFTER.search(after):
            return "not_yet_or_causal"
        if _SYSTEM_FAILURE.search(text):
            return "not_yet_or_causal"
        whole = message_head + " " + cue + " " + message_tail
        if _KIN_ORIGINATION.search(whole) and not _WITHOUT_AUTHORIZATION.search(whole):
            return "attributed_to_named_relative"
        if _ACCEPTANCE.search(cue):
            # RF1S: declining an offer is not a report. Acceptance is disowned only
            # over an item already charged or shown in the customer's records, and a
            # reason clause marks a decision, not a disowning.
            if _NOT_YET_OR_CAUSAL_AFTER.search(after):
                return "not_yet_or_causal"
            if not (
                _CHARGED_ITEM.search(whole)
                or _RECORD_LOCATION.search(whole)
                or _OBSERVED_ACTIVITY.search(message_head + " " + before)
            ):
                return "no_existing_item"
        # As for non-performance, an emphatic subject or "nunca" marks disowning,
        # so a following reason clause does not turn it into a failure to act.
        emphatic = bool(_EMPHATIC_BEFORE.search(before) or _EMPHATIC_ORIGIN_DENIAL.search(cue))
        if not emphatic and _NOT_YET_OR_CAUSAL_AFTER.search(after):
            return "not_yet_or_causal"
    return None


def _rf1s_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF1S cue, or None when the cue is not tied to the customer's account."""

    text = sentences[index].text
    cue = text[start:end]
    if family == "credential_takeover":
        # The customer's own credential is the anchor.
        credential = _rx(_CREDENTIAL).search(cue)
        return credential.group(0) if credential else None
    if family == "impersonation":
        # The customer is the referent; the conversation must be about banking.
        if any(_BANK_CONTEXT.search(sentence.text) for sentence in sentences):
            return cue
        return None
    # unnamed_actor_activity: the customer's account, card, or data as source,
    # instrument, or location, or activity observed in the customer's records.
    tie = _ACCOUNT_TIE.search(text) or _MONEY_FLOW_ANCHOR.search(text)
    if tie is not None:
        return tie.group(0)
    if _OBSERVATION_FRAME.search(text[:start]) and _RECORDS_CONTEXT.search(text):
        # The observed actor verb is itself the activity.
        return _rf1o_anchor(text, family) or cue
    return None


_DATIVE_REPORT = _rx(r"\b(?:me|nos)\s+(?:dice|dijo|dicen|dijeron|diz|disse|dizem|disseram)\s+que\b")


def _rf1s_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1S families.

    They take the shared RF1O scope checks (whole-sentence protasis, question
    scope, hedges, retraction, resolution, permission). Reported speech blocks
    unless it is a notification to the customer ("me dice que ...") or a relay by
    a named relative or represented principal. Each family adds its own checks.
    """

    text = sentence.text
    before = text[:start]
    after = text[end:]
    cue = text[start:end]
    prefix = _clause_prefix(text, start)
    whole = message_head + " " + cue + " " + message_tail

    if _DOUBLE_NEGATION.search(before):
        return "double_negation"
    if _PRIOR_BELIEF.search(before):
        return "prior_belief"
    if _REPORTED_SPEECH.search(before) and not _DATIVE_REPORT.search(before):
        return "reported_speech"
    if _INTRUSION_HEDGE_TAIL.search(prefix):
        return "uncertainty_hedge"
    if _LATER_RECOGNITION.search(message_tail):
        return "later_recognition"
    resolution = _resolution_blocker(text, message_tail, start)
    if resolution is not None:
        return resolution
    # These cues report a past event, so a resolution earlier in the same sentence
    # covers it ("ya me reintegraron lo que alguien retiró ..."), unless a fresh event
    # is marked in between ("..., pero ahora alguien ...").
    if _PERMISSION_GRANTED.search(_NEGATED_GRANT.sub(" ", message_tail)):
        return "authorized_third_party"
    # The cue is included: "se alguém fez" needs the subject to read as a protasis.
    if _sentence_protasis(text[:end]):
        return "conditional_protasis"
    if sentence.question_start is not None and start >= sentence.question_start:
        return "interrogative_scope"

    if family == "unnamed_actor_activity":
        remainder = _UNNAMED_CHANGE.sub("", cue).strip()
        incoming = _INCOMING_DATIVE.match(remainder) or _TO_MY_ACCOUNT.search(after)
        if incoming and not _FROM_MY_ACCOUNT.search(text):
            return "incoming_transfer"
        if _DELEGATED_FOR_ME.search(after) or _DELEGATED_REQUEST.search(message_tail):
            return "delegated_by_customer"
        if _NOT_YET_BEFORE.search(before) or _NOT_YET_AFTER.search(after):
            return "not_yet_or_causal"
        return None
    if family == "impersonation":
        if _NON_BANK_PLATFORM.search(after):
            return "non_bank_context"
        return None
    # credential_takeover
    if _CUSTOMER_REQUESTED.search(whole):
        return "customer_requested"
    if not (_UNNAMED_CHANGE.match(cue) or _CHANGE_DISOWNED.search(whole)):
        return "change_not_disowned"
    return None


# ------------------------------------------------- RF1Q structural-scope demotion
# The structural resolver asserts a few non-report shapes: an advice question with
# an indefinite-future protasis embedded after its question word ("¿Qué debo hacer
# si algún día veo un cargo que no reconozco?"), and a non-recognition the
# customer resolves later in the same message ("No reconocí el cargo al
# principio, pero ya me acordé: fue la suscripción"). For exactly these shapes
# the structural assertion is demoted: it no longer decides on its own, and the
# denial-safety layer, with all of its blockers, decides instead.
_INDEFINITE_PROTASIS = _rx(
    r"\b(?:si|se|caso)\s+(?:yo\s+|eu\s+)?(?:algun dia|alguna vez|en algun momento|en el futuro|"
    r"un dia|algum dia|um dia|alguma vez|no futuro|por acaso|por casualidad|llegara a|"
    r"llego a|llegase a|chegar a)\b"
    r"|\bsi\s+(?:yo\s+)?(?:me\s+)?(?:viera|vieras|apareciera|aparecieran|hubiera|hubiese|"
    r"tuviera|encontrara|notara|detectara|ocurriera|pasara|llegara)\b"
    r"|\bse\s+(?:eu\s+)?(?:me\s+)?(?:vir|aparecer|aparecerem|houver|tiver|surgir|surgirem|"
    r"acontecer|notar|encontrar|vier|visse|aparecesse|houvesse|tivesse)\b"
    r"|\bcaso\s+(?:eu\s+)?(?:veja|apareca|aparecam|haja|tenha|surja|surjam)\b"
    r"|\b(?:en caso de que|supongamos que|suponhamos que|imaginemos que|hipoteticamente)\b"
)
_SOURCE_SENTENCE_BREAK = _rx(r"[.!?;:\n]")
# RF1S: the customer's own attempted payment came back "not authorized". The
# adjectival non-authorization is the system's status on the customer's own
# attempt, not a denial of someone else's activity. It needs an own attempt in
# the same sentence (a possessed transaction or an attempt verb), no newly
# introduced item, and a decline outcome or a status frame on the label.
_ADJECTIVAL_NON_AUTHORIZATION = _rx(r"\b(?:no|nao)\s+(?:(?:fue|fueron|foi|foram)\s+)?autorizad[oa]s?\b")
_FIRST_PERSON_DISOWNING = _rx(
    r"\b(?:no|nunca|jamas|nao|jamais)\s+(?:(?:lo|la|los|las|o|a|os|as|me)\s+)?"
    r"(?:reconozco|reconoci|reconheco|reconheci|hice|realice|autorice|fiz|realizei|autorizei|"
    r"pedi|solicite|solicitei)\b"
    r"|\b(?:no fui yo|yo no fui|nao fui eu|eu nao fui)\b"
    r"|\b(?:no|nao)\s+(?:es|son|e|sao)\s+(?:mio|mia|mios|mias|meu|minha|meus|minhas)\b"
    r"|\bautorizad[oa]s?\s+por\s+(?:mi|mim)\b"
)
_OWN_ATTEMPT = _rx(
    r"\b(?:mi|mis|meu|minha|meus|minhas)\s+(?:pago|pagos|compra|compras|transaccion|"
    r"transacciones|transferencia|transferencias|retiro|giro|pagamento|pagamentos|transacao|"
    r"transacoes|saque|pix)\b"
    r"|\b(?:intente|intentamos|quise|quisimos|trate de|tratamos de|tentei|tentamos|quis)\b"
    r"|\b(?:al|ao|fui a|fui|fuimos a|fomos)\s+(?:pagar|comprar|retirar|sacar|transferir)\b"
    r"|\b(?:estaba|estava)\s+(?:pagando|comprando|retirando|sacando|transfiriendo|transferindo)\b"
)
_DECLINE_OUTCOME = _rx(
    r"\b(?:rechaz|declin|deneg|recusad|recusou|recusaram|negad)\w*"
    r"|\bno\s+(?:me\s+)?(?:paso|pasa|dejo|deja|funciono|funciona)\b"
    r"|\bno\s+se\s+(?:pudo|proceso|aprobo)\b"
    r"|\bnao\s+(?:me\s+)?(?:passou|passa|deixou|funcionou|foi aprovad[oa])\b"
    r"|\b(?:tuve|tuvimos|tive|tivemos)\s+que\s+pagar\b"
)
_STATUS_FRAME = _rx(
    r"\b(?:salio|sale|aparece|aparecio|dice|dijo|dio|marco|marca|quedo|figura|diz|disse|deu|"
    r"ficou|apareceu|consta)\s+(?:como\s+)?\W?(?:[a-z]+\s+){0,2}?(?:no|nao)\s+autorizad"
)
_NEW_ITEM_INTRO = _rx(
    r"\b(?:hay|habia|hubo|aparece|aparecen|aparecio|tengo|veo|vi|tem|houve|apareceu|vejo)\s+"
    r"(?:un|una|unos|unas|dos|tres|varios|varias|otro|otra|um|uma|uns|umas|outro|outra)\b"
)


def structural_assertion_demotion(text: str, source_start: int, source_end: int) -> str | None:
    """Return why a structural ASSERTIVE proposition is demoted, or None.

    ``source_start``/``source_end`` are the proposition's source offsets in
    ``text``. Only the RF1Q and RF1S shapes above demote; everything else the
    resolver asserts keeps structural authority.
    """

    before = text[:source_start]
    breaks = list(_SOURCE_SENTENCE_BREAK.finditer(before))
    sentence_start = breaks[-1].end() if breaks else 0
    if _INDEFINITE_PROTASIS.search(_normalize(text[sentence_start:source_start])):
        return "indefinite_hypothetical_protasis"
    tail = _normalize(text[source_end:])
    # RF1S: the resolver's span can swallow the start of the resolution ("no
    # reconocí ya está | aclarado"), so the check reads from the span start.
    if _RESOLVED_AFTER.search(tail) or _RESOLVED_AFTER.search(_normalize(text[source_start:])):
        return "resolved_after"
    sentence_end = _SOURCE_SENTENCE_BREAK.search(text, source_end)
    sentence = _normalize(text[sentence_start : sentence_end.start() if sentence_end else None])
    past_or_initial = _PAST_OR_INITIAL_DENIAL.search(sentence)
    if _RECALLED_AFTER.search(tail) and past_or_initial:
        return "recalled_after"
    # RF1S shapes.
    sentence_prefix = _normalize(text[sentence_start:source_start])
    if _resolved_earlier_in_sentence(sentence, len(sentence_prefix)):
        return "resolved_before"
    if (
        past_or_initial
        and _RECOGNIZED_ATTRIBUTION.search(tail)
        and not _UNAUTHORIZED_USE.search(_normalize(text))
    ):
        return "recognized_attribution"
    span = _normalize(text[source_start:source_end])
    if (
        _ADJECTIVAL_NON_AUTHORIZATION.search(span)
        and not _FIRST_PERSON_DISOWNING.search(span)
        and _OWN_ATTEMPT.search(sentence)
        and not _NEW_ITEM_INTRO.search(sentence)
        and (_DECLINE_OUTCOME.search(_normalize(text)) or _STATUS_FRAME.search(sentence))
    ):
        return "declined_own_attempt"
    return None


def denial_safety_findings(text: str) -> tuple[DenialSafetyFinding, ...]:
    """Return every cue occurrence with its anchor and blocking decision."""

    normalized = _normalize(text)
    sentences = _sentences(normalized)
    findings: list[DenialSafetyFinding] = []
    for index, sentence in enumerate(sentences):
        seen: set[tuple[bool, int, int]] = set()
        for family, pattern in _CUE_FAMILIES:
            for match in pattern.finditer(sentence.text):
                # RF1Q families keep their own span bookkeeping, so an older family
                # matching the same span (and blocked for lack of an activity
                # anchor) cannot hide a product-anchored RF1Q cue.
                span = (
                    2 if family in _RF1S_FAMILIES else int(family in _RF1Q_FAMILIES),
                    match.start(),
                    match.end(),
                )
                if span in seen:
                    continue
                seen.add(span)
                if family in _RF1S_FAMILIES:
                    anchor = _rf1s_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                elif family in _RF1Q_FAMILIES:
                    anchor = _rf1q_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                elif family in _RF1O_FAMILIES:
                    anchor = _rf1o_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                else:
                    anchor = _anchor(sentence.text)
                if (
                    anchor is None
                    and family in _ANAPHORIC_FAMILIES
                    and index > 0
                    and (
                        _anaphora_eligible(sentence.text, match.start(), match.end(), family)
                        or (
                            _PROVENANCE_CUE.match(match.group(0)) is not None
                            and _opens_short_clause(sentence.text, match.start(), match.end())
                        )
                    )
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
