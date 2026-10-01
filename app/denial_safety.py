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
   heads, and relays by someone acting for the account holder. RF1U adds an activity
   item characterized as fraudulent or unknown (presented as the customer's own),
   third-party authorship with an explicit negated self, personal/card-data misuse
   for financial activity, and a scam followed by a transaction in the customer's
   name; it also makes the Brazilian "movimento" an activity noun.
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
    r"pix|saque|saques|gasto|gastos|boleto|boletos|movimento|movimentos|destinatario|destinatarios|"
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
    r"transacoes|pix|saque|saques|gasto|gastos|boleto|boletos|movimento|movimentos|suscripcion|"
    r"suscripciones|assinatura|assinaturas|domiciliacion|recorrencia)\b(?:\s+[^\s,]+){0,8}\s+$"
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
    r"cobrancas|lancamento|lancamentos|movimiento|movimientos|movimento|movimentos|movimentacao|"
    r"transaccion|"
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

# ---------------------------------------------------------------- RF1U families
# Activity items a customer can characterize as fraudulent or unknown.
_ES_ITEM = (
    r"(?:cargo|cargos|cobro|cobros|compra|compras|pago|pagos|movimiento|movimientos|operacion|"
    r"operaciones|transaccion|transacciones|transferencia|transferencias|debito|debitos|retiro|"
    r"retiros|consumo|consumos|giro|giros|avance|avances)"
)
_PT_ITEM = (
    r"(?:cobranca|cobrancas|compra|compras|pagamento|pagamentos|lancamento|lancamentos|operacao|"
    r"operacoes|transacao|transacoes|transferencia|transferencias|pix|debito|debitos|saque|saques|"
    r"gasto|gastos|ted|boleto|boletos|movimento|movimentos|movimentacao|movimentacoes)"
)
_ITEM = r"(?:" + _ES_ITEM + r"|" + _PT_ITEM + r")"
# At most two bare modifiers sit between the item and its characterization ("un
# cobro mensual desconocido"). A preposition, determiner, or relativizer ends the
# item phrase, so "una transferencia de un remitente desconocido" characterizes
# the sender, not the transfer.
_ITEM_MODIFIERS = (
    r"(?:\s+(?!(?:de|del|da|do|das|dos|que|a|al|ao|en|em|no|na|nos|nas|por|para|pra|con|com|y|e|"
    r"un|una|um|uma|el|la|o|os|as|los|las|mi|mis|meu|minha|se|me)\b)[a-z0-9]+){0,2}"
)
_FRAUD_ADJECTIVE = r"fraudulent[oa]s?"
_UNKNOWN_ADJECTIVE = (
    r"(?:desconocid[oa]s?|desconhecid[oa]s?|(?:no|nao)\s+(?:reconocid|reconhecid)[oa]s?|"
    r"de\s+(?:origen|origem|procedencia)\s+(?:desconocid|desconhecid)[oa])"
)
# The characterized item must be presented as the customer's actual item: a copula
# ("es un cargo fraudulento"), its presence or observation ("tengo / hay / me
# salió / apareceu / estou com"), a charge to the customer ("me hicieron un ..."),
# a report verb ("quiero reportar un ..."), a demonstrative, or the customer's own
# account as its location. A bare mention ("cómo identificar una compra
# fraudulenta") is not a report.
# Articles, numerals, and quantifiers before the item ("me cargaron dos pagos ...").
_QUANTIFIER = (
    r"(?:(?:un|una|unos|unas|um|uma|uns|umas|dos|tres|cuatro|varios|varias|algunos|algunas|"
    r"otro|otra|otros|otras|dois|duas|alguns|algumas|outro|outra|outros|outras)\s+){0,2}"
)
# The copula's subject is null, a demonstrative, or a belief complementizer ("creo
# que es ..."), which the structural grammar also asserts.
_CHARACTERIZATION_COPULA = _rx(
    r"(?:^|\b(?:esto|eso|este|ese|esta|esa|aquello|isso|isto|esse|essa|aquilo|ele|ela)\s+"
    r"|\b(?:creo|pienso|sospecho|estoy seguro|estoy segura|acho|penso|suspeito|tenho certeza|"
    r"estou certo|estou certa)\s+que\s+)"
    r"(?:es|fue|era|son|fueron|eran|e|foi|sao|foram|eram)\s+" + _QUANTIFIER + r"$"
)
_PRESENCE_VERB = (
    r"(?:tengo|tenia|tenemos|hay|habia|hubo|aparece|aparecen|aparecio|aparecieron|veo|vi|vimos|"
    r"sale|salen|salio|salieron|figura|figuran|registra|registran|llego|llegaron|tenho|tinha|"
    r"temos|tem|ha|houve|aparecem|apareceu|apareceram|vejo|consta|constam|caiu|cairam|chegou|"
    r"chegaram|saiu|sairam|veio|vieram|estou com|estoy con|encontre|encontrei|identifique|"
    r"identifiquei|detecte|detectei|note|notei)"
)
# The presence verb's object must be the item itself: the window may not cross a
# topic noun or a non-locative preposition ("tengo una duda sobre compras
# fraudulentas", "tenemos un protocolo para pagos fraudulentos").
_TOPIC_WORD = (
    r"(?:sobre|acerca|respecto|relacion|contra|para|pra|de|del|da|do|das|con|com|sin|sem|"
    r"como|duda|dudas|duvida|duvidas|pregunta|preguntas|pergunta|perguntas|consulta|consultas|"
    r"informacion|informacao|questao|interes|interesse|miedo|medo|video|noticia|noticias|"
    r"articulo|artigo|protocolo|politica|seguro)"
)
_CHARACTERIZATION_PRESENCE = _rx(
    r"\b" + _PRESENCE_VERB + r"\b(?:\s+(?!" + _TOPIC_WORD + r"\b)[^\s,]+){0,6}?\s+$"
)
# The characterization is about the topic in general, not an item of the customer's.
_GENERAL_TOPIC = _rx(
    r"\b(?:en general|em geral|en las noticias|nas noticias|nos jornais|en la tele|na tv|"
    r"reportaje|reportagem)\b"
)
_CHARGE_TO_ME = (
    r"(?:hicieron|cobraron|cargaron|aplicaron|debitaron|pasaron|realizaron|efectuaron|fizeram|"
    r"cobraram|debitaram|lancaram|passaram|realizaram|efetuaram)"
)
_CHARACTERIZATION_CHARGE = _rx(
    r"\b(?:(?:me|nos)\s+)?" + _CHARGE_TO_ME + r"\s+" + _QUANTIFIER + r"$"
)
_CHARACTERIZATION_REPORT = _rx(
    r"\b(?:reportar|reporto|reporte|denunciar|denuncio|reclamar|reclamo|disputar|disputo|"
    r"impugnar|impugno|contestar|contesto|desconocer|informar|informo|avisar|aviso)\s+"
    r"(?:(?:sobre|de|por)\s+)?(?:(?:un|una|unos|unas|um|uma|uns|umas|el|la|los|las|o|a|os|as)\s+)?$"
)
_CHARACTERIZATION_DEMONSTRATIVE = _rx(
    r"\b(?:este|esta|estos|estas|ese|esa|esos|esas|aquel|aquella|esse|essa|esses|essas|aquele|"
    r"aquela)\s+$"
)
_CHARACTERIZATION_BARE_START = _rx(r"^" + _QUANTIFIER + r"$")
_OWN_ACCOUNT_LOCATION = _rx(
    r"^(?:\s+[^\s,]+){0,4}?\s+(?:en|de|desde|na|no|da|do|em)\s+(?:mi|mis|minha|meu|minhas|meus)\s+"
    r"(?:cuenta|cuentas|tarjeta|tarjetas|extracto|estado de cuenta|resumen|app|conta|contas|"
    r"cartao|cartoes|extrato|fatura|aplicativo)\b"
)
# "No tengo ningún cargo desconocido": the item's presence is denied.
_NEGATED_PRESENCE = _rx(
    r"\b(?:no|nao|nunca|jamas|jamais|tampoco|tampouco)\s+(?:(?:me|te|se|lo|la|le|nos)\s+)?"
    + _PRESENCE_VERB + r"\b"
    r"|\b(?:ningun|ninguna|ningunos|ningunas|nenhum|nenhuma|sin|sem|nada de)\s+"
    r"(?:(?:otro|otra|outro|outra)\s+)?$"
)
# Money arriving at the customer ("me llegó una transferencia desconocida") is
# incoming, not unauthorized activity on the customer's account.
_INCOMING_RECEIPT = _rx(
    r"\b(?:recibi|recibimos|me llego|me llegaron|nos llego|me depositaron|me consignaron|"
    r"me transfirieron|me enviaron|me mandaron|me hicieron|me hizo|me giraron|recebi|recebemos|"
    r"me mandaram|me enviaram|me transferiram|me depositaram|me fizeram|me fez|entrou|entraram|"
    r"me caiu|"
    # Arrival verbs on a transfer-type item mean money arriving.
    r"llego|llegaron|entro|entraron|ingreso|ingresaron|cayo|cayeron|chegou|chegaram|caiu|cairam)\b"
)
_INCOMING_ITEM = _rx(
    r"^(?:transferencia|transferencias|pix|ted|giro|giros|deposito|depositos|abono|abonos)\b"
)
# A recognition already made earlier in the sentence ("ya reconocí el movimiento
# desconocido, ...") resolves the characterization.
_RECOGNIZED_BEFORE = _rx(
    r"\b(?:ya|ja)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:reconoci|reconheci|identifique|"
    r"identifiquei|aclare|esclareci)\b"
)
# Advice or information about the topic, not a report of an item.
_INFORMATIONAL_FRAME = _rx(
    r"\bcomo\s+(?:\S+\s+){0,3}?(?:identificar|reconocer|reconhecer|evitar|reportar|denunciar|"
    r"contestar|reclamar|detectar|prevenir|proceder|actuar|agir|lidar|bloquear)\b"
    r"|\b(?:informacion|informacao|consejos|dicas|recomendaciones|recomendacoes)\s+"
    r"(?:sobre|para|de)\b"
    r"|\b(?:que|o que)\s+(?:hacer|hago|debo hacer|se hace|fazer|faco|devo fazer)\b"
)
# A message quoting what a text or caller claims ("un SMS diciendo que tengo ...")
# relays an unverified claim, not the customer's report.
_RELAYED_CLAIM = _rx(
    r"\b(?:diciendo|dizendo|avisando|informando|afirmando|alegando)\s+que\b"
    r"|\b(?:que|onde)\s+(?:dice|decia|diz|dizia|afirma|alega)\s+que\b"
)
# U-P01: a lead clause that is only a hedge or a prior belief ("Tal vez, es un
# cargo fraudulento", "Pensé, es ...") keeps the following copula unasserted.
_LEAD_CLAUSE_HEDGE = _rx(
    r"^\s*(?:tal vez|talvez|quizas|quiza|puede ser|pode ser|podria ser|poderia ser|no se|nao sei|"
    r"a lo mejor|capaz|sera|no estoy seguro|no estoy segura|nao tenho certeza|supongo|suponho|"
    r"pense|pensaba|crei|creia|pensei|achei|achava)\s*$"
)
_CHARACTERIZATION_HEDGE = _rx(
    r"\b(?:podria|puede|podra|seria|pode|poderia|sera|parece|tal vez|quizas|quiza|talvez)\s+"
    r"(?:ser\s+)?(?:(?:un|una|um|uma)\s+)?$"
)

# Third-party authorship with the customer explicitly disowning it: an unnamed
# party did it, "not me" ("fue hecha por otra persona, no por mí", "lo hizo un
# tercero, no yo", "foi outra pessoa, não eu"). The contrast is part of the cue.
_NEGATED_SELF = r"\s*,?\s*(?:(?:y|e|pero|mas)\s+)?(?:no|nao)\s+(?:por\s+(?:mi|mim)|yo|eu)\b"
_AGENT_PARTICIPLE = (
    r"(?:hech|realizad|efectuad|enviad|mandad|transferid|pagad|retirad|sacad|cobrad|solicitad|"
    r"autorizad|comprad|feit|efetuad|pag|gast)[oa]s?"
)
_ES_AUTHOR_VERBS = (
    r"(?:hizo|realizo|efectuo|envio|mando|transfirio|pago|retiro|saco|compro|pidio|solicito)"
)
_PT_AUTHOR_VERBS = (
    r"(?:fez|realizou|efetuou|enviou|mandou|transferiu|pagou|retirou|sacou|comprou|pediu|"
    r"solicitou)"
)
_THIRD_PARTY_AUTHORSHIP = (
    r"\b(?:fue|fueron|ha sido|han sido|foi|foram)\s+" + _AGENT_PARTICIPLE
    + r"\s+(?:[^\s,]+\s+){0,3}?por\s+" + _UNNAMED_ACTOR + r"\b(?:\s+[^\s,]+){0,3}?" + _NEGATED_SELF
    + r"|\b(?:fue|fueron|foi|foram)\s+" + _UNNAMED_ACTOR + r"\b" + _NEGATED_SELF
    + r"|\b(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:" + _ES_AUTHOR_VERBS + r"|" + _PT_AUTHOR_VERBS
    + r")\s+" + _UNNAMED_ACTOR + r"\b" + _NEGATED_SELF
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:(?:me|le|lhe|lo|la|los|las|o|a|os|as)\s+)?(?:"
    + _ES_ACTOR_VERBS + r"|" + _PT_ACTOR_VERBS + r")\b(?:\s+[^\s,]+){0,4}?" + _NEGATED_SELF
)

# Personal-data misuse to perform financial activity: the customer's personal,
# card, or account data used to buy, pay, transfer, or take out a product.
_DATA_NP = (
    r"(?:mis\s+datos(?:\s+(?:personales|bancarios|financieros))?|(?:los\s+)?datos\s+"
    r"(?:(?:personales|bancarios)\s+)?de\s+mi\s+(?:tarjeta|cuenta|cedula)|"
    r"mi\s+(?:cedula|identidad)|"
    r"(?:os\s+)?meus\s+dados(?:\s+(?:pessoais|bancarios))?|(?:os\s+)?dados\s+"
    r"(?:(?:pessoais|bancarios)\s+)?d(?:o|a)\s+(?:meu|minha)\s+(?:cartao|conta)|(?:o\s+)?meu\s+cpf|"
    r"(?:a\s+)?minha\s+identidade)"
)
_PLURAL_USE = (
    r"(?:usaron|han usado|estan usando|utilizaron|han utilizado|usaram|utilizaram|estao usando|"
    r"tem usado)"
)
_SINGULAR_USE = r"(?:uso|ha usado|utilizo|usou|utilizou)"
_FINANCIAL_PURPOSE = (
    r"(?:\s+[^\s,]+){0,3}?\s+(?:para|pra|a fin de|con el fin de|com o fim de)\s+(?:poder\s+)?"
    r"(?:(?:hacer|realizar|efectuar|fazer|efetuar|sacar|pedir|solicitar|tirar|abrir|contratar)\s+"
    r"(?:[^\s,]+\s+){0,3}?(?:" + _ITEM + r"|" + _PRODUCT_HEAD + r")"
    r"|comprar|pagar|transferir|retirar|girar|enviar dinero|mandar dinero|enviar dinheiro|"
    r"mandar dinheiro)\b"
)
_IMPERSONAL_ACTIVITY = (
    r"(?:hicieron|realizaron|efectuaron|sacaron|pidieron|solicitaron|compraron|pagaron|"
    r"transfirieron|fizeram|realizaram|efetuaram|sacaram|pediram|solicitaram|compraram|pagaram|"
    r"transferiram|tiraram|abrieron|abriram|contrataron|contrataram)"
)
_DATA_MISUSE = (
    r"\b" + _PLURAL_USE + r"\s+" + _DATA_NP + _FINANCIAL_PURPOSE
    + r"|\b" + _UNNAMED_ACTOR + r"\s+" + _SINGULAR_USE + r"\s+" + _DATA_NP + _FINANCIAL_PURPOSE
    + r"|\b" + _IMPERSONAL_ACTIVITY + r"\s+(?:[^\s,]+\s+){0,1}?" + _ITEM
    + r"\b(?:\s+[^\s,]+){0,3}?\s+(?:con|usando|utilizando|com)\s+" + _DATA_NP
)
_DATA_MISUSE_ITEM = _rx(
    r"\b(?:" + _ITEM + r"|" + _PRODUCT_HEAD + r"|comprar|pagar|transferir|retirar|girar|dinero|"
    r"dinheiro)\b"
)
_NAMED_SUBJECT_BEFORE = _rx(
    r"\b(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN + r"\b(?:\s+[^\s,]+){0,2}?\s*$"
    r"|\b(?:ellos|ellas|eles|elas|el|ella|ele|ela)\s+$"
)

# Scam victimization plus activity in the customer's name: the scam alone is not
# an unauthorized-activity report; the licence is an impersonal or unnamed party's
# transaction in the customer's name, with their data, or from their account.
_SCAM_NOUN = (
    r"(?:estafa|estafas|fraude|fraudes|golpe|golpes|timo|engano|phishing|trampa|vishing|"
    r"smishing)"
)
_SCAM_VICTIM = (
    r"\b(?:cai|caimos|he caido|hemos caido)\s+(?:(?:en|em|num|numa|no|na|de|del)\s+)?"
    r"(?:(?:un|una|um|uma|el|la|o|a)\s+)?" + _SCAM_NOUN + r"\b"
    r"|\b(?:fui|fuimos|he sido|hemos sido|fomos)\s+(?:victima|victimas|vitima|vitimas)\s+"
    r"(?:de|del|da|do)\s+(?:(?:un|una|um|uma|el|la|o|a)\s+)?" + _SCAM_NOUN + r"\b"
    r"|\b(?:me|nos)\s+(?:estafaron|timaron|han estafado|enganaron|han enganado|enganaram)\b"
    r"|\b(?:me|nos)\s+(?:aplicaron|aplicaram|hicieron|deram|deu|dieron)\s+"
    r"(?:(?:un|una|um|uma|el|o)\s+)?"
    + _SCAM_NOUN + r"\b"
    r"|\b(?:fui|fuimos|fomos)\s+(?:estafad|enganad|timad)[oa]s?\b"
    r"|\b(?:sofri|sufri)\s+(?:(?:un|una|um|uma)\s+)?" + _SCAM_NOUN + r"\b"
)
# Purchase, payment, and transfer verbs carry the activity themselves, whatever
# their object ("compraram passagens no meu nome").
_TRANSACTING_PLURAL = (
    r"(?:compraron|pagaron|transfirieron|retiraron|sacaron|compraram|pagaram|transferiram|"
    r"sacaram|retiraram)"
)
_ACTIVITY_IN_MY_NAME = _rx(
    r"(?<!no )(?<!nao )(?<!nunca )(?<!jamas )(?<!jamais )"
    r"\b(?:(?:" + _IMPERSONAL_ACTIVITY + r"|" + _UNNAMED_ACTOR + r"\s+(?:" + _ES_ACTOR_VERBS
    + r"|" + _PT_ACTOR_VERBS + r"))\s+(?:[^\s,]+\s+){0,4}?(?:" + _ITEM + r"|" + _PRODUCT_HEAD
    + r"|dinero|plata|dinheiro)\b|" + _TRANSACTING_PLURAL + r"\b)(?:\s+[^\s,]+){0,4}?\s+(?:"
    + _IN_MY_NAME
    + r"|(?:de|desde|con|del)\s+(?:mi|mis)\s+(?:cuenta|cuentas|tarjeta|tarjetas|datos)"
    r"|(?:da|de|com|do|na|no)\s+(?:minha|meu|minhas|meus)\s+"
    r"(?:conta|contas|cartao|cartoes|dados))\b"
)
# The customer asked the actor to do it ("pero yo se lo pedí", "eu pedi para ela
# fazer"): a delegation, not a disowning.
_RF1U_DELEGATION = _rx(
    r"\b(?:yo|eu)\s+(?:se\s+(?:lo|la|los|las)|le|les|lhe|lhes)\s+(?:pedi|encargue|solicite|"
    r"solicitei|mande|mandei|encomendei)\b"
    r"|\b(?:yo|eu)\s+(?:(?:lo|la|o|a)\s+)?(?:autorice|autorizei)\b"
    r"|\bpedi\s+(?:para|pra|a)\s+(?:el|ella|ele|ela|ellos|eles|elas|(?:o|a|mi|meu|minha)\s+\S+)\s+"
    r"(?:que\s+)?(?:hacer|hiciera|pagar|pagara|transferir|transfiriera|enviar|mandar|fazer|"
    r"fizesse|pagasse|transferisse|enviasse|mandasse)\b"
)
# "si/se/caso" right before the licensing verb makes it conditional; the shared
# protasis check leaves bare Portuguese "se" alone because it is also a clitic.
_CONDITIONAL_RIGHT_BEFORE = _rx(r"\b(?:si|se|caso)\s+$")
_NEAR_MISS_BEFORE = _rx(r"\b(?:casi|quase|por poco|por pouco|quase que)\s+(?:[^\s,]+\s+)?$")

# ---------------------------------------------------------------- RF1W families
# The customer's data taken by an impersonal or unnamed party and then used through
# a back-reference ("robaron mis datos y los usaron para ...", "pegaram meus dados e
# fizeram uma compra com eles"). The taking verb licenses the back-reference, so the
# customer's own or a merchant's use ("le di mis datos a la tienda y con ellos ...")
# stays outside.
# "Tomar datos" also means taking a customer's details down, so it is not a taking verb.
_TAKE_PLURAL = (
    r"(?:robaron|han robado|sacaron|consiguieron|obtuvieron|hackearon|clonaron|"
    r"copiaron|filtraron|roubaram|pegaram|clonaram|conseguiram|obtiveram|hackearam|copiaram|"
    r"vazaram|furtaram|capturaram)"
)
_TAKE_SINGULAR = (
    r"(?:robo|ha robado|saco|consiguio|obtuvo|hackeo|clono|copio|roubou|pegou|clonou|"
    r"conseguiu|obteve|hackeou|copiou|furtou)"
)
_DATA_PRONOUN = r"(?:ellos|ellas|eles|elas|esos datos|esses dados)"
_COORDINATED = r"(?:\s+[^\s,]+){0,3}?\s*,?\s+(?:y|e)\s+"
_PLURAL_ACTIVITY_WITH_DATA = (
    r"(?:(?:los|las|os|as)\s+)?" + _PLURAL_USE + r"(?:\s+(?:eles|elas))?" + _FINANCIAL_PURPOSE
    + r"|(?:con|com)\s+" + _DATA_PRONOUN + r"\s+" + _IMPERSONAL_ACTIVITY
    + r"\s+(?:[^\s,]+\s+){0,1}?" + _ITEM + r"\b"
    + r"|" + _IMPERSONAL_ACTIVITY + r"\s+(?:[^\s,]+\s+){0,1}?" + _ITEM
    + r"\b(?:\s+[^\s,]+){0,3}?\s+(?:con|com)\s+" + _DATA_PRONOUN + r"\b"
)
_SINGULAR_ACTIVITY_WITH_DATA = (
    r"(?:(?:los|las|os|as)\s+)?" + _SINGULAR_USE + r"(?:\s+(?:eles|elas))?" + _FINANCIAL_PURPOSE
    + r"|(?:hizo|realizo|fez|realizou)\s+(?:[^\s,]+\s+){0,1}?" + _ITEM
    + r"\b(?:\s+[^\s,]+){0,3}?\s+(?:con|com)\s+" + _DATA_PRONOUN + r"\b"
)
_DATA_MISUSE_BACKREF = (
    r"\b(?:(?:me|nos|le|lhe)\s+)?" + _TAKE_PLURAL + r"\s+" + _DATA_NP + _COORDINATED
    + r"(?:" + _PLURAL_ACTIVITY_WITH_DATA + r")"
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:(?:me|le|lhe)\s+)?" + _TAKE_SINGULAR + r"\s+" + _DATA_NP
    + _COORDINATED + r"(?:" + _SINGULAR_ACTIVITY_WITH_DATA + r")"
)
# The customer's own bank account: an account noun not followed by "de/da/do" plus
# something other than an account type ("la cuenta de correo", "a conta de luz" and
# "la cuenta de mi empresa" are not it).
_OWN_ACCOUNT_TYPE = r"(?:ahorros?|poupanca|corriente|cheques|nomina|sueldo|salario)"
_ACCOUNT_NOUN = (
    r"(?:cuenta|cuentas|conta|contas)\b"
    r"(?!\s+(?:de|da|do|del)\s+(?!" + _OWN_ACCOUNT_TYPE + r"\b))"
)
_POSSESSED_ACCOUNT = r"(?:(?:la|las|a|as)\s+)?(?:mi|mis|minha|minhas)\s+" + _ACCOUNT_NOUN
_ANY_ACCOUNT = r"(?:(?:la|las|a|as)\s+)?(?:(?:mi|mis|minha|minhas)\s+)?" + _ACCOUNT_NOUN
# Impersonal activity performed using the customer's own account ("fizeram uma
# transferência usando minha conta", "hicieron compras usando mi cuenta"). A negated
# activity ("não fizeram nenhuma ...") is not a report.
_ACCOUNT_USE = (
    r"(?<!no )(?<!nao )(?<!nunca )(?<!jamas )(?<!jamais )"
    r"\b" + _IMPERSONAL_ACTIVITY + r"\s+(?:[^\s,]+\s+){0,2}?" + _ITEM
    + r"\b(?:\s+[^\s,]+){0,3}?\s+(?:usando|utilizando)\s+" + _POSSESSED_ACCOUNT
)
# Money arriving to the customer through their account is not a report.
_RF1W_INCOMING = _rx(
    r"\b(?:pra|para)\s+(?:mi|mim)\b|\ba\s+mi\s+favor\b|\b(?:de|como)\s+destino\b"
    r"|\b(?:sueldo|salario|nomina|aguinaldo|reembolso|estorno|devolucion|devolucao|deposito)\b"
)
# The customer's account emptied or drained by an impersonal or unnamed party ("me
# vaciaron la cuenta", "alguien me vació la cuenta sin mi permiso", "zeraram minha
# conta"). The account is the customer's through a dative "me/nos" or a possessive;
# the customer's own or a named party's drain stays outside.
_DRAIN_PLURAL = (
    r"(?:vaciaron|han vaciado|limpiaron|han limpiado|esvaziaram|zeraram|limparam|rasparam)"
)
_DRAIN_SINGULAR = r"(?:vacio|ha vaciado|limpio|ha limpiado|esvaziou|zerou|limpou|raspou)"
_LEFT_EMPTY = r"(?:en\s+cero|vacia|zerada|vazia|sem\s+(?:saldo|dinheiro|nada))"
_NOT_NEGATED = r"(?<!no )(?<!nao )(?<!nunca )(?<!jamas )(?<!jamais )"
_ACCOUNT_DRAIN = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+" + _DRAIN_PLURAL + r"\s+" + _ANY_ACCOUNT
    + r"|" + _NOT_NEGATED + r"\b" + _DRAIN_PLURAL + r"\s+" + _POSSESSED_ACCOUNT
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:me|nos)\s+" + _DRAIN_SINGULAR + r"\s+" + _ANY_ACCOUNT
    + r"|\b" + _UNNAMED_ACTOR + r"\s+" + _DRAIN_SINGULAR + r"\s+" + _POSSESSED_ACCOUNT
    + r"|" + _NOT_NEGATED + r"\b(?:me|nos)\s+(?:dejaron|deixaram)\s+" + _ANY_ACCOUNT
    + r"\s+" + _LEFT_EMPTY + r"\b"
    + r"|" + _NOT_NEGATED + r"\b(?:dejaron|deixaram)\s+" + _POSSESSED_ACCOUNT
    + r"\s+" + _LEFT_EMPTY + r"\b"
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:me\s+|nos\s+)?(?:dejo|deixou)\s+" + _ANY_ACCOUNT
    + r"\s+" + _LEFT_EMPTY + r"\b"
)
_UNNAMED_ACTOR_START = _rx(r"^" + _UNNAMED_ACTOR + r"\b")

# ---------------------------------------------------------------- RF1Y families
# RF1X miss shapes of the RF1W account-drain / account-use reports, plus a guard for
# the one RF1X over-escalation. Each family is licensed only for the customer's own
# account, card, or data and an unnamed or impersonal actor.
_RF1Y_ACCOUNT = (
    r"(?:cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes)\b"
    r"(?!\s+(?:de|da|do|del)\s+(?!" + _OWN_ACCOUNT_TYPE + r"\b))"
)
_RF1Y_POSSESSED = (
    r"(?:(?:la|las|a|as|os)\s+)?(?:mi|mis|minha|minhas|meu|meus)\s+(?:" + _RF1Y_ACCOUNT
    + r"|(?:datos|dados)\b)"
)
# 1. Passive voice: the customer's account, card, or data drained or used ("mi cuenta
# fue vaciada por alguien", "fue vaciada mi cuenta por ...", "minha conta foi
# esvaziada ..."). The passive is licensed by an unnamed agent right after it or by
# a disowning in the message, so the bank or a named person draining it stays out.
_PASSIVE_AUX = r"(?:fue|fueron|ha sido|han sido|foi|foram|tem sido)"
_PASSIVE_PARTICIPLE = (
    r"(?:vaciad|limpiad|usad|utilizad|clonad|hackead|esvaziad|zerad|limpad|raspad)[oa]s?"
)
_PASSIVE_ACCOUNT_MISUSE = (
    r"\b" + _RF1Y_POSSESSED + r"(?:\s+[^\s,]+){0,2}?\s+" + _PASSIVE_AUX + r"\s+"
    + _PASSIVE_PARTICIPLE + r"\b"
    + r"|\b" + _PASSIVE_AUX + r"\s+" + _PASSIVE_PARTICIPLE + r"\s+" + _RF1Y_POSSESSED
)
_RF1Y_UNNAMED_AGENT = _rx(r"^\s*(?:,\s*)?(?:por|pelo|pela)\s+" + _UNNAMED_ACTOR + r"\b")
_RF1Y_NAMED_AGENT = _rx(
    r"^\s*(?:,\s*)?(?:por|pelo|pela)\s+(?:(?:mi|mis|meu|minha|meus|minhas)\s+" + _KIN
    + r"|(?:el|la|o|a)\s+(?:banco|empresa|tienda|loja)|banco)\b"
)
_RF1Y_DISOWNED = _rx(
    r"\b(?:no fui yo|yo no fui|nao fui eu|eu nao fui)\b|" + _WITHOUT_MY_AUTHORIZATION
    + r"|\b(?:yo|eu)\s+(?:no|nunca|nao)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?"
    r"(?:hice|autorice|saque|retire|fiz|autorizei|tirei|saquei|retirei)\b"
    r"|\b(?:no|nunca|nao)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:autorice|autorizei)\b"
)
# 2. Spanish double clitic ("me la vaciaron"): the feminine clitic stands for the
# account or balance, so the message must name a banking context for it.
_DOUBLE_CLITIC_DRAIN = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+(?:la|las)\s+(?:vaciaron|han vaciado|limpiaron|han limpiado|"
    r"dejaron\s+(?:vacia|vacias|en\s+cero))\b"
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:me|nos)\s+(?:la|las)\s+(?:vacio|ha vaciado|limpio|"
    r"ha limpiado|dejo\s+(?:vacia|vacias|en\s+cero))\b"
)
_RF1Y_BANKING_CONTEXT = _rx(
    r"\b(?:" + _ACCOUNT_NOUN + r"|(?:tarjeta|tarjetas|saldo|app|aplicacion|banca\s+(?:en\s+linea|"
    r"movil|virtual)|billetera)\b)"
)
# A physical container named before the clitic is its referent, not the account.
_RF1Y_NONFINANCIAL_REFERENT = _rx(
    r"\b(?:casa|nevera|heladera|alcancia|despensa|bodega|habitacion|maleta|mochila)\b"
)
# 3. Progressive or habitual use of the customer's account ("andou usando a minha
# conta para transferir ..."). A singular auxiliary needs an unnamed subject; the
# use needs a financial purpose or an explicit lack of permission.
_PROGRESSIVE_PLURAL = (
    r"(?:andam|andaram|andavam|vem|vinham|estao|estavam|ficaram|continuam|seguem|andan|"
    r"anduvieron|han estado|estuvieron|siguen|estan)"
)
_PROGRESSIVE_SINGULAR = (
    r"(?:anda|andou|andava|vem|vinha|veio|esta|estava|ficou|fica|continua|continuou|segue|"
    r"seguiu|anduvo|ha estado|estuvo|sigue)"
)
_PROGRESSIVE_TARGET = (
    r"\s+(?:usando|utilizando)\s+(?:(?:la|las|a|as)\s+)?(?:mi|mis|minha|minhas)\s+"
    + _ACCOUNT_NOUN + r"(?:" + _FINANCIAL_PURPOSE + r"|\s+" + _WITHOUT_MY_AUTHORIZATION + r")"
)
_PROGRESSIVE_ACCOUNT_USE = (
    _NOT_NEGATED + r"\b" + _PROGRESSIVE_PLURAL + _PROGRESSIVE_TARGET
    + r"|\b" + _UNNAMED_ACTOR + r"\s+" + _PROGRESSIVE_SINGULAR + _PROGRESSIVE_TARGET
)
# 4. A fronted lack of permission with an article-only object ("Sem minha autorização,
# alguém esvaziou a conta"): the fronted clause makes the object the customer's.
_RF1Y_WITHOUT_PERMISSION_FRONT = (
    r"(?:sin|sem)\s+(?:(?:a\s+)?(?:mi|minha)\s+)?(?:permiso|autorizacion|consentimiento|"
    r"permissao|autorizacao|consentimento)"
)
_FRONTED_PERMISSION_DRAIN = (
    r"(?:^|(?<=, ))" + _RF1Y_WITHOUT_PERMISSION_FRONT + r"\s*,?\s+(?:"
    + _UNNAMED_ACTOR + r"\s+(?:(?:me|nos)\s+)?(?:" + _DRAIN_SINGULAR + r"|" + _SINGULAR_USE + r")"
    + r"|(?:(?:me|nos)\s+)?(?:" + _DRAIN_PLURAL + r"|" + _PLURAL_USE + r"))"
    + r"\s+(?:la|las|a|as|el|o)\s+(?:" + _RF1Y_ACCOUNT + r"|saldo\b)"
)
# 5. A quantified plural account object ("me vaciaron las dos cuentas").
_RF1Y_QUANT = r"(?:dos|tres|ambas|todas|duas)"
_RF1Y_PLURAL_ACCOUNT = (
    r"(?:cuentas|contas|tarjetas|cartoes)\b(?!\s+(?:de|da|do|del)\s+(?!" + _OWN_ACCOUNT_TYPE
    + r"\b))"
)
_RF1Y_QUANTIFIED_OBJECT = (
    r"(?:(?:las|as)\s+)?" + _RF1Y_QUANT + r"\s+(?:(?:las|as)\s+)?(?:(?:mis|minhas)\s+)?"
    + _RF1Y_PLURAL_ACCOUNT
)
_RF1Y_POSSESSED_QUANTIFIED = (
    r"(?:mis|minhas)\s+" + _RF1Y_QUANT + r"\s+" + _RF1Y_PLURAL_ACCOUNT
)
_QUANTIFIED_PLURAL_DRAIN = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+" + _DRAIN_PLURAL + r"\s+(?:" + _RF1Y_QUANTIFIED_OBJECT
    + r"|" + _RF1Y_POSSESSED_QUANTIFIED + r")"
    + r"|" + _NOT_NEGATED + r"\b" + _DRAIN_PLURAL + r"\s+" + _RF1Y_POSSESSED_QUANTIFIED
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:(?:me|nos)\s+)?" + _DRAIN_SINGULAR + r"\s+(?:"
    + _RF1Y_QUANTIFIED_OBJECT + r"|" + _RF1Y_POSSESSED_QUANTIFIED + r")"
)
# 6. Leaving the customer without money ("me dejaron sin un centavo"); licensed by
# the customer's account or card, an unnamed actor, or a disowning in the message.
_RF1Y_NO_MONEY = (
    r"(?:sin|sem)\s+(?:(?:un\s+solo|um\s+so|ni\s+un|nem\s+um|un|um)\s+)?(?:centavo|peso|euro|"
    r"dolar|real|tostao|quinto)\b"
    r"|(?:sin|sem)\s+(?:plata|dinero|dinheiro|saldo|fondos|fundos)\b"
    r"|(?:sin|sem)\s+nada\s+(?:en|na|no)\s+(?:la\s+|a\s+)?(?:mi\s+|minha\s+)?(?:cuenta|conta)\b"
)
_NO_MONEY_DRAIN = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+(?:dejaron|han dejado|deixaram)\s+(?:" + _RF1Y_NO_MONEY + r")"
    + r"|\b" + _UNNAMED_ACTOR + r"\s+(?:me|nos)\s+(?:dejo|ha dejado|deixou)\s+(?:"
    + _RF1Y_NO_MONEY + r")"
)
_RF1Y_CUE_SIN = _rx(r"\bsin\b")
_RF1Y_ACCOUNT_CONTEXT = _rx(r"\b(?:cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes)\b")
# A fee, interest, or expense named after the verb is the cause, not an actor
# ("me dejaron sin un peso los intereses").
_RF1Y_POST_VERBAL_CAUSE = _rx(
    r"^(?:\s+[^\s,]+){0,4}?\s+(?:las|los|os|as|tantas|tantos|essas|esses|esas|esos)\s+"
    r"(?:comisiones|intereses|cargos|cobros|gastos|deudas|impuestos|cuotas|juros|tarifas|taxas|"
    r"despesas|dividas|parcelas|compras|facturas|faturas|cuentas|contas)\b"
)
# 7. RF1X over-escalation: non-recognition of the app, its version, or its interface
# ("no reconozco la nueva versión de la app, ¿dónde quedó el botón de transferencias?")
# is not a disowned transaction when the recognized object names no activity, money,
# account, card, or data.
_INTERFACE_OBJECT = _rx(
    r"^\s*(?:(?:el|la|los|las|o|a|os|as|este|esta|esse|essa|ese|esa)\s+)?"
    r"(?:(?:nuevo|nueva|nuevos|nuevas|novo|nova|novos|novas|ultimo|ultima|actual|atual)\s+)?"
    r"(?:version|versao|versiones|versoes|actualizacion|atualizacao|diseno|design|layout|"
    r"interfaz|interface|pantalla|tela|menu|icono|icone|boton|botao|aplicacion|aplicativo|app)\b"
)
_INTERFACE_NOUN = (
    r"(?:version|versao|actualizacion|atualizacao|diseno|design|layout|interfaz|interface|"
    r"pantalla|tela|menu|icono|icone|boton|botao|aplicacion|aplicativo|app|seccion|secao|"
    r"opcion|opcao|pestana|aba)"
)
# An interface element named after a section ("el botón de transferencias", "a tela de
# pagamentos") labels the interface; it is not an activity.
_INTERFACE_LABEL = _rx(
    r"\b" + _INTERFACE_NOUN + r"(?:\s+(?:de|del|da|do|das|dos)\s+(?:(?:la|el|los|las|o|a|os|as)\s+)?"
    r"[^\s,]+)+"
)
_INTERFACE_FINANCIAL = _rx(
    r"\b(?:" + _ITEM + r"|cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes|datos|dados|"
    r"dinero|dinheiro|plata|saldo|fondos|fundos|cargo|cargos|prestamo|emprestimo|credito|"
    r"extracto|extrato|estado de cuenta|fatura|factura|resumen)\b"
)

# ---------------------------------------------------------------- RF2 families
# RF1Z miss shapes of the RF1Y families, plus a guard for the one RF1Z
# over-escalation. Each family needs the customer's own account, card, or funds and
# an unnamed, impersonal, or disowned actor; a cue whose licence is missing stays
# unasserted.
_RF2_QUANT = r"(?:dos|tres|cuatro|ambas|ambos|todas|todos|duas|dois|quatro|varias|varios)"
_RF2_FUNDS = (
    r"(?:ahorros|poupanca|economias|saldo|dinero|plata|fondos|fundos|dinheiro|grana|sueldo|"
    r"salario|nomina|quincena|pension|pensao|aposentadoria)\b"
)
_RF2_OWN_OBJECT = (
    r"(?:(?:todo|toda|todos|todas|tudo)\s+)?(?:(?:el|la|los|las|o|a|os|as)\s+)?"
    r"(?:mi|mis|minha|minhas|meu|meus)\s+(?:" + _RF1Y_ACCOUNT + r"|" + _RF2_FUNDS + r")"
)
# A stranger or an unknown person, beyond the RF1S unnamed actors.
_RF2_ACTOR = (
    r"(?:(?:una|uma)\s+persona\s+que\s+(?:yo\s+)?no\s+conozco|uma\s+pessoa\s+que\s+(?:eu\s+)?"
    r"nao\s+conheco|alguien\s+que\s+(?:yo\s+)?no\s+conozco|alguem\s+que\s+(?:eu\s+)?nao\s+"
    r"conheco|gente\s+que\s+(?:yo\s+)?no\s+conozco|un\s+extrano|una\s+extrana|um\s+estranho|"
    r"uma\s+estranha|extranos|estranhos|" + _UNNAMED_ACTOR + r")"
)
_RF2_ACTOR_START = _rx(r"^" + _RF2_ACTOR + r"\b")
# A clause-initial frame before an impersonal plural verb: learning of it, or how long
# it has gone on ("fiquei sabendo que andavam ...", "hace días que ...").
_RF2_PLURAL_SLOT = _rx(
    r"(?:\b(?:fiquei sabendo|me entere(?:\s+de)?|me acabo de enterar(?:\s+de)?|vi|veo|vejo|"
    r"noto|note|reparei|resulta)\s+que|\b(?:hace|faz)\s+(?:[^\s,]+\s+){1,2}que|"
    r"\b(?:durante la (?:noche|madrugada)|de madrugada|anteontem|anteayer|el fin de semana|"
    r"no fim de semana))\s*(?:me\s+)?$"
)
# The customer did not do it or did not allow it: a disowning, a household denial, a
# lack of authorization or consent, or the customer being asleep or away.
_RF2_NON_AUTHORIZATION = (
    r"\bsin\s+que\s+(?:yo\s+)?(?:(?:lo|la|los|las|me|se\s+lo)\s+)?(?:diera|diese|hiciera|"
    r"autorizara|aprobara|pidiera|supiera|solicitara|ordenara|permitiera|consintiera|enterara|"
    r"diera cuenta|haya autorizado|hubiera autorizado|haya dado|hubiera dado)\b"
    r"|\bsin\s+(?:haber(?:lo|la|los|las)?|habermelo)\s+(?:yo\s+)?(?:autorizado|aprobado|pedido|"
    r"solicitado|permitido)\b"
    r"|\bsin\s+(?:mi\s+)?(?:permiso|autorizacion|consentimiento|conocimiento|aprobacion)\b"
    r"|\bsin\s+(?:preguntarme|consultarme|pedirme permiso)\b"
    r"|\bsem\s+(?:que\s+)?eu\s+(?:ter\s+|tivesse\s+|tenha\s+)?(?:autorizado|autorizar|autorizasse|"
    r"permitido|permitir|permitisse|pedido|pedir|pedisse|saber|soubesse|dado|feito|fizesse|desse|"
    r"aprovado|aprovar|aprovasse)\b"
    r"|\bsem\s+(?:a\s+|o\s+)?(?:minha\s+|meu\s+)?(?:permissao|autorizacao|consentimento|"
    r"conhecimento|aprovacao)\b"
    r"|\bsem\s+me\s+(?:perguntar|consultar|pedir)\b"
)
_RF2_DISOWNED = _rx(
    _RF2_NON_AUTHORIZATION
    + r"|\b(?:no fui yo|yo no fui|nao fui eu|eu nao fui)\b"
    r"|\b(?:yo|eu)\s+(?:no|nunca|nao|jamas|jamais)\s+(?:(?:lo|la|los|las|o|a|os|as|me|le|lhe)\s+)?"
    r"(?:saque|retire|hice|autorice|transferi|toque|movi|use|di|gaste|pedi|fiz|autorizei|tirei|"
    r"saquei|retirei|mexi|usei|gastei|dei)\b"
    r"|\b(?:nunca|jamas|jamais)\s+(?:he ido|he estado|fui|estuve|estive|pisei)\b"
    r"|\b(?:nadie|ninguno|ninguna|ninguem|nenhum|nenhuma)\s+(?:de|da|do|en|na|no)\s+(?:mi|minha|"
    r"meu)\s+(?:familia|casa)\s+(?:(?:lo|la|los|las|o|a|os|as|nela|nele)\s+)?(?:hizo|saco|retiro|"
    r"uso|toco|movio|fez|sacou|retirou|usou|mexeu|tirou)\b"
    r"|\b(?:mientras|enquanto)\s+(?:yo\s+|eu\s+)?(?:dormia|estaba dormid[oa]|estaba durmiendo|"
    r"estava dormindo|estaba de viaje|estava viajando|viajaba|viajava|estaba fuera|estava fora)\b"
)
# An unnamed party taking the money, anywhere in the message ("alguien sacó todo").
_RF2_UNNAMED_TAKE = _rx(
    r"\b" + _RF2_ACTOR + r"\s+(?:(?:me|nos|le|lhe)\s+)?(?:saco|retiro|robo|llevo|vacio|"
    r"transfirio|uso|gasto|sacou|retirou|roubou|levou|esvaziou|zerou|transferiu|usou|gastou|"
    r"tirou)\b"
    r"|" + _NOT_NEGATED + r"\b(?:me|nos)\s+(?:(?:lo|la|los|las)\s+)?(?:sacaron|robaron|retiraron|"
    r"llevaron|vaciaron|quitaron|sacaram|roubaram|retiraram|levaram|esvaziaram|tiraram)\b"
)
# A fee, debt, or seizure named after the cue is its cause, not an actor.
_RF2_CAUSE_AFTER = _rx(
    r"^(?:\s+[^\s,]+){0,4}?\s+(?:por|pelo|pela|pelos|pelas|con|com)\s+(?:(?:un|una|el|la|los|las|"
    r"um|uma|o|a|os|as|tantas|tantos)\s+)?(?:embargo|embargos|bloqueo|bloqueio|retencion|retencao|"
    r"comisiones|comision|intereses|cargos|cuotas|deudas|deuda|impuestos|juros|tarifas|taxas|"
    r"dividas|divida|parcelas)\b"
)
# 1. Passive drain of the customer's account, card, or funds with a non-"cuenta"
# subject, an adverbial, an inverted subject, or a reflexive passive ("fueron
# retirados todos mis ahorros", "minha poupança foi zerada").
_RF2_PASSIVE_AUX = (
    r"(?:fue|fueron|ha sido|han sido|habia sido|habian sido|foi|foram|tem sido|tinha sido|"
    r"tinham sido)"
)
_RF2_PASSIVE_PARTICIPLE = (
    r"(?:vaciad|limpiad|retirad|sacad|transferid|robad|desviad|drenad|esvaziad|zerad|limpad|"
    r"raspad|roubad|levad|resgatad|furtad)[oa]s?"
)
_RF2_DEGREE = r"(?:\s+(?:completamente|totalmente|por completo|integramente|ayer|anoche|ontem))?"
_RF2_PASSIVE_DEPLETION = (
    r"\b" + _RF2_OWN_OBJECT + r"(?:\s+[^\s,]+){0,3}?\s+" + _RF2_PASSIVE_AUX + _RF2_DEGREE + r"\s+"
    + _RF2_PASSIVE_PARTICIPLE + r"\b"
    + r"|\b" + _RF2_PASSIVE_AUX + r"\s+" + _RF2_PASSIVE_PARTICIPLE + r"\s+" + _RF2_OWN_OBJECT
    + r"|\bse\s+(?:retiraron|sacaron|llevaron|robaron|vaciaron|retiro|saco|llevo|robo|vacio)\s+"
    + _RF2_OWN_OBJECT
)
_RF2_NAMED_AGENT = _rx(
    r"^(?:\s+[^\s,]+){0,3}?\s+(?:por|pelo|pela)\s+(?:mi|mim|(?:mi|mis|meu|minha|meus|minhas)\s+"
    + _KIN + r"|(?:el|la|o|a)\s+(?:banco|empresa|tienda|loja|juzgado|gobierno)|banco)\b"
)
_RF2_UNNAMED_AGENT = _rx(r"^\s*(?:,\s*)?(?:por|pelo|pela)\s+" + _RF2_ACTOR + r"\b")
# Quasi-passive: the customer's account(s) found empty ("las dos cuentas que tengo
# amanecieron vacías", "minha conta amanheceu zerada").
_RF2_STATE_SUBJECT = (
    r"(?:" + _RF2_OWN_OBJECT + r"|(?:(?:las|as|mis|minhas|meus)\s+)?" + _RF2_QUANT + r"\s+"
    + _RF1Y_PLURAL_ACCOUNT + r"(?:\s+que\s+(?:tengo|tenemos|tenho|temos))?)"
)
_RF2_STATE_VERB = (
    r"(?:amanecio|amanecieron|aparecio|aparecieron|quedo|quedaron|amanheceu|amanheceram|"
    r"apareceu|apareceram|ficou|ficaram)"
)
_RF2_EMPTY = (
    r"(?:vaci[ao]s?|en\s+cero|vazi[ao]s?|zerad[ao]s?|limpi[ao]s?|sin\s+(?:saldo|fondos|dinero|"
    r"plata|nada|un peso|un centavo)|sem\s+(?:saldo|dinheiro|nada|um centavo))"
)
_RF2_DEPLETED_STATE = (
    r"\b" + _RF2_STATE_SUBJECT + r"(?:\s+[^\s,]+){0,2}?\s+" + _RF2_STATE_VERB + _RF2_DEGREE + r"\s+"
    + _RF2_EMPTY + r"\b"
)
# 2. Spanish clitic drain beyond "me la vaciaron": the clitic stands for money named
# earlier in the message ("tenía mis ahorros ... y me los sacaron").
_RF2_CLITIC_PLURAL = (
    r"(?:sacaron|robaron|vaciaron|limpiaron|retiraron|llevaron|quitaron|volaron|han sacado|"
    r"han robado|han vaciado|han limpiado|han retirado|han llevado|han quitado)"
)
_RF2_CLITIC_SINGULAR = (
    r"(?:saco|robo|vacio|limpio|retiro|llevo|quito|ha sacado|ha robado|ha vaciado|ha retirado|"
    r"ha llevado|ha quitado)"
)
_RF2_CLITIC_DRAIN = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+(?:lo|los|la|las)\s+" + _RF2_CLITIC_PLURAL + r"\b"
    + r"|\b" + _RF2_ACTOR + r"\s+(?:me|nos)\s+(?:lo|los|la|las)\s+" + _RF2_CLITIC_SINGULAR + r"\b"
)
_RF2_MONEY_REFERENT = (
    r"(?:ahorros|dinero|plata|platica|saldo|fondos|sueldo|salario|quincena|pension|aguinaldo|"
    r"cuenta|cuentas|tarjeta|tarjetas)"
)
_RF2_PHYSICAL_REFERENT = (
    r"(?:casa|laptop|computador|computadora|celular|telefono|carro|coche|moto|bicicleta|bolso|"
    r"cartera|billetera|mochila|maleta|reloj|nevera|heladera|alcancia|despensa|bodega|"
    r"habitacion|oficina|tienda|efectivo)"
)
_RF2_REFERENT = _rx(r"\b(?:" + _RF2_MONEY_REFERENT + r"|" + _RF2_PHYSICAL_REFERENT + r")\b")
_RF2_MONEY_REFERENT_RX = _rx(r"^" + _RF2_MONEY_REFERENT + r"$")
# 3. Ongoing, habitual, or present use of the customer's account or card ("llevan días
# usando mi tarjeta", "estão utilizando a minha conta pra ...", "um estranho usa minha
# conta para ..."), licensed by a financial purpose, purchases somewhere, or a lack of
# authorization.
_RF2_ONGOING_PLURAL = (
    r"(?:" + _PROGRESSIVE_PLURAL + r"|llevan|llevaban|vienen|venian|andaban|estaban|seguian|"
    r"continuan|continuaban|ficam|ficavam|vivem)"
)
_RF2_ONGOING_SINGULAR = (
    r"(?:" + _PROGRESSIVE_SINGULAR + r"|lleva|llevaba|viene|venia|andaba|seguia|vive)"
)
_RF2_DURATION = (
    r"(?:\s+(?:(?:unos|unas|varios|varias|uns|umas)\s+)?(?:dias|semanas|meses|"
    r"horas|tiempo|un tiempo|rato))?"
)
_RF2_GERUND = r"\s+(?:usando|utilizando|ocupando)"
_RF2_USE_TARGET = (
    r"\s+(?:(?:la|las|a|as|o|os|el|los)\s+)?(?:mi|mis|minha|minhas|meu|meus)\s+" + _RF1Y_ACCOUNT
)
_RF2_ONGOING_USE = (
    _NOT_NEGATED + r"\b" + _RF2_ONGOING_PLURAL + _RF2_DURATION + _RF2_GERUND + _RF2_USE_TARGET
    + r"|\b" + _RF2_ACTOR + r"\s+" + _RF2_ONGOING_SINGULAR + _RF2_DURATION + _RF2_GERUND
    + _RF2_USE_TARGET
    + r"|\b" + _RF2_ACTOR + r"\s+(?:usa|utiliza|usaba|utilizaba|usava|utilizava)" + _RF2_USE_TARGET
    + r"|" + _NOT_NEGATED + r"\b(?:usan|utilizan|usaban|utilizaban|usam|utilizam|usavam|"
    r"utilizavam)" + _RF2_USE_TARGET
)
_RF2_ITEM_OBJECT = (
    r"(?:\s+[^\s,]+){0,3}?\s+(?:" + _ITEM + r"|" + _PRODUCT_HEAD + r"|dinero|dinheiro|plata|grana|"
    r"fondos|fundos|valores|saldo)\b"
)
_RF2_PURPOSE = _rx(
    r"^(?:\s+[^\s,]+){0,3}?\s+(?:para|pra|a fin de|con el fin de|com o fim de)\s+(?:poder\s+)?"
    r"(?:(?:pagar|comprar|transferir|retirar|sacar|girar|gastar)\b"
    r"|(?:mandar|enviar|mover|movimentar|mexer|hacer|realizar|efectuar|fazer|efetuar|pedir|"
    r"solicitar|tirar|sacar)" + _RF2_ITEM_OBJECT + r")"
    r"|^(?:\s+[^\s,]+){0,3}?\s+(?:en|em|para comprar en|para comprar em)\s+(?:(?:unas|unos|umas|"
    r"uns|varias|varios)\s+)?(?:tiendas|comercios|lojas|sitios|sites|paginas|"
    r"establecimientos|estabelecimentos)\b"
)
# 4. A fronted lack of authorization or consent before an impersonal or unnamed taking
# or use of money, a card, or a payment ("Sin que yo diera permiso, sacaron el dinero
# de la cuenta", "Sem meu consentimento, usaram o cartão ...").
_RF2_FRONT = (
    r"(?:sin\s+que\s+(?:yo\s+)?(?:(?:lo|la|los|las|me)\s+)?(?:diera|diese|hiciera|autorizara|"
    r"aprobara|pidiera|supiera|solicitara|ordenara|permitiera|consintiera)(?:\s+(?:permiso|"
    r"autorizacion|consentimiento|ninguna orden|orden|nada))?"
    r"|sin\s+(?:haber(?:lo|la|los|las)?|habermelo)\s+(?:yo\s+)?(?:autorizado|aprobado|pedido|"
    r"solicitado|permitido)(?:\s+yo)?"
    r"|sin\s+(?:mi\s+)?(?:permiso|autorizacion|consentimiento|conocimiento|aprobacion)"
    r"|sem\s+(?:que\s+)?eu\s+(?:ter\s+|tivesse\s+)?(?:autorizado|autorizar|autorizasse|permitido|"
    r"permitir|permitisse|pedido|pedir|pedisse|saber|soubesse|dado|desse|aprovado|aprovar)"
    r"(?:\s+(?:permissao|autorizacao|nada))?"
    r"|sem\s+(?:a\s+|o\s+)?(?:minha\s+|meu\s+)?(?:permissao|autorizacao|consentimento|"
    r"conhecimento|aprovacao))"
)
_RF2_TAKE_PLURAL = (
    r"(?:sacaron|retiraron|transfirieron|llevaron|robaron|vaciaron|limpiaron|usaron|utilizaron|"
    r"gastaron|compraron|pagaron|hicieron|realizaron|movieron|mandaron|enviaron|desviaron|"
    r"han sacado|han retirado|han transferido|han usado|han hecho|sacaram|retiraram|transferiram|"
    r"levaram|roubaram|esvaziaram|zeraram|limparam|usaram|utilizaram|gastaram|compraram|pagaram|"
    r"fizeram|realizaram|movimentaram|mandaram|enviaram|tiraram|desviaram)"
)
_RF2_TAKE_SINGULAR = (
    r"(?:saco|retiro|transfirio|llevo|robo|vacio|limpio|uso|utilizo|gasto|compro|pago|hizo|"
    r"realizo|movio|mando|envio|desvio|sacou|retirou|transferiu|levou|roubou|esvaziou|zerou|"
    r"limpou|usou|utilizou|gastou|comprou|pagou|fez|realizou|movimentou|mandou|enviou|tirou|"
    r"desviou)"
)
_RF2_TAKE_TARGET = (
    r"\s+(?!(?:de|da|do|del|das|dos)\b)(?:[^\s,]+\s+){0,5}?(?:" + _RF2_FUNDS + r"|" + _ITEM
    + r"\b|(?:cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes)\b)"
)
_RF2_FRONTED_NON_CONSENT = (
    r"(?:^|(?<=, ))" + _RF2_FRONT + r"\s*,?\s+(?:"
    + _RF2_ACTOR + r"\s+(?:(?:me|nos|se|le|lhe)\s+)?" + _RF2_TAKE_SINGULAR
    + r"|(?:(?:me|nos|se|le|lhe)\s+)?" + _RF2_TAKE_PLURAL + r")\b" + _RF2_TAKE_TARGET
)
# 5. Money taken from several of the customer's cards or accounts ("me sacaron dinero de
# mis tres tarjetas").
_RF2_PLURAL_SOURCE = (
    r"(?:\s+(?:(?:todo|todos|tudo|el|la|los|las|o|a|os|as|un|una|um|uma)\s+)?(?:(?:poco|pouco|algo)"
    r"\s+(?:de\s+)?)?(?:dinero|plata|fondos|saldo|saldos|dinheiro|grana|ahorros|todo|tudo))?"
    r"\s+(?:de|desde|da|das|dos)\s+(?:(?:mis|minhas|meus)\s+(?:" + _RF2_QUANT + r"\s+)?"
    r"|(?:las|as|os)\s+" + _RF2_QUANT + r"\s+(?:(?:mis|minhas|meus)\s+)?)" + _RF1Y_PLURAL_ACCOUNT
)
_RF2_PLURAL_TAKE = (
    r"(?:sacaron|robaron|retiraron|quitaron|llevaron|han sacado|han robado|han retirado|"
    r"han quitado|sacaram|roubaram|tiraram|levaram|retiraram)"
)
_RF2_PLURAL_INSTRUMENT_DRAIN = (
    _NOT_NEGATED + r"\b(?:(?:me|nos|se)\s+)?" + _RF2_PLURAL_TAKE + _RF2_PLURAL_SOURCE
    + r"|\b" + _RF2_ACTOR + r"\s+(?:(?:me|nos|se)\s+)?(?:saco|robo|retiro|quito|llevo|sacou|roubou|"
    r"tirou|levou|retirou)" + _RF2_PLURAL_SOURCE
)
# 6. The customer left ruined or without money in the account ("me dejaron en la
# ruina", "quedé sin nada en la cuenta"), licensed by the account and a disowning,
# a lack of authorization, or an unnamed party's taking.
_RF2_RUIN = (
    r"(?:en\s+la\s+ruina|en\s+la\s+calle|en\s+bancarrota|en\s+la\s+lona|sin\s+nada|"
    r"pelad[oa]s?|limpi[oa]s?|na\s+miseria|na\s+rua|na\s+pindaiba|sem\s+nada|liso|lisa|"
    r"quebrad[oa]s?)"
)
_RF2_RUIN_IDIOM = (
    _NOT_NEGATED + r"\b(?:me|nos)\s+(?:dejaron|han dejado|deixaram)\s+" + _RF2_RUIN + r"(?=\W|$)"
    + r"|\b" + _RF2_ACTOR + r"\s+(?:me|nos)\s+(?:dejo|ha dejado|deixou)\s+" + _RF2_RUIN + r"(?=\W|$)"
)
_RF2_NO_MONEY_STATE = (
    r"\b(?:amaneci|me quede|quede|desperte|me encontre|estoy|amanheci|fiquei|acordei|estou)\s+"
    r"(?:sin|sem)\s+(?:(?:un|um|ni un|nem um|un solo|um so)\s+)?(?:peso|centavo|quinto|real|"
    r"euro|dolar|nada|plata|dinero|dinheiro|saldo|fondos|fundos)\b(?:\s+[^\s,]+){0,2}?\s+"
    r"(?:en|na|no)\s+(?:(?:la|a|o)\s+)?(?:(?:mi|minha|meu)\s+)?(?:cuenta|conta|tarjeta|cartao)\b"
)
_RF2_SIN = _rx(r"\bsin\b")
_RF2_INCOMING_DATIVE = _rx(
    r"\b(?:me|lhe)\s+(?:transfirieron|enviaron|mandaron|pagaron|depositaron|transferiram|enviaram|"
    r"mandaram|pagaram|depositaram)\b"
)
# 7. RF1Z over-escalation: the interface named after an adverb ("não reconheço mais o
# menu") is still the interface.
_RF2_INTERFACE_ADVERB = _rx(r"^\s*(?:mas|mais|ya|bien|direito|nada|para nada)\b")
_RF2_STRUCTURAL_NONRECOGNITION = _rx(
    r"^(?:no|nao)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:reconozco|reconheco|reconoci|"
    r"reconheci|identifico|identifiquei|identifique)$"
)

# ---------------------------------------------------------------- RF3 families
# RF2 fresh-confirmation miss shapes, read as one report shape rather than as more
# phrasings: a financial action by an unnamed, unknown, or impersonal party on the
# customer's own money, card, or account, in a message that says the customer did
# not do it, did not allow it, or does not know who did. The action is parsed from a
# verb lexicon in every tense and aspect; the object, the subject, and the licence
# are then checked separately, so a new wording of the same report needs no new cue.
def _rf3_alt(words: list[str] | tuple[str, ...]) -> str:
    return r"(?:" + "|".join(sorted(set(words), key=len, reverse=True)) + r")"


# Regular stems (normalized, without accents) of verbs that move, take, spend, or use
# money or a card. Spanish and Portuguese first-conjugation stems share the
# participle and the gerund; the finite endings differ.
_RF3_ES_AR = (
    "sac", "retir", "rob", "llev", "vaci", "limpi", "pas", "us", "utiliz", "ocup", "gast",
    "compr", "pag", "cobr", "carg", "desvi", "quit", "dren", "agot", "mand", "envi", "gir",
    "debit", "tom", "hurt", "vol",
)
_RF3_PT_AR = (
    "sac", "retir", "roub", "lev", "esvazi", "zer", "limp", "pass", "us", "utiliz", "gast",
    "compr", "pag", "cobr", "desvi", "tir", "furt", "rasp", "mand", "envi", "debit",
    "moviment", "dren", "tom",
)
_RF3_PLURAL_FORMS = (
    [s + e for s in _RF3_ES_AR for e in ("aron", "an", "aban")]
    + [s + e for s in _RF3_PT_AR for e in ("aram", "am", "avam")]
    + [
        "transfirieron", "transfieren", "transferian", "movieron", "mueven", "movian",
        "consumieron", "consumen", "consumian", "extrajeron", "extraen", "extraian",
        "hicieron", "hacen", "hacian", "vuelan", "descontaron", "descuentan", "descontaban",
        "transferiram", "transferem", "transferiam", "consumiram", "consomem", "consumiam",
        "fizeram", "fazem", "faziam", "descontaram", "descontam",
    ]
)
_RF3_SINGULAR_FORMS = (
    [s + e for s in _RF3_ES_AR for e in ("o", "a", "aba")]
    + [s + e for s in _RF3_PT_AR for e in ("ou", "a", "ava")]
    + [
        "transfirio", "transfiere", "transferia", "movio", "mueve", "movia", "consumio",
        "consume", "consumia", "extrajo", "extrae", "extraia", "hizo", "hace", "hacia", "vuela",
        "desconto", "descuenta", "descontaba", "transferiu", "transfere", "consumiu", "consome",
        "fez", "faz", "fazia", "descontou", "desconta",
    ]
)
_RF3_GERUNDS = (
    [s + "ando" for s in set(_RF3_ES_AR) | set(_RF3_PT_AR)]
    + [
        "transfiriendo", "moviendo", "consumiendo", "extrayendo", "haciendo", "descontando",
        "transferindo", "consumindo", "fazendo",
    ]
)
_RF3_INFINITIVES = (
    [s + "ar" for s in set(_RF3_ES_AR) | set(_RF3_PT_AR)]
    + ["transferir", "mover", "consumir", "extraer", "hacer", "descontar", "fazer"]
)
_RF3_PARTICIPLE = (
    _rf3_alt(
        [s + "ad" for s in set(_RF3_ES_AR) | set(_RF3_PT_AR)]
        + ["transferid", "movid", "consumid", "extraid", "descontad"]
    )
    + r"[oa]s?"
)
# Progressive, habitual, and continuative auxiliaries, with an optional duration
# ("llevan días usando", "vem pagando há dias").
_RF3_AUX_PLURAL = (
    r"(?:estan|estaban|estuvieron|han estado|siguen|seguian|vienen|venian|andan|andaban|"
    r"llevan|llevaban|continuan|continuaban|viven|estao|estavam|estiveram|tem estado|seguem|"
    r"seguiam|vem|vinham|andam|andavam|continuam|continuavam|vivem|ficam|ficavam)"
)
_RF3_AUX_SINGULAR = (
    r"(?:esta|estaba|estuvo|ha estado|sigue|seguia|viene|venia|anda|andaba|lleva|llevaba|"
    r"continua|continuaba|vive|vivia|estava|esteve|tem estado|segue|vem|vinha|andava|"
    r"continuava|fica|ficava)"
)
_RF3_DURATION = r"(?:\s+(?:(?:unos|unas|uns|umas|varios|varias)\s+)?(?:dias|semanas|meses|horas))?"
_RF3_AGAIN_PLURAL = (
    r"(?:volvieron a|vuelven a|empezaron a|comenzaron a|siguen a|voltaram a|voltam a|"
    r"comecaram a|continuam a)"
)
_RF3_AGAIN_SINGULAR = (
    r"(?:volvio a|vuelve a|empezo a|comenzo a|voltou a|volta a|comecou a|continua a)"
)
_RF3_PERFECT_PLURAL = r"(?:han|habian|tem|tinham)"
_RF3_PERFECT_SINGULAR = r"(?:ha|habia|tem|tinha)"
_RF3_CLITICS = r"(?:(?:me|nos|se|le|les|lhe|lhes|te)\s+)?(?:(?:lo|la|los|las|o|a|os|as)\s+)?"
_RF3_PLURAL_VERB = (
    r"(?:" + _RF3_AUX_PLURAL + _RF3_DURATION + r"\s+" + _rf3_alt(_RF3_GERUNDS)
    + r"|" + _RF3_AGAIN_PLURAL + r"\s+" + _rf3_alt(_RF3_INFINITIVES)
    + r"|" + _RF3_PERFECT_PLURAL + r"\s+" + _RF3_PARTICIPLE
    + r"|" + _rf3_alt(_RF3_PLURAL_FORMS) + r")"
)
_RF3_SINGULAR_VERB = (
    r"(?:" + _RF3_AUX_SINGULAR + _RF3_DURATION + r"\s+" + _rf3_alt(_RF3_GERUNDS)
    + r"|" + _RF3_AGAIN_SINGULAR + r"\s+" + _rf3_alt(_RF3_INFINITIVES)
    + r"|" + _RF3_PERFECT_SINGULAR + r"\s+" + _RF3_PARTICIPLE
    + r"|" + _rf3_alt(_RF3_SINGULAR_FORMS) + r")"
)
_RF3_ENCLITIC = r"(?:-(?:o|a|os|as|lo|la|los|las|no|na|nos|nas))?"
# An unknown, unnamed, or criminal party ("un desconocido", "um golpista", "alguien que
# no conozco"), beyond the RF1S and RF2 unnamed actors.
_RF3_ACTOR = (
    r"(?:(?:(?:un|una|um|uma|el|la|o|a|unos|unas|uns|umas|los|las|os|as)\s+)?"
    r"(?:desconocid[oa]s?|desconhecid[oa]s?|extran[oa]s?|estranh[oa]s?|golpistas?|"
    r"estafador(?:a|es|as)?|ladron(?:a|es|as)?|ladra[oe]s?|ladras?|hackers?|delincuentes?|"
    r"criminal(?:es)?|criminos[oa]s?|bandid[oa]s?|impostor(?:a|es|as)?|farsantes?|"
    r"timador(?:a|es|as)?|vigaristas?|tercer[oa]s?|terceir[oa]s?)"
    r"|alguien(?:\s+mas)?|alguem(?:\s+mais)?|gente|(?:una|uma)\s+persona|uma\s+pessoa"
    r"|(?:alguien|alguem|gente|(?:una|uma)\s+persona|uma\s+pessoa)\s+que\s+(?:yo\s+|eu\s+)?"
    r"(?:no|nao)\s+(?:conozco|conheco|soy|sou)(?:\s+(?:yo|eu))?)"
)
_RF3_THERE_IS_ACTOR = (
    r"(?:hay|habia|tem|tinha|ha)\s+" + _RF3_ACTOR + r"\s+" + _rf3_alt(_RF3_GERUNDS)
)
_RF3_ACTIVE_EVENT = (
    r"\b(?:" + _RF3_THERE_IS_ACTOR + r"|" + _RF3_CLITICS + r"(?:" + _RF3_PLURAL_VERB + r"|"
    + _RF3_SINGULAR_VERB + r")" + _RF3_ENCLITIC + r")(?=[\s,.;:!?]|$)"
)
_RF3_PLURAL_CUE = _rx(r"^" + _RF3_CLITICS + _RF3_PLURAL_VERB + _RF3_ENCLITIC + r"$")
_RF3_THERE_IS_CUE = _rx(r"^" + _RF3_THERE_IS_ACTOR + r"$")
_RF3_CUE_CLITIC = _rx(
    r"^(?:(?:me|nos|se|le|les|lhe|lhes|te)\s+)?(lo|la|los|las|o|a|os|as)\s"
    r"|-(?:o|a|os|as|lo|la|los|las|no|na|nos|nas)$"
)
_RF3_CUE_DATIVE_OWN = _rx(r"^(?:me|nos)\b")
_RF3_HACER = _rx(r"\b(?:hicieron|hacen|hacian|hizo|hace|hacia|haciendo|hacer|fizeram|fazem|"
                 r"faziam|fez|faz|fazia|fazendo|fazer)\b")
# Passive, reflexive-passive, state, and disappearance reports of the customer's
# money or account ("el saldo de mi tarjeta se esfumó", "sumiu todo o dinheiro da
# minha poupança", "la cuenta estaba vacía").
_RF3_PASSIVE_AUX = (
    r"(?:fue|fueron|ha sido|han sido|habia sido|habian sido|era|eran|foi|foram|tem sido|"
    r"tinha sido|tinham sido|era|eram)"
)
_RF3_ADVERB = (
    r"(?:\s+(?:completamente|totalmente|por completo|integramente|ayer|anoche|hoy|ontem|"
    r"hoje|todo|toda|todos|todas|tudo|completo|completa|enterito|enterita|inteiro|inteira))?"
)
_RF3_EMPTY = (
    r"(?:vaci[oa]s?|en\s+ceros?|a\s+cero|agotad[oa]s?|limpi[oa]s?|pelad[oa]s?|vazi[oa]s?|"
    r"zerad[oa]s?|a\s+zero|esgotad[oa]s?|limp[oa]s?|sin\s+(?:saldo|fondos|nada|un\s+peso|"
    r"un\s+centavo|un\s+quinto|plata|dinero)|sem\s+(?:saldo|nada|um\s+centavo|um\s+real|"
    r"um\s+tostao|dinheiro))"
)
_RF3_STATE_VERB = (
    r"(?:quedo|quedaron|amanecio|amanecieron|aparecio|aparecieron|esta|estan|estaba|estaban|"
    r"termino|terminaron|ficou|ficaram|amanheceu|amanheceram|apareceu|apareceram|estao|estava|"
    r"estavam|acabou|acabaram)"
)
_RF3_LEAVE = r"(?:(?:me|nos)\s+)?(?:(?:lo|la|los|las|a|as|o|os)\s+)?(?:dejaron|han dejado|dejo|ha dejado|deixaram|deixou)"
_RF3_DISAPPEAR = (
    r"(?:desaparecio|desaparecieron|se esfumo|se esfumaron|se evaporo|se evaporaron|volo|"
    r"volaron|se fue|se fueron|sumiu|sumiram|desapareceu|desapareceram|evaporou|evaporaram|"
    r"ya no esta|ya no estan|no queda nada|ya no queda nada|ya no hay nada|nao esta mais|"
    r"nao estao mais|ja nao esta|nao sobrou nada|nao tem mais nada|ya no aparece|"
    r"nao aparece mais)"
)
_RF3_PASSIVE_EVENT = (
    r"\b(?:" + _RF3_PASSIVE_AUX + _RF3_ADVERB + r"\s+" + _RF3_PARTICIPLE
    + r"|se\s+(?:(?:lo|la|los|las)\s+)?" + _rf3_alt(_RF3_SINGULAR_FORMS + _RF3_PLURAL_FORMS)
    + r"|" + _RF3_STATE_VERB + _RF3_ADVERB + r"\s+" + _RF3_EMPTY
    + r"|" + _RF3_LEAVE + r"(?:\s+[^\s,]+){0,4}?\s+" + _RF3_EMPTY
    + r"|" + _RF3_DISAPPEAR + r")(?=[\s,.;:!?]|$)"
)
_RF3_DISAPPEAR_CUE = _rx(r"^" + _RF3_DISAPPEAR + r"$")
_RF3_NOTHING_LEFT_CUE = _rx(
    r"^(?:no queda nada|ya no queda nada|ya no hay nada|nao sobrou nada|nao tem mais nada)$"
)
_RF3_ACTIVE_PASSIVE_CUE = _rx(r"^(?:" + _RF3_LEAVE + r"|se\s)")
# The customer's money, card, or account.
_RF3_QUANT = (
    r"(?:dos|tres|cuatro|cinco|ambas|ambos|todas|todos|varias|varios|algunas|algunos|duas|dois|"
    r"quatro|algumas|alguns)"
)
_RF3_INSTRUMENT = (
    r"(?:cuenta|cuentas|conta|contas|tarjeta|tarjetas|cartao|cartoes)\b"
    r"(?!\s+(?:de|da|do|del)\s+(?!(?:" + _OWN_ACCOUNT_TYPE
    + r"|credito|debito|corriente|corrente|ahorro|empresa|negocio|banco|la empresa|"
    r"el negocio|beneficio|nomina)\b))"
)
_RF3_FUNDS = (
    r"(?:dinero|plata|platica|lana|saldo|saldos|fondos|ahorros|sueldo|salario|nomina|quincena|"
    r"pension|aguinaldo|bono|liquidacion|cesantias?|cupo|limite|efectivo|dinheiro|grana|"
    r"poupanca|economias|fundos|rendimentos|decimo terceiro|fgts|aposentadoria|pensao|"
    r"reservas|valores|prima\s+(?:vacacional|de servicios|navidena))\b"
)
_RF3_OWN = r"(?:mi|mis|minha|minhas|meu|meus|nuestra|nuestro|nuestras|nuestros|nossa|nosso|nossas|nossos)"
_RF3_DET = (
    r"(?:(?:todo|toda|todos|todas|tudo)\s+)?(?:el|la|los|las|o|a|os|as|un|una|um|uma)"
)
_RF3_OWN_NP = (
    r"(?:(?:todo|toda|todos|todas|tudo)\s+)?(?:(?:el|la|los|las|o|a|os|as)\s+)?" + _RF3_OWN
    + r"\s+(?:" + _RF3_QUANT + r"\s+)?(?:" + _RF3_INSTRUMENT + r"|" + _RF3_FUNDS + r")"
)
_RF3_ARTICLE_NP = (
    r"(?:" + _RF3_DET + r"\s+(?:" + _RF3_QUANT + r"\s+)?|" + _RF3_QUANT + r"\s+)(?:"
    + _RF3_INSTRUMENT + r"|" + _RF3_FUNDS + r")"
)
_RF3_BARE_FUNDS = r"(?:dinero|plata|dinheiro|grana|saldo|fondos|fundos|ahorros|economias)\b"
_RF3_ALL = r"(?:todo|tudo|todo lo que tenia|tudo o que tinha|o que tinha|lo que tenia)\b"
_RF3_ITEMS = (
    r"(?:" + _ITEM + r"|contas|cuentas|facturas|faturas|boletos|suscripciones|assinaturas|"
    r"recargas|apuestas|apostas)\b"
)
_RF3_SOURCE = (
    r"(?:de|del|desde|da|do|das|dos|en|na|no|nas|nos|con|com|em|pelo|pela)\s+(?:(?:el|la|los|"
    r"las|o|a|os|as)\s+)?(?:" + _RF3_OWN + r"\s+)?(?:" + _RF3_QUANT + r"\s+)?" + _RF3_INSTRUMENT
)
_RF3_OBJECT = _rx(
    r"\b(?:" + _RF3_OWN_NP + r"|" + _RF3_ARTICLE_NP + r"|" + _RF3_BARE_FUNDS + r"|" + _RF3_ALL
    + r"|lo de|o do|o da|" + _RF3_SOURCE + r")"
)
_RF3_SOURCE_BEFORE = _rx(r"\b" + _RF3_OWN + r"\s+" + _RF3_INSTRUMENT)
_RF3_SOURCE_RX = _rx(r"\b" + _RF3_SOURCE)
_RF3_ITEM_RX = _rx(r"\b" + _RF3_ITEMS)
_RF3_OWN_NP_RX = _rx(r"\b" + _RF3_OWN_NP)
_RF3_OF_IT = _rx(r"^\s*del[ae]s?\b")
_RF3_REFLEXIVE_CUE = _rx(r"^se\s")
_RF3_PT_OBJECT_PRONOUN = _rx(r"^\s+(?:ele|ela|eles|elas)\b")
_RF3_THIRD_PARTY_DATIVE = _rx(r"^(?:le|les|lhe|lhes)\b")
_RF3_BARE_RELATIVE = _rx(r"(?:^|\s)que\s*$")
_RF3_NEEDS_INSTRUMENT = _rx(r"^(?:" + _RF3_ALL + r"|lo de|o do|o da)$")
# Money named without the customer's possessive is the customer's only with a dative
# ("me sacaron plata") or the customer's account or card as its source ("el saldo de
# la tarjeta"); a stranger taking cash from an ATM is not account activity.
_RF3_UNOWNED_FUNDS = _rx(r"^\s?(?:" + _RF3_DET + r"\s+(?:" + _RF3_QUANT + r"\s+)?)?" + _RF3_FUNDS)
_RF3_DESTINATION_BEFORE = _rx(r"\b(?:a|al|hacia|para|pra|ao|pro)\s*$")
_RF3_INSTRUMENT_RX = _rx(r"\b" + _RF3_INSTRUMENT)
_RF3_FINANCIAL_CONTEXT = _rx(
    r"\b(?:" + _RF3_INSTRUMENT + r"|" + _RF3_FUNDS + r"|cajero|caixa eletronico|atm|"
    r"banco|en efectivo)"
)
_RF3_SUBJECT_NP = _rx(
    r"\b(?:" + _RF3_OWN_NP + r"|" + _RF3_ARTICLE_NP + r"|" + _RF3_ALL + r"|lo de|o do|o da)"
)
# Money or a card named before a clitic or a subjectless passive is its antecedent; a
# physical object named after it is the antecedent instead.
_RF3_REFERENT = _rx(
    r"\b(?:" + _RF3_INSTRUMENT + r"|" + _RF3_FUNDS + r"|casa|laptop|computador|computadora|"
    r"celular|telefono|carro|coche|moto|bicicleta|bolso|cartera|billetera|mochila|maleta|reloj|"
    r"nevera|heladera|alcancia|despensa|bodega|habitacion|oficina|tienda|llaves|chaves|"
    r"carteira|bolsa|mochila|relogio|carro|moto|bicicleta|celular|telefone|notebook|"
    r"documentos|pasaporte|passaporte|bolsillo|bolso|paquete|pacote)\b"
)
_RF3_MONEY_REFERENT = _rx(r"^(?:" + _RF3_INSTRUMENT + r"|" + _RF3_FUNDS + r")")
# Someone else's money, card, or account.
_RF3_FOREIGN_OWNER = _rx(
    r"^\s*(?:de|del|da|do)\s+(?:mi|mis|meu|minha|meus|minhas|su|sus|seu|sua|el|la|o|a|un|una|"
    r"um|uma|otra|otro|outra|outro)\b(?!\s+(?:" + _RF3_INSTRUMENT + r"|banco|cajero))"
    r"|^\s*(?:ajen[oa]s?|alhei[oa]s?|dele|dela|deles|delas)\b"
)
# The customer did not do it, did not allow it, or does not know who did.
_RF3_FIRST_PERSON_ACTS = (
    r"(?:hice|he hecho|hecho|hago|saque|retire|use|utilice|ocupe|gaste|compre|pague|cargue|"
    r"pedi|he pedido|transferi|movi|toque|mande|envie|solicite|autorice|he autorizado|di|fui|"
    r"he ido|he estado|estuve|visito|uso|compro|pago|pido|cargo|frecuento|conozco|reconozco|"
    r"fiz|faco|saquei|retirei|usei|utilizei|gastei|comprei|paguei|pedi|transferi|mexi|"
    r"autorizei|dei|mandei|enviei|solicitei|estive|frequento|conheco|reconheco|peco|mexo|"
    r"tirei|movimentei|tenho feito|tenho usado)"
)
_RF3_DISOWNING = (
    r"\b(?:no|nao)\s+(?:fui|soy|sou|he sido|era|fue|foi)\s+(?:yo|eu)\b"
    r"|\b(?:yo|eu)\s+(?:no|nao)\s+(?:fui|soy|sou|era)\b"
    r"|\b(?:no|nao)\s+(?:son|sao|es|e)\s+(?:mias|mios|mia|mio|minhas|meus|minha|meu)\b"
    r"|\b(?:yo|eu)\s+(?:no|nunca|jamas|nao|jamais)\s+(?:(?:lo|la|los|las|le|les|me|o|a|os|as|"
    r"lhe|nada|ni)\s+){0,2}" + _RF3_FIRST_PERSON_ACTS + r"\b"
    r"|\b(?:que|donde|onde|en los que|en las que|nos quais|nas quais)\s+(?:yo\s+|eu\s+)?"
    r"(?:no|nunca|jamas|nao|jamais)\s+(?:(?:lo|la|los|las|le|les|me|o|a|os|as|lhe)\s+){0,2}"
    + _RF3_FIRST_PERSON_ACTS + r"\b"
    r"|\b(?:nunca|jamas|jamais)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?" + _RF3_FIRST_PERSON_ACTS
    + r"\b"
    r"|\b(?:no|nao)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:hice|he hecho|saque|retire|"
    r"autorice|he autorizado|pedi|he pedido|fiz|saquei|retirei|autorizei|usei|gastei|comprei|"
    r"paguei|mexi|reconozco|reconheco)\b"
)
_RF3_NON_CONSENT = (
    r"\b(?:sin|sem)\s+(?:(?:mi|minha|meu|el|la|a|o|ningun|ninguna|nenhum|nenhuma|previo|"
    r"previa|tu|su)\s+)*(?:permiso|autorizacion|consentimiento|conocimiento|aviso|aprobacion|"
    r"permissao|autorizacao|consentimento|conhecimento|aprovacao|aval|anuencia)\b"
    r"|\b(?:sin|sem)\s+que\s+(?:(?:yo|eu|nadie|ninguem|ninguno|ninguna|nenhum)\s+)?"
    r"(?:(?:me|lo|la|los|las|se|le|les|nos|o|a|os|as)\s+){0,2}(?:(?:autoriz|permit|consint|"
    r"consent|aprob|aprov|sup|soub|enter|pid|ped|solicit|orden|hic|fiz|us|"
    r"utiliz|compr|gast|retir|sac|consult|pregunt|pergunt|avis|perceb|mex|toc|mov)[a-z]*"
    r"(?:ara|iera|ase|iese|asse|esse|isse|aran|ieran|assem|essem|issem)|sepa|sepan|saiba|"
    r"diera|dieran|diese|desse|dessem|autorice|autorize|de|diga|pida|haya autorizado|"
    r"tenha autorizado)\b"
    r"|\bsin\s+(?:haber(?:le|les|lo|la|los|las|melo)?|habermelo)\s+(?:yo\s+)?(?:dado|autorizado|"
    r"aprobado|pedido|solicitado|permitido)\b"
    r"|\bsem\s+(?:que\s+)?(?:eu|ninguem)\s+(?:(?:me|lhe|o|a)\s+)?(?:ter\s+|tivesse\s+|tenha\s+|"
    r"haver\s+)?(?:dado|dar|desse|autoriz\w*|permit\w*|consent\w*|aprov\w*|ped\w*|saber|"
    r"soubesse|perceb\w*|mex\w*|us\w*|avis\w*|pergunt\w*|consult\w*|conhec\w*)"
    r"|\b(?:sin|sem)\s+(?:preguntarme|consultarme|avisarme|decirme|pedirme|me\s+(?:perguntar|"
    r"consultar|avisar|dizer|pedir))\b"
    r"|\ba\s+mis\s+espaldas\b|\bpelas\s+minhas\s+costas\b|\bpor\s+tras\s+de\s+mim\b"
    r"|\b(?:yo\s+|eu\s+)?(?:no|nunca|jamas|nao|jamais)\s+(?:(?:le|les|lhe|lhes)\s+)?"
    r"(?:di|dei|he dado|otorgue)\s+(?:(?:mi|minha|ningun|ninguna|nenhum|nenhuma)\s+)?"
    r"(?:permiso|autorizacion|consentimiento|permissao|autorizacao|consentimento|aval)\b"
    r"|\b(?:nadie|ninguem)\s+(?:(?:lo|la|o|a)\s+)?(?:autorizo|autorizou|aprobo|aprovou)\b"
    r"|\bautorizacion\s+de\s+nadie\b|\bautorizacao\s+de\s+ninguem\b"
)
_RF3_UNFAMILIAR = (
    r"\b(?:en|desde|de|em|no|na|do|da|para)\s+(?:el\s+|o\s+)?(?:extranjero|exterior|"
    r"otro pais|otra ciudad|otro estado|outro pais|outra cidade|outro estado)\b"
    r"|\b(?:sitios|sites|paginas|tiendas|lojas)\s+(?:estrangeir|extranjer)\w*"
)
# An unknown or criminal party named anywhere licenses the report; a bare "gente" or
# "una persona" does so only as the subject or agent of the action itself.
_RF3_STRONG_ACTOR = (
    r"(?:alguien|alguem|(?:un|una|um|uma|unos|unas|uns|umas)\s+(?:desconocid[oa]s?|"
    r"desconhecid[oa]s?|extran[oa]s?|estranh[oa]s?)|desconocidos|desconhecidos|golpistas?|"
    r"estafador(?:a|es|as)?|ladron(?:a|es|as)?|ladra[oe]s?|hackers?|delincuentes?|"
    r"criminos[oa]s?|bandid[oa]s?|impostor(?:a|es|as)?|timador(?:a|es|as)?|vigaristas?|"
    r"(?:no se|nao sei)\s+quien|nao sei quem)"
)
_RF3_LICENCE = _rx(
    _RF3_DISOWNING + r"|" + _RF3_NON_CONSENT + r"|\b" + _RF3_STRONG_ACTOR + r"\b"
)
# Use abroad or in another city licenses a report only when the customer does not say
# they were using the card themselves ("cuando uso la tarjeta en el exterior").
_RF3_UNFAMILIAR_RX = _rx(_RF3_UNFAMILIAR)
_RF3_SELF_USE = _rx(
    r"(?<!no )(?<!nao )(?<!nunca )\b(?:uso|use|usamos|pague|pagamos|compre|compramos|viaje|"
    r"viajo|viajamos|usei|usamos|paguei|comprei|viajei|viajamos)\b"
    r"|\b(?:estoy|estamos|estou|estamos)\s+(?:de\s+viaje|de\s+viagem|viajando)\b"
)
_RF3_THEFT_VERB = _rx(r"\b(?:rob|roub|hurt|furt)[a-z]*$")
_RF3_ACTOR_SLOT = _rx(
    r"\b" + _RF3_ACTOR + r"(?:\s+(?:mas|mais|tambien|tambem|ya|ja|otra vez|de nuevo|de novo|"
    r"anoche|ayer|ontem|hoje|hoy))?\s*$"
)
_RF3_UNKNOWN_AGENT = _rx(
    r"^(?:\s+[^\s,]+){0,4}?\s+(?:por|pelo|pela)\s+(?:" + _RF3_ACTOR
    + r"|(?:alguien|alguem)\s+que\s+(?:no|nao)\s+(?:soy|sou)\s+(?:yo|eu))\b"
)
_RF3_NAMED_AGENT = _rx(
    r"^(?:\s+[^\s,]+){0,4}?\s+(?:por|pelo|pela)\s+(?:mi|mim|(?:mi|mis|meu|minha|meus|minhas)\s+"
    r"[a-z]+|(?:el|la|o|a)\s+(?:banco|empresa|tienda|loja|juzgado|gobierno|governo)|banco|"
    r"(?:mi|mim)\s+(?:mism[oa]|mesm[oa]))\b"
)
# A person, the bank, or another institution named as the subject of the action.
_RF3_KNOWN_SUBJECT = _rx(
    r"(?<!de )(?<!del )(?<!da )(?<!do )(?<!dos )(?<!das )"
    r"\b(?:mi|mis|meu|minha|meus|minhas|su|sus|seu|sua|seus|suas|nuestro|nuestra|nuestros|"
    r"nuestras|nosso|nossa|nossos|nossas)\s+(?:" + _KIN + r"|socio|socia|socios|jefe|jefa|"
    r"contador|contadora|abogado|abogada|empleado|empleada|empleados|asistente|amigo|amiga|"
    r"amigos|amigas|vecino|vecina|vecinos|familia|familiares|chefe|advogado|advogada|"
    r"funcionario|funcionaria|vizinho|vizinha|parentes|empresa|banco|sobrino|sobrina|"
    r"sobrinho|sobrinha|primo|prima|cunado|cunada|cunhado|cunhada|nuera|yerno|nora|genro|"
    r"ex)\b"
    r"|\b(?:yo|eu|nosotros|nosotras|ellos|ellas|eles|elas|el|ella|ele|ela|usted|ustedes|voce|"
    r"voces)\s*(?:(?:me|nos|se|le|les|lhe|lo|la|los|las|o|a|os|as)\s+)*$"
    r"|(?<!de )(?<!da )(?<!do )\b(?:el|la|los|las|o|a|os|as)\s+(?:banco|bancos|empresa|tienda|"
    r"comercio|comercios|entidad|gobierno|juzgado|loja|lojas|governo|aseguradora|seguradora|"
    r"operadora|tiendas|supermercado|colegio|universidad|escola|faculdade)\b"
    r"(?:\s+[^\s,]+){0,2}?\s*$"
    r"|(?<!de )(?<!del )(?<!da )(?<!do )\b(?:banco|bancos)\b(?:\s+[^\s,]+){0,2}?\s*$"
)
# The customer allowed it, asked for it, or the money is arriving.
_RF3_PERMISSION = _rx(
    r"\bcon\s+(?:mi|el|su)\s+(?:permiso|autorizacion|consentimiento)\b"
    r"|\bcon\s+(?:permiso|autorizacion)\s+mi[oa]\b"
    r"|\bcom\s+(?:a\s+|o\s+)?(?:minha|meu)\s+(?:permissao|autorizacao|consentimento)\b"
    r"|\b(?:como|segun|conforme)\s+(?:yo\s+|eu\s+)?(?:lo\s+|o\s+)?(?:pedi|solicite|ordene|"
    r"acordamos|quedamos|combinamos|indique|solicitei|ordenei)\b"
    r"|\b(?:yo|eu)\s+(?:(?:le|les|lhe|lo|la|o|a)\s+)?(?:deje|deixei|autorice|autorizei|permiti)\b"
    r"|\b(?:le|les|lhe)\s+(?:di|dei)\s+(?:(?:mi|minha)\s+)?(?:permiso|permissao|autorizacion|"
    r"autorizacao)\b"
)
_RF3_INCOMING = _rx(
    r"^(?:me|nos|lhe)\s+(?:(?:lo|la|los|las|o|a|os|as)\s+)?(?:transfirieron|transfirio|"
    r"depositaron|deposito|pagaron|pago|mandaron|mando|enviaron|envio|abonaron|abono|"
    r"consignaron|consigno|giraron|giro|transferiram|transferiu|depositaram|depositou|"
    r"pagaram|pagou|mandaram|mandou|enviaram|enviou)\b"
)
_RF3_FOREIGN_DESTINATION = _rx(
    r"\b(?:a|hacia|para|pra)\s+(?:(?:una|uma|otra|outra)\s+)+(?:cuenta|conta|persona|"
    r"pessoa|tarjeta|cartao)\b|\b(?:a|para|pra)\s+(?:otra|outra|otro|outro)\b"
    r"|\bcuenta\s+(?:desconocida|ajena)|\bconta\s+(?:desconhecida|alheia)"
)
_RF3_TRANSFER_CUE = _rx(r"\b(?:transf|mand|envi|gir|pas|mov|deposit)")
_RF3_TO_MY_ACCOUNT = _rx(r"\b(?:a|hacia|para|pra|na)\s+(?:mi|minha)\s+(?:cuenta|conta)\b")
_RF3_FEE = _rx(
    r"\b(?:comision|comisiones|cuota|cuotas|seguro|anualidad|intereses|interes|tarifa|tarifas|"
    r"impuesto|impuestos|manejo|mensualidad|multa|multas|deuda|deudas|embargo|embargos|"
    r"prestamo|retencion|anuidade|juros|taxa|taxas|imposto|impostos|mensalidade|parcela|"
    r"parcelas|divida|dividas|emprestimo|financiamento|iof|retencao|bloqueio|bloqueo|"
    r"pension alimenticia|pensao alimenticia)\b"
)
# The customer's own action named as the cause ("porque pagué la tarjeta").
_RF3_SELF_CAUSE = _rx(
    r"\b(?:porque|ya que|pues|pois|por que|despues de que|depois que)\s+(?:yo\s+|eu\s+)?"
    r"(?:(?:la|lo|las|los|a|o|as|os)\s+)?(?:pague|cerre|retire|saque|gaste|compre|transferi|"
    r"pase|movi|use|invert|paguei|fechei|saquei|gastei|comprei|transferi|passei|usei|"
    r"investi)\w*\b"
)
_RF3_SI_PREFIX = _rx(r"\bsi(?=[a-z])")
_RF3_NEGATED_BEFORE = _rx(r"\b(?:no|nao|nunca|jamas|jamais|ni|nem)\s+$")
_RF3_DETERMINER_BEFORE = _rx(
    r"\b(?:un|una|el|la|los|las|um|uma|o|a|os|as|mi|mis|meu|minha|meus|minhas|este|esta|ese|"
    r"esa|esse|essa|del|do|da|de|ningun|ninguna|nenhum|nenhuma|cada|otro|otra|outro|outra|su|"
    r"seu|sua|al|ao|primer|primera|ultimo|ultima|algun|alguna|algum|alguma)\s+$"
)
# 7. RF1U F5 gap: card or account data used to subscribe to or contract a service.
_RF3_SUBSCRIPTION = (
    r"(?:\s+[^\s,]+){0,3}?\s+(?:para|pra|a fin de|con el fin de)\s+(?:poder\s+)?"
    r"(?:assinar|suscribir(?:se)?|subscribir(?:se)?|contratar|afiliar(?:se)?|inscribir(?:se)?|"
    r"registrar(?:se)?|cadastrar(?:-se)?|adquirir|abonar(?:se)?|activar|ativar|"
    r"(?:hacer|fazer)\s+(?:una|uma)\s+(?:suscripcion|assinatura))\b"
)
_RF3_DATA_SUBSCRIPTION = (
    r"\b(?:" + _PLURAL_USE + r"|" + _UNNAMED_ACTOR + r"\s+" + _SINGULAR_USE + r")\s+" + _DATA_NP
    + _RF3_SUBSCRIPTION
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
    # RF1U: an activity item characterized as fraudulent or unknown by the customer.
    (
        "fraud_characterization",
        _rx(r"\b" + _ITEM + _ITEM_MODIFIERS + r"\s+" + _FRAUD_ADJECTIVE + r"\b"),
    ),
    (
        "unknown_characterization",
        _rx(r"\b" + _ITEM + _ITEM_MODIFIERS + r"\s+" + _UNKNOWN_ADJECTIVE + r"\b"),
    ),
    # RF1U: an unnamed party did it, and the customer says it was not them.
    ("third_party_authorship", _rx(_THIRD_PARTY_AUTHORSHIP)),
    # RF1U: the customer's personal or card data used for financial activity.
    ("data_misuse", _rx(_DATA_MISUSE)),
    # RF1U: a scam the customer fell for, followed by activity in their name.
    ("scam_activity", _rx(_SCAM_VICTIM)),
    # RF1W: taken data used through a back-reference (U-P29 class).
    ("data_misuse_backref", _rx(_DATA_MISUSE_BACKREF)),
    # RF1W: impersonal activity using the customer's own account.
    ("account_use", _rx(_ACCOUNT_USE)),
    # RF1W: the customer's account drained by an impersonal or unnamed party.
    ("account_drain", _rx(_ACCOUNT_DRAIN)),
    # RF1Y: passive drain or use of the customer's account, card, or data.
    ("passive_account_misuse", _rx(_PASSIVE_ACCOUNT_MISUSE)),
    # RF1Y: Spanish double-clitic account drain ("me la vaciaron").
    ("double_clitic_drain", _rx(_DOUBLE_CLITIC_DRAIN)),
    # RF1Y: progressive or habitual use of the customer's account.
    ("progressive_account_use", _rx(_PROGRESSIVE_ACCOUNT_USE)),
    # RF1Y: fronted lack of permission with an article-only object.
    ("fronted_permission_drain", _rx(_FRONTED_PERMISSION_DRAIN)),
    # RF1Y: drain of a quantified plural of the customer's accounts.
    ("quantified_plural_drain", _rx(_QUANTIFIED_PLURAL_DRAIN)),
    # RF1Y: the customer left without money by an impersonal or unnamed party.
    ("no_money_drain", _rx(_NO_MONEY_DRAIN)),
    # RF2: passive drain of the customer's account, card, or funds (wider subjects).
    ("rf2_passive_depletion", _rx(_RF2_PASSIVE_DEPLETION)),
    # RF2: the customer's account(s) found empty (quasi-passive).
    ("rf2_depleted_state", _rx(_RF2_DEPLETED_STATE)),
    # RF2: Spanish clitic drain of money named earlier ("me los sacaron").
    ("rf2_clitic_drain", _rx(_RF2_CLITIC_DRAIN)),
    # RF2: ongoing, habitual, or present use of the customer's account or card.
    ("rf2_ongoing_use", _rx(_RF2_ONGOING_USE)),
    # RF2: fronted lack of authorization before a taking or use of money or a card.
    ("rf2_fronted_non_consent", _rx(_RF2_FRONTED_NON_CONSENT)),
    # RF2: money taken from several of the customer's cards or accounts.
    ("rf2_plural_instrument_drain", _rx(_RF2_PLURAL_INSTRUMENT_DRAIN)),
    # RF2: the customer left ruined by an impersonal or unnamed party.
    ("rf2_ruin_idiom", _rx(_RF2_RUIN_IDIOM)),
    # RF2: the customer left without money in the account.
    ("rf2_no_money_state", _rx(_RF2_NO_MONEY_STATE)),
    # RF3: an unnamed or impersonal party acting on the customer's money or card.
    ("rf3_active_event", _rx(_RF3_ACTIVE_EVENT)),
    # RF3: the customer's money or account drained, emptied, or gone (passive/state).
    ("rf3_passive_event", _rx(_RF3_PASSIVE_EVENT)),
    # RF3: card or account data used to subscribe to or contract a service.
    ("rf3_data_subscription", _rx(_RF3_DATA_SUBSCRIPTION)),
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
_RF1U_FAMILIES = frozenset(
    {
        "fraud_characterization",
        "unknown_characterization",
        "third_party_authorship",
        "data_misuse",
        "scam_activity",
    }
)
_RF1W_FAMILIES = frozenset({"data_misuse_backref", "account_use", "account_drain"})
_RF1Y_FAMILIES = frozenset(
    {
        "passive_account_misuse",
        "double_clitic_drain",
        "progressive_account_use",
        "fronted_permission_drain",
        "quantified_plural_drain",
        "no_money_drain",
    }
)
_RF2_FAMILIES = frozenset(
    {
        "rf2_passive_depletion",
        "rf2_depleted_state",
        "rf2_clitic_drain",
        "rf2_ongoing_use",
        "rf2_fronted_non_consent",
        "rf2_plural_instrument_drain",
        "rf2_ruin_idiom",
        "rf2_no_money_state",
    }
)
_RF2_STATE_FAMILIES = frozenset(
    {"rf2_passive_depletion", "rf2_depleted_state", "rf2_no_money_state"}
)
_RF3_FAMILIES = frozenset({"rf3_active_event", "rf3_passive_event", "rf3_data_subscription"})
_CHARACTERIZATION_FAMILIES = frozenset({"fraud_characterization", "unknown_characterization"})
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
        r"movimentacao|movimentacoes|"
        # RF1U: "movimento" is the Brazilian account-movement noun.
        r"movimento|movimentos)\b"
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

    if family in _RF3_FAMILIES:
        return _rf3_blocker(sentence, start, end, family, message_tail, message_head)
    if family in _RF2_FAMILIES:
        return _rf2_blocker(sentence, start, end, family, message_tail, message_head)
    if family in _RF1Y_FAMILIES:
        return _rf1y_blocker(sentence, start, end, family, message_tail, message_head)
    if family in _RF1W_FAMILIES:
        return _rf1w_blocker(sentence, start, end, family, message_tail, message_head)
    if family == "non_recognition" and _interface_nonrecognition(text, end):
        return "interface_nonrecognition"
    if family in _RF1U_FAMILIES:
        return _rf1u_blocker(sentence, start, end, family, message_tail, message_head)
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


def _rf1u_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF1U cue, or None when the cue is not tied to account activity."""

    text = sentences[index].text
    cue = text[start:end]
    if family in _CHARACTERIZATION_FAMILIES:
        # The characterized item is the anchor.
        return cue.split()[0]
    if family == "data_misuse":
        # The transaction or product the data was used for.
        item = _DATA_MISUSE_ITEM.search(cue)
        return item.group(0) if item else None
    if family == "scam_activity":
        # The licence is a transaction in the customer's name after the scam, in
        # the same sentence or the next one, itself outside question or
        # conditional scope ("caí en una estafa. ¿Si hicieron un pago ...?").
        candidates = [(end, sentences[index])] + [(0, s) for s in sentences[index + 1 : index + 2]]
        for position, candidate in candidates:
            for activity in _ACTIVITY_IN_MY_NAME.finditer(candidate.text, position):
                in_question = (
                    candidate.question_start is not None
                    and activity.start() >= candidate.question_start
                )
                before_activity = candidate.text[: activity.start()]
                if not (
                    in_question
                    or _sentence_protasis(before_activity)
                    or _CONDITIONAL_RIGHT_BEFORE.search(before_activity)
                ):
                    return activity.group(0)
        return None
    # third_party_authorship: the activity named in the sentence, or, for a short or
    # back-referring sentence, in the one before it.
    anchor = _anchor(text)
    if anchor is not None or index == 0:
        return anchor
    if len(text.split()) <= _ANAPHORIC_MAX_TOKENS or _BACK_REFERENCE.search(cue):
        return _anchor(sentences[index - 1].text)
    return None


def _characterization_frame(text: str, start: int, end: int) -> bool:
    """True when the characterized item is presented as the customer's actual item."""

    # U-P01: after a comma the clause prefix keeps its leading space, which the
    # start-anchored frames must not see ("Señores, es una compra fraudulenta").
    prefix = _clause_prefix(text, start).lstrip()
    return bool(
        _CHARACTERIZATION_COPULA.search(prefix)
        or _CHARACTERIZATION_PRESENCE.search(prefix)
        or _CHARACTERIZATION_CHARGE.search(prefix)
        or _CHARACTERIZATION_REPORT.search(prefix)
        or _CHARACTERIZATION_DEMONSTRATIVE.search(prefix)
        or (_CHARACTERIZATION_BARE_START.search(prefix) and _OWN_ACCOUNT_LOCATION.match(text[end:]))
    )


def _rf1u_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1U families.

    They take the RF1S scope checks (retraction, reported speech except a
    notification to the customer, hedges, resolution, permission, a protasis read
    through the cue, interrogative scope). Each family then adds the checks that
    keep it a report rather than advice, a plan, a delegation, or incoming money.
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
    if _PERMISSION_GRANTED.search(_NEGATED_GRANT.sub(" ", message_tail)):
        return "authorized_third_party"
    if _sentence_protasis(text[:end]):
        return "conditional_protasis"
    if sentence.question_start is not None and start >= sentence.question_start:
        return "interrogative_scope"
    if _DELEGATED_REQUEST.search(whole) or _RF1U_DELEGATION.search(whole):
        return "delegated_by_customer"

    if family in _CHARACTERIZATION_FAMILIES:
        if _CHARACTERIZATION_HEDGE.search(prefix):
            return "uncertainty_hedge"
        lead = text[: start - len(prefix)].rstrip(" ,(")
        if _LEAD_CLAUSE_HEDGE.match(lead[max(lead.rfind(","), lead.rfind("(")) + 1 :]):
            return "uncertainty_hedge"
        if _INFORMATIONAL_FRAME.search(before):
            return "informational_request"
        if _NEGATED_PRESENCE.search(prefix):
            return "negated_presence"
        if _GENERAL_TOPIC.search(text):
            return "general_topic"
        if _RELAYED_CLAIM.search(before):
            return "relayed_claim"
        if _RECOGNIZED_BEFORE.search(before):
            return "resolved_or_recognized"
        if _RECOGNIZED_ATTRIBUTION.search(message_tail) and not _UNAUTHORIZED_USE.search(whole):
            return "resolved_or_recognized"
        if (
            _INCOMING_ITEM.match(cue)
            and _INCOMING_RECEIPT.search(text)
            and not _FROM_MY_ACCOUNT.search(text)
        ):
            return "incoming_transfer"
        if not _characterization_frame(text, start, end):
            return "no_report_frame"
        return None
    if family == "data_misuse":
        if _NAMED_SUBJECT_BEFORE.search(prefix):
            return "named_actor"
        if _NOT_YET_BEFORE.search(before) or _NOT_YET_AFTER.search(after):
            return "not_yet_or_causal"
        return None
    if family == "scam_activity":
        if _NEAR_MISS_BEFORE.search(before):
            return "near_miss"
        return None
    # third_party_authorship
    if _NOT_YET_BEFORE.search(before):
        return "not_yet_or_causal"
    return None


def _rf1w_licensed_anchor(text: str, start: int, end: int, family: str) -> str | None:
    """Anchor for an RF1W cue, or None when the cue is not tied to account activity."""

    cue = text[start:end]
    if family == "account_drain":
        # The customer's own drained account is the anchor.
        return cue
    # data_misuse_backref, account_use: the transaction the data or account was used for.
    item = _DATA_MISUSE_ITEM.search(cue)
    return item.group(0) if item else None


def _rf1w_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1W families.

    They take the RF1U data-misuse checks: every shared RF1U check (retraction,
    reported speech, hedges, resolution, permission, protasis, interrogative scope,
    delegation), a named actor right before the cue, and a not-yet frame. An
    impersonal plural verb must also stand without an overt subject in its clause
    ("los cobros del banco me vaciaron ...", "meus pais fizeram ..."), as for RF1O
    intrusions; and money arriving through the account is not account misuse.
    """

    blocked = _rf1u_blocker(sentence, start, end, "data_misuse", message_tail, message_head)
    if blocked is not None:
        return blocked
    text = sentence.text
    cue = text[start:end]
    if not _UNNAMED_ACTOR_START.match(cue):
        before = text[:start]
        clause_start = 0
        for brk in _CLAUSE_BREAK.finditer(before):
            clause_start = brk.end()
        if not _INTRUSION_PLURAL_SLOT.search(before[clause_start:]):
            return "overt_subject"
    if family == "account_use" and _RF1W_INCOMING.search(text):
        return "incoming_transfer"
    return None


def _interface_nonrecognition(text: str, end: int) -> bool:
    """True when a non-recognition cue's object is the app or its interface only."""

    after = text[end:]
    # RF2: an adverb before the object ("não reconheço mais o menu").
    adverb = _RF2_INTERFACE_ADVERB.match(after)
    if adverb:
        after = after[adverb.end() :]
    if not _INTERFACE_OBJECT.match(after):
        return False
    stop = re.search(r"[,¿?]", after)
    obj = after[: stop.start()] if stop else after
    return not _INTERFACE_FINANCIAL.search(_INTERFACE_LABEL.sub(" ", obj))


def _rf1y_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF1Y cue, or None when its licence is missing."""

    text = sentences[index].text
    cue = text[start:end]
    message = " ".join(s.text for s in sentences)
    if family == "passive_account_misuse":
        after = text[end:]
        if _RF1Y_UNNAMED_AGENT.match(after) or _RF1Y_DISOWNED.search(message):
            return cue
        return None
    if family == "double_clitic_drain":
        head = " ".join([s.text for s in sentences[:index]] + [text[:start]])
        if _RF1Y_BANKING_CONTEXT.search(message) and not _RF1Y_NONFINANCIAL_REFERENT.search(head):
            return cue
        return None
    if family == "no_money_drain":
        if (
            _UNNAMED_ACTOR_START.match(cue)
            or _RF1Y_ACCOUNT_CONTEXT.search(message)
            or _RF1Y_DISOWNED.search(message)
        ):
            return cue
        return None
    return cue


def _rf1y_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF1Y families.

    Active families take the RF1W checks (every shared RF1U check, a named actor, a
    not-yet frame, an impersonal verb without an overt subject, and incoming money
    for account use). The passive family has no subject slot to check; it takes the
    shared RF1U checks and blocks a named agent. A fee or expense named after the
    verb is a cause, not an actor.
    """

    after = sentence.text[end:]
    # Inside an RF1Y cue, "sin" is the cue's own no-money or no-permission preposition,
    # never a conditional; the shared protasis pattern also reads "si" inside "sin", so
    # that token is masked (same length) for these families' checks only.
    sentence = _Sentence(
        text=sentence.text[:start] + _RF1Y_CUE_SIN.sub("s_n", sentence.text[start:end])
        + sentence.text[end:],
        question_start=sentence.question_start,
    )
    if family == "passive_account_misuse":
        blocked = _rf1u_blocker(sentence, start, end, "data_misuse", message_tail, message_head)
        if blocked is not None:
            return blocked
        if _RF1Y_NAMED_AGENT.match(after):
            return "named_actor"
        return None
    rf1w_family = "account_use" if family == "progressive_account_use" else "account_drain"
    blocked = _rf1w_blocker(sentence, start, end, rf1w_family, message_tail, message_head)
    if blocked is not None:
        return blocked
    if _RF1Y_POST_VERBAL_CAUSE.match(after):
        return "post_verbal_cause"
    return None


def _rf2_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF2 cue, or None when its licence is missing."""

    text = sentences[index].text
    cue = text[start:end]
    message = " ".join(s.text for s in sentences)
    if family in ("rf2_passive_depletion", "rf2_depleted_state", "rf2_no_money_state"):
        # A depleted account or state needs the customer's disowning, a lack of
        # authorization, an unnamed agent, or an unnamed party's taking.
        if family == "rf2_passive_depletion" and _RF2_UNNAMED_AGENT.match(text[end:]):
            return cue
        if _RF2_DISOWNED.search(message) or _RF2_UNNAMED_TAKE.search(message):
            return cue
        return None
    if family == "rf2_clitic_drain":
        # The clitic's antecedent is the last money or physical noun before it.
        head = " ".join([s.text for s in sentences[:index]] + [text[:start]])
        referents = _RF2_REFERENT.findall(head)
        if referents and _RF2_MONEY_REFERENT_RX.match(referents[-1]):
            return cue
        return None
    if family == "rf2_ongoing_use":
        if _RF2_PURPOSE.match(text[end:]) or _RF2_DISOWNED.search(message):
            return cue
        return None
    if family == "rf2_ruin_idiom":
        if _RF1Y_ACCOUNT_CONTEXT.search(message) and (
            _RF2_DISOWNED.search(message) or _RF2_UNNAMED_TAKE.search(message)
        ):
            return cue
        return None
    # rf2_fronted_non_consent, rf2_plural_instrument_drain: the cue carries its own
    # lack of consent or the customer's instruments.
    return cue


def _rf2_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF2 families.

    Every family takes the shared RF1U checks (retraction, reported speech, hedges,
    resolution, permission, protasis, interrogative scope, delegation, a named actor
    right before the cue, a not-yet frame) and blocks a fee, debt, or seizure named
    as the cause. The passive and state families block a named or self agent. The
    active families need an unnamed actor or no overt subject, as for RF1W, and
    account use or taking cannot be money arriving to the customer.
    """

    after = sentence.text[end:]
    # "sin" before the cue end is a no-permission or no-money preposition, never a
    # conditional; the shared protasis pattern also reads "si" inside "sin", so that
    # token is masked (same length) for these families' checks only.
    sentence = _Sentence(
        text=_RF2_SIN.sub("s_n", sentence.text[:end]) + sentence.text[end:],
        question_start=sentence.question_start,
    )
    blocked = _rf1u_blocker(sentence, start, end, "data_misuse", message_tail, message_head)
    if blocked is not None:
        return blocked
    if _RF2_CAUSE_AFTER.match(after) or _RF1Y_POST_VERBAL_CAUSE.match(after):
        return "post_verbal_cause"
    if family in _RF2_STATE_FAMILIES:
        if _RF2_NAMED_AGENT.match(after):
            return "named_actor"
        return None
    text = sentence.text
    cue = text[start:end]
    if family != "rf2_fronted_non_consent" and not _RF2_ACTOR_START.match(cue):
        before = text[:start]
        clause_start = 0
        for brk in _CLAUSE_BREAK.finditer(before):
            clause_start = brk.end()
        slot = before[clause_start:]
        if not (_INTRUSION_PLURAL_SLOT.search(slot) or _RF2_PLURAL_SLOT.search(slot)):
            return "overt_subject"
    if family in ("rf2_ongoing_use", "rf2_fronted_non_consent") and _RF1W_INCOMING.search(text):
        return "incoming_transfer"
    if family == "rf2_fronted_non_consent" and (
        _RF2_INCOMING_DATIVE.search(cue) or _TO_MY_ACCOUNT.search(text[start:])
    ):
        return "incoming_transfer"
    return None


def _rf3_clause_slot(text: str, start: int) -> str:
    """The clause before an RF3 cue, reaching back over a bare relative "que"."""

    before = text[:start]
    breaks = [brk for brk in _CLAUSE_BREAK.finditer(before)]
    clause_start = breaks[-1].end() if breaks else 0
    slot = before[clause_start:]
    if _RF3_BARE_RELATIVE.search(slot) and breaks:
        previous = breaks[-2].end() if len(breaks) >= 2 else 0
        slot = before[previous:]
    return slot


def _rf3_object(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """The customer's money, card, or account the RF3 action applies to, if any."""

    text = sentences[index].text
    cue = text[start:end]
    message = " ".join(s.text for s in sentences)
    head = " ".join([s.text for s in sentences[:index]] + [text[:start]])
    brk = _CLAUSE_BREAK.search(text, end)
    window = text[end : brk.start() if brk else len(text)]
    window = " ".join(window.split()[:8])
    if family == "rf3_active_event" and _RF3_HACER.search(cue):
        # "hacer compras / fazer pagamentos" needs the item and the customer's card or
        # account as its instrument ("compras con mi tarjeta", "cargos en la tarjeta").
        item = _RF3_ITEM_RX.search(window)
        if item and _RF3_SOURCE_RX.search(window[item.end() :]):
            return item.group(0)
        if item and _RF3_SOURCE_BEFORE.search(head):
            return item.group(0)
        return None
    found = None
    for candidate in _RF3_OBJECT.finditer(" " + window):
        if _RF3_DESTINATION_BEFORE.search((" " + window)[: candidate.start()]):
            continue
        if _RF3_UNOWNED_FUNDS.match(candidate.group(0)) and not (
            _RF3_CUE_DATIVE_OWN.match(cue)
            or _RF3_SOURCE_RX.search(window[candidate.end() - 1 :])
        ):
            continue
        found = candidate
        break
    if found is not None:
        word = found.group(0)
        owner = _RF3_FOREIGN_OWNER.match(window[found.end() - 1 :])
        if owner is not None:
            # "dele / dela" may stand for the card or account named just before.
            referents = _RF3_REFERENT.findall(head)
            if not (
                _RF3_OF_IT.match(owner.group(0))
                and referents
                and _RF3_MONEY_REFERENT.match(referents[-1])
            ):
                return None
        if _RF3_NEEDS_INSTRUMENT.match(word):
            if _RF3_INSTRUMENT_RX.search(window) or _RF3_INSTRUMENT_RX.search(message):
                return word
            return None
        return word
    if family == "rf3_passive_event":
        # A passive, state, or disappearance names its subject before the cue in the
        # clause, or names an unknown agent after it with money or an account in view.
        slot = _rf3_clause_slot(text, start)
        subject = None
        for subject in _RF3_SUBJECT_NP.finditer(slot):
            pass
        if subject is not None:
            if _RF3_NEEDS_INSTRUMENT.match(subject.group(0)) and not _RF3_INSTRUMENT_RX.search(
                message
            ):
                return None
            return subject.group(0)
        if _RF3_UNKNOWN_AGENT.match(text[end:]) and _RF3_FINANCIAL_CONTEXT.search(message):
            return "agent"
        if _RF3_NOTHING_LEFT_CUE.match(cue) and _RF3_FINANCIAL_CONTEXT.search(text):
            return "context"
        if _RF3_DISAPPEAR_CUE.match(cue) or _RF3_REFLEXIVE_CUE.match(cue):
            # "se fue", "voló", "se llevaron" need their own money subject: people
            # leave and take things too.
            return None
    # A clitic stands for the last money, card, or physical object named before it.
    clitic = _RF3_CUE_CLITIC.search(cue)
    if clitic is None:
        clitic = _RF3_PT_OBJECT_PRONOUN.match(text[end:])
    if clitic is not None or family == "rf3_passive_event":
        referents = _RF3_REFERENT.findall(head)
        if referents and _RF3_MONEY_REFERENT.match(referents[-1]):
            return referents[-1]
    return None


def _rf3_licensed_anchor(
    sentences: list[_Sentence], index: int, start: int, end: int, family: str
) -> str | None:
    """Anchor for an RF3 cue, or None when its object or licence is missing."""

    text = sentences[index].text
    cue = text[start:end]
    message = " ".join(s.text for s in sentences)
    before = text[:start]
    if _RF3_NEGATED_BEFORE.search(before):
        return None
    if family == "rf3_data_subscription":
        # The data and the service are the cue; RF1U data misuse needs no other licence.
        return cue
    if _RF3_DETERMINER_BEFORE.search(before):
        return None
    if family == "rf3_active_event" and not (
        _RF3_PLURAL_CUE.match(cue) or _RF3_THERE_IS_CUE.match(cue)
    ):
        # A singular action needs an unknown or unnamed actor as its subject.
        if not _RF3_ACTOR_SLOT.search(_rf3_clause_slot(text, start)):
            return None
    if _rf3_object(sentences, index, start, end, family) is None:
        return None
    if _RF3_LICENCE.search(message) or (
        _RF3_UNFAMILIAR_RX.search(message) and not _RF3_SELF_USE.search(message)
    ):
        return cue
    if family == "rf3_active_event" and (
        _RF3_THERE_IS_CUE.match(cue)
        or _RF3_ACTOR_SLOT.search(_rf3_clause_slot(text, start))
        or _RF3_THEFT_VERB.search(cue)
    ):
        # An unknown actor, or a verb that itself means taking without consent.
        return cue
    if family == "rf3_passive_event" and _RF3_UNKNOWN_AGENT.match(text[end:]):
        return cue
    return None


def _rf3_blocker(
    sentence: _Sentence,
    start: int,
    end: int,
    family: str,
    message_tail: str,
    message_head: str,
) -> str | None:
    """Scope checks for the RF3 families.

    Every family takes the shared RF1U checks (retraction, reported speech, hedges,
    resolution, permission, protasis, interrogative scope, delegation). An action
    named for someone else ("le vaciaron"), by a known person, the bank, or another
    institution, with the customer's permission, as money arriving, or as a fee, debt,
    or the customer's own payment stays outside.
    """

    original = sentence.text
    after = original[end:]
    cue = original[start:end]
    # The shared protasis pattern also reads "si" at the start of a longer word ("sin",
    # "sigue", "sitios"); as for RF2's "sin", that token is masked (same length) for
    # these families' checks only.
    sentence = _Sentence(
        text=_RF3_SI_PREFIX.sub("s_", original[:end]) + original[end:],
        question_start=sentence.question_start,
    )
    shared = "data_misuse" if family == "rf3_data_subscription" else "third_party_authorship"
    blocked = _rf1u_blocker(sentence, start, end, shared, message_tail, message_head)
    if blocked is not None:
        return blocked
    if family == "rf3_data_subscription":
        return None
    whole = message_head + " " + cue + " " + message_tail
    if _RF3_PERMISSION.search(_NEGATED_GRANT.sub(" ", whole)):
        return "authorized_third_party"
    if _RF3_THIRD_PARTY_DATIVE.match(cue):
        return "third_party_dative"
    slot = _rf3_clause_slot(original, start)
    # A passive, state, or disappearance names the money, not the actor, before it;
    # "dejar" and a reflexive "se llevó" are actions whose subject comes first.
    active = family == "rf3_active_event" or _RF3_ACTIVE_PASSIVE_CUE.match(cue)
    if active and _RF3_KNOWN_SUBJECT.search(slot) and not _RF3_ACTOR_SLOT.search(slot):
        return "named_actor"
    if family == "rf3_passive_event" and _RF3_NAMED_AGENT.match(after):
        return "named_actor"
    if _RF2_CAUSE_AFTER.match(after) or _RF1Y_POST_VERBAL_CAUSE.match(after):
        return "post_verbal_cause"
    brk = _CLAUSE_BREAK.search(original, end)
    clause = original[start : brk.start() if brk else len(original)]
    if _RF3_FEE.search(clause) or _RF3_FEE.search(slot):
        return "known_charge"
    if _RF3_SELF_CAUSE.search(original) and not _RF3_LICENCE.search(original[start:]):
        return "self_explained"
    if _RF3_INCOMING.match(cue) and not (
        _RF3_FOREIGN_DESTINATION.search(after) or _RF3_OWN_NP_RX.search(after)
    ):
        return "incoming_transfer"
    if _RF3_TRANSFER_CUE.search(cue) and _RF3_TO_MY_ACCOUNT.search(after):
        return "incoming_transfer"
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
    # RF2: non-recognition of the app, its version, or its interface only ("depois da
    # atualização não reconheço mais o menu") is not a disowned transaction.
    if _RF2_STRUCTURAL_NONRECOGNITION.match(span):
        clause = _normalize(text[source_end : sentence_end.start() if sentence_end else None])
        if _interface_nonrecognition(" " + clause, 0):
            return "interface_nonrecognition"
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
                    7
                    if family in _RF3_FAMILIES
                    else 6
                    if family in _RF2_FAMILIES
                    else 5
                    if family in _RF1Y_FAMILIES
                    else 4
                    if family in _RF1W_FAMILIES
                    else 3
                    if family in _RF1U_FAMILIES
                    else 2
                    if family in _RF1S_FAMILIES
                    else int(family in _RF1Q_FAMILIES),
                    match.start(),
                    match.end(),
                )
                if span in seen:
                    continue
                seen.add(span)
                if family in _RF3_FAMILIES:
                    anchor = _rf3_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                    # RF3 cues are lexicon matches; without the customer's money or
                    # card and a licence the match is not an RF3 cue occurrence.
                    if anchor is None:
                        continue
                elif family in _RF2_FAMILIES:
                    anchor = _rf2_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                elif family in _RF1Y_FAMILIES:
                    anchor = _rf1y_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                elif family in _RF1W_FAMILIES:
                    anchor = _rf1w_licensed_anchor(
                        sentence.text, match.start(), match.end(), family
                    )
                elif family in _RF1U_FAMILIES:
                    anchor = _rf1u_licensed_anchor(
                        sentences, index, match.start(), match.end(), family
                    )
                elif family in _RF1S_FAMILIES:
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
