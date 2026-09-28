from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import unicodedata
from typing import Iterable


_TXID_RE = re.compile(
    r"(?i)\bdemo(?:[-\s]*)(es|pt)(?:[-\s]*)(\d{4})\b"
)

_WORD_RE = re.compile(r"[\w]+(?:[\'’][\w]+)*", re.UNICODE)

_STRUCTURAL_PUNCTUATION = frozenset(".?!;:,¿¡-—–")


class PredicateFamily(str, Enum):
    PERFORM = "perform"
    ORIGINATE = "originate"
    AUTHORIZE = "authorize"
    GIVE_PERMISSION = "give_permission"
    RECOGNIZE = "recognize"
    USE_ACCESS = "use_access"
    COMPROMISE = "compromise"


class SelfRole(str, Enum):
    SUBJECT = "self_subject"
    AGENT = "self_agent"
    SOURCE = "self_source"
    POSSESSOR = "self_possessor"
    DATIVE = "self_dative"


class LexicalTag(str, Enum):
    ACTIVITY = "activity"
    INSTRUMENT = "instrument"
    SELF = "self"
    THIRD_PARTY = "third_party"
    NEGATOR = "negator"
    NEG_QUANTIFIER = "neg_quantifier"
    COORD_NEGATION = "coord_negation"
    OWNERSHIP = "ownership"
    AUTH_NOUN = "auth_noun"
    FRAUD_MARKER = "fraud_marker"
    DESCRIPTOR_NOUN = "descriptor_noun"
    SECURITY_INFO = "security_info"
    UNCERTAINTY = "uncertainty"
    CONDITIONAL = "conditional"
    RETRACTION = "retraction"
    AFFIRM_SELF = "affirm_self"
    TXID = "txid"
    QUESTION_OPEN = "question_open"
    QUESTION_CLOSE = "question_close"
    CONTRAST = "contrast"


@dataclass(frozen=True)
class Token:
    surface: str
    normalized: str
    start: int
    end: int
    had_acute: bool
    is_txid: bool = False
    txid_language: str | None = None
    txid_digits: str | None = None


@dataclass(frozen=True)
class ClauseSegment:
    index: int
    token_start: int
    token_end: int
    source_start: int
    source_end: int


@dataclass(frozen=True)
class PredicateForm:
    family: PredicateFamily
    lemma: str
    language: str
    person: int | None
    number: str | None
    tense_aspect: str
    mood: str
    voice: str
    accent_required: bool


@dataclass(frozen=True)
class PredicateMatch:
    form: PredicateForm
    token_start: int
    token_end: int
    accent_ambiguous: bool = False


@dataclass(frozen=True)
class SelfEvidence:
    role: SelfRole
    token_start: int
    token_end: int
    implicit_from_predicate: bool = False
    ambiguous: bool = False


@dataclass(frozen=True)
class FoundationAnalysis:
    tokens: tuple[Token, ...]
    clauses: tuple[ClauseSegment, ...]
    predicates: tuple[PredicateMatch, ...]
    tags: tuple[frozenset[LexicalTag], ...]
    self_evidence: tuple[SelfEvidence, ...]


def _strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _has_acute(text: str) -> bool:
    decomposed = unicodedata.normalize("NFD", text)
    return "\u0301" in decomposed


def _normalize_word(text: str) -> str:
    return _strip_diacritics(text).replace("’", "'")


def tokenize_with_source(text: str) -> tuple[Token, ...]:
    """Tokenize while retaining exact source offsets and accent metadata."""

    tokens: list[Token] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue

        txid_match = _TXID_RE.match(text, index)
        if txid_match is not None:
            surface = txid_match.group(0)
            tokens.append(
                Token(
                    surface=surface,
                    normalized="<txid>",
                    start=index,
                    end=txid_match.end(),
                    had_acute=False,
                    is_txid=True,
                    txid_language=txid_match.group(1).lower(),
                    txid_digits=txid_match.group(2),
                )
            )
            index = txid_match.end()
            continue

        char = text[index]
        if char in _STRUCTURAL_PUNCTUATION:
            normalized = "-" if char in {"—", "–"} else char
            tokens.append(
                Token(
                    surface=char,
                    normalized=normalized,
                    start=index,
                    end=index + 1,
                    had_acute=False,
                )
            )
            index += 1
            continue

        word_match = _WORD_RE.match(text, index)
        if word_match is not None:
            surface = word_match.group(0)
            tokens.append(
                Token(
                    surface=surface,
                    normalized=_normalize_word(surface),
                    start=index,
                    end=word_match.end(),
                    had_acute=_has_acute(surface),
                )
            )
            index = word_match.end()
            continue

        tokens.append(
            Token(
                surface=char,
                normalized=_normalize_word(char),
                start=index,
                end=index + 1,
                had_acute=_has_acute(char),
            )
        )
        index += 1

    return tuple(tokens)


def _is_numeric_punctuation(text: str, token: Token) -> bool:
    if token.surface not in {".", ","}:
        return False
    before = text[token.start - 1] if token.start > 0 else ""
    after = text[token.end] if token.end < len(text) else ""
    return before.isdigit() and after.isdigit()


def _has_following_whitespace(text: str, token: Token) -> bool:
    return token.end >= len(text) or text[token.end].isspace()


def _is_whitespace_adjacent_dash(text: str, token: Token) -> bool:
    if token.normalized != "-":
        return False
    before_ok = token.start == 0 or text[token.start - 1].isspace()
    after_ok = token.end == len(text) or text[token.end].isspace()
    return before_ok and after_ok


def _is_primary_boundary(text: str, token: Token) -> bool:
    if token.normalized in {"?", "!", ";"}:
        return True
    if token.normalized == ".":
        if _is_numeric_punctuation(text, token):
            return False
        return _has_following_whitespace(text, token)
    if token.normalized == "-":
        return _is_whitespace_adjacent_dash(text, token)
    return False


def _form(
    family: PredicateFamily,
    lemma: str,
    language: str,
    person: int | None,
    number: str | None,
    tense_aspect: str,
    mood: str,
    surface: str,
    *,
    voice: str = "active",
) -> tuple[str, PredicateForm]:
    return (
        _normalize_word(surface),
        PredicateForm(
            family=family,
            lemma=lemma,
            language=language,
            person=person,
            number=number,
            tense_aspect=tense_aspect,
            mood=mood,
            voice=voice,
            accent_required=_has_acute(surface),
        ),
    )


_ES_REGULAR_ENDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "ar": {
        "present": ("o", "as", "a", "amos", "áis", "an"),
        "preterite": ("é", "aste", "ó", "amos", "asteis", "aron"),
        "imperfect": ("aba", "abas", "aba", "ábamos", "abais", "aban"),
        "present_subjunctive": ("e", "es", "e", "emos", "éis", "en"),
    },
    "er": {
        "present": ("o", "es", "e", "emos", "éis", "en"),
        "preterite": ("í", "iste", "ió", "imos", "isteis", "ieron"),
        "imperfect": ("ía", "ías", "ía", "íamos", "íais", "ían"),
        "present_subjunctive": ("a", "as", "a", "amos", "áis", "an"),
    },
    "ir": {
        "present": ("o", "es", "e", "imos", "ís", "en"),
        "preterite": ("í", "iste", "ió", "imos", "isteis", "ieron"),
        "imperfect": ("ía", "ías", "ía", "íamos", "íais", "ían"),
        "present_subjunctive": ("a", "as", "a", "amos", "áis", "an"),
    },
}

_PT_REGULAR_ENDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "ar": {
        "present": ("o", "as", "a", "amos", "ais", "am"),
        "preterite": ("ei", "aste", "ou", "amos", "astes", "aram"),
        "imperfect": ("ava", "avas", "ava", "ávamos", "áveis", "avam"),
        "present_subjunctive": ("e", "es", "e", "emos", "eis", "em"),
    },
    "er": {
        "present": ("o", "es", "e", "emos", "eis", "em"),
        "preterite": ("i", "este", "eu", "emos", "estes", "eram"),
        "imperfect": ("ia", "ias", "ia", "íamos", "íeis", "iam"),
        "present_subjunctive": ("a", "as", "a", "amos", "ais", "am"),
    },
    "ir": {
        "present": ("o", "es", "e", "imos", "is", "em"),
        "preterite": ("i", "iste", "iu", "imos", "istes", "iram"),
        "imperfect": ("ia", "ias", "ia", "íamos", "íeis", "iam"),
        "present_subjunctive": ("a", "as", "a", "amos", "ais", "am"),
    },
}


def _spanish_stem_for_ending(stem: str, ending: str) -> str:
    if not ending.startswith(("e", "é")):
        return stem
    if stem.endswith("z"):
        return stem[:-1] + "c"
    if stem.endswith("c"):
        return stem[:-1] + "qu"
    if stem.endswith("g"):
        return stem + "u"
    return stem


def _portuguese_stem_for_ending(stem: str, ending: str) -> str:
    if not ending.startswith(("e", "é")):
        return stem
    if stem.endswith("c"):
        return stem[:-1] + "qu"
    if stem.endswith("g"):
        return stem + "u"
    return stem


def _regular_forms(
    language: str,
    family: PredicateFamily,
    lemma: str,
) -> list[tuple[str, PredicateForm]]:
    endings_table = _ES_REGULAR_ENDINGS if language == "es" else _PT_REGULAR_ENDINGS
    conjugation = lemma[-2:]
    if conjugation not in endings_table:
        return []

    stem = lemma[:-2]
    person_number = (
        (1, "singular"),
        (2, "singular"),
        (3, "singular"),
        (1, "plural"),
        (2, "plural"),
        (3, "plural"),
    )
    output: list[tuple[str, PredicateForm]] = []
    for tense_aspect, endings in endings_table[conjugation].items():
        mood = "subjunctive" if "subjunctive" in tense_aspect else "indicative"
        for (person, number), ending in zip(person_number, endings, strict=True):
            adjusted_stem = (
                _spanish_stem_for_ending(stem, ending)
                if language == "es"
                else _portuguese_stem_for_ending(stem, ending)
            )
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    mood,
                    adjusted_stem + ending,
                )
            )

    if language == "es":
        future_endings = ("é", "ás", "á", "emos", "éis", "án")
        conditional_endings = ("ía", "ías", "ía", "íamos", "íais", "ían")
    else:
        future_endings = ("ei", "ás", "á", "emos", "eis", "ão")
        conditional_endings = ("ia", "ias", "ia", "íamos", "íeis", "iam")

    for tense_aspect, endings in (
        ("future", future_endings),
        ("conditional", conditional_endings),
    ):
        for (person, number), ending in zip(person_number, endings, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    "indicative",
                    lemma + ending,
                )
            )
    return output


_ES_IRREGULAR: dict[str, dict[str, tuple[str, ...]]] = {
    "hacer": {
        "present": ("hago", "haces", "hace", "hacemos", "hacéis", "hacen"),
        "preterite": ("hice", "hiciste", "hizo", "hicimos", "hicisteis", "hicieron"),
        "imperfect": ("hacía", "hacías", "hacía", "hacíamos", "hacíais", "hacían"),
        "present_subjunctive": ("haga", "hagas", "haga", "hagamos", "hagáis", "hagan"),
    },
    "dar": {
        "present": ("doy", "das", "da", "damos", "dais", "dan"),
        "preterite": ("di", "diste", "dio", "dimos", "disteis", "dieron"),
        "imperfect": ("daba", "dabas", "daba", "dábamos", "dabais", "daban"),
        "present_subjunctive": ("dé", "des", "dé", "demos", "deis", "den"),
    },
    "salir": {
        "present": ("salgo", "sales", "sale", "salimos", "salís", "salen"),
        "preterite": ("salí", "saliste", "salió", "salimos", "salisteis", "salieron"),
        "imperfect": ("salía", "salías", "salía", "salíamos", "salíais", "salían"),
        "present_subjunctive": ("salga", "salgas", "salga", "salgamos", "salgáis", "salgan"),
    },
    "venir": {
        "present": ("vengo", "vienes", "viene", "venimos", "venís", "vienen"),
        "preterite": ("vine", "viniste", "vino", "vinimos", "vinisteis", "vinieron"),
        "imperfect": ("venía", "venías", "venía", "veníamos", "veníais", "venían"),
        "present_subjunctive": ("venga", "vengas", "venga", "vengamos", "vengáis", "vengan"),
    },
    "reconocer": {
        "present": ("reconozco", "reconoces", "reconoce", "reconocemos", "reconocéis", "reconocen"),
        "preterite": ("reconocí", "reconociste", "reconoció", "reconocimos", "reconocisteis", "reconocieron"),
        "imperfect": ("reconocía", "reconocías", "reconocía", "reconocíamos", "reconocíais", "reconocían"),
        "present_subjunctive": ("reconozca", "reconozcas", "reconozca", "reconozcamos", "reconozcáis", "reconozcan"),
    },
}

_PT_IRREGULAR: dict[str, dict[str, tuple[str, ...]]] = {
    "fazer": {
        "present": ("faço", "fazes", "faz", "fazemos", "fazeis", "fazem"),
        "preterite": ("fiz", "fizeste", "fez", "fizemos", "fizestes", "fizeram"),
        "imperfect": ("fazia", "fazias", "fazia", "fazíamos", "fazíeis", "faziam"),
        "present_subjunctive": ("faça", "faças", "faça", "façamos", "façais", "façam"),
    },
    "dar": {
        "present": ("dou", "dás", "dá", "damos", "dais", "dão"),
        "preterite": ("dei", "deste", "deu", "demos", "destes", "deram"),
        "imperfect": ("dava", "davas", "dava", "dávamos", "dáveis", "davam"),
        "present_subjunctive": ("dê", "dês", "dê", "demos", "deis", "deem"),
    },
    "sair": {
        "present": ("saio", "sais", "sai", "saímos", "saís", "saem"),
        "preterite": ("saí", "saíste", "saiu", "saímos", "saístes", "saíram"),
        "imperfect": ("saía", "saías", "saía", "saíamos", "saíeis", "saíam"),
        "present_subjunctive": ("saia", "saias", "saia", "saiamos", "saiais", "saiam"),
    },
    "vir": {
        "present": ("venho", "vens", "vem", "vimos", "vindes", "vêm"),
        "preterite": ("vim", "vieste", "veio", "viemos", "viestes", "vieram"),
        "imperfect": ("vinha", "vinhas", "vinha", "vínhamos", "vínheis", "vinham"),
        "present_subjunctive": ("venha", "venhas", "venha", "venhamos", "venhais", "venham"),
    },
    "reconhecer": {
        "present": ("reconheço", "reconheces", "reconhece", "reconhecemos", "reconheceis", "reconhecem"),
        "preterite": ("reconheci", "reconheceste", "reconheceu", "reconhecemos", "reconhecestes", "reconheceram"),
        "imperfect": ("reconhecia", "reconhecias", "reconhecia", "reconhecíamos", "reconhecíeis", "reconheciam"),
        "present_subjunctive": ("reconheça", "reconheças", "reconheça", "reconheçamos", "reconheçais", "reconheçam"),
    },
}


_ES_LEMMAS: dict[PredicateFamily, tuple[str, ...]] = {
    PredicateFamily.PERFORM: (
        "hacer",
        "realizar",
        "efectuar",
        "ordenar",
        "mandar",
        "pagar",
        "retirar",
        "transferir",
        "comprar",
        "gastar",
    ),
    PredicateFamily.ORIGINATE: ("salir", "partir", "provenir", "venir"),
    PredicateFamily.AUTHORIZE: ("autorizar", "aprobar", "consentir", "permitir"),
    PredicateFamily.GIVE_PERMISSION: ("dar",),
    PredicateFamily.RECOGNIZE: ("reconocer", "identificar"),
    PredicateFamily.USE_ACCESS: (
        "usar",
        "utilizar",
        "entrar",
        "acceder",
        "agarrar",
        "coger",
        "tomar",
        "sacar",
    ),
    PredicateFamily.COMPROMISE: ("robar", "clonar", "hackear"),
}

_PT_LEMMAS: dict[PredicateFamily, tuple[str, ...]] = {
    PredicateFamily.PERFORM: (
        "fazer",
        "realizar",
        "efetuar",
        "mandar",
        "pagar",
        "sacar",
        "transferir",
        "comprar",
        "gastar",
    ),
    PredicateFamily.ORIGINATE: ("partir", "sair", "vir"),
    PredicateFamily.AUTHORIZE: ("autorizar", "aprovar", "consentir", "permitir"),
    PredicateFamily.GIVE_PERMISSION: ("dar",),
    PredicateFamily.RECOGNIZE: ("reconhecer", "identificar"),
    PredicateFamily.USE_ACCESS: (
        "usar",
        "utilizar",
        "entrar",
        "acessar",
        "pegar",
        "tomar",
    ),
    PredicateFamily.COMPROMISE: ("roubar", "clonar", "hackear", "invadir", "furtar"),
}


_ES_FUTURE_STEMS = {
    "hacer": "har",
    "salir": "saldr",
    "venir": "vendr",
}
_PT_FUTURE_STEMS = {
    "fazer": "far",
    "vir": "vir",
}


def _irregular_forms(
    language: str,
    family: PredicateFamily,
    lemma: str,
) -> list[tuple[str, PredicateForm]]:
    table = _ES_IRREGULAR if language == "es" else _PT_IRREGULAR
    if lemma not in table:
        return []

    person_number = (
        (1, "singular"),
        (2, "singular"),
        (3, "singular"),
        (1, "plural"),
        (2, "plural"),
        (3, "plural"),
    )
    output: list[tuple[str, PredicateForm]] = []
    for tense_aspect, surfaces in table[lemma].items():
        mood = "subjunctive" if "subjunctive" in tense_aspect else "indicative"
        for (person, number), surface in zip(person_number, surfaces, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    mood,
                    surface,
                )
            )

    if language == "es":
        future_stem = _ES_FUTURE_STEMS.get(lemma, lemma)
        future_endings = ("é", "ás", "á", "emos", "éis", "án")
        conditional_endings = ("ía", "ías", "ía", "íamos", "íais", "ían")
    else:
        future_stem = _PT_FUTURE_STEMS.get(lemma, lemma)
        future_endings = ("ei", "ás", "á", "emos", "eis", "ão")
        conditional_endings = ("ia", "ias", "ia", "íamos", "íeis", "iam")

    for tense_aspect, endings in (
        ("future", future_endings),
        ("conditional", conditional_endings),
    ):
        for (person, number), ending in zip(person_number, endings, strict=True):
            output.append(
                _form(
                    family,
                    lemma,
                    language,
                    person,
                    number,
                    tense_aspect,
                    "indicative",
                    future_stem + ending,
                )
            )
    return output


def _participle(language: str, lemma: str) -> str:
    if language == "es":
        irregular = {
            "hacer": "hecho",
        }
        if lemma in irregular:
            return irregular[lemma]
        if lemma.endswith("ar"):
            return lemma[:-2] + "ado"
        return lemma[:-2] + "ido"

    irregular = {
        "fazer": "feito",
    }
    if lemma in irregular:
        return irregular[lemma]
    if lemma.endswith("ar"):
        return lemma[:-2] + "ado"
    return lemma[:-2] + "ido"


_ES_AUXILIARIES: dict[str, tuple[tuple[str, int, str], ...]] = {
    "present_perfect": (
        ("he", 1, "singular"),
        ("has", 2, "singular"),
        ("ha", 3, "singular"),
        ("hemos", 1, "plural"),
        ("habéis", 2, "plural"),
        ("han", 3, "plural"),
    ),
    "pluperfect": (
        ("había", 1, "singular"),
        ("habías", 2, "singular"),
        ("había", 3, "singular"),
        ("habíamos", 1, "plural"),
        ("habíais", 2, "plural"),
        ("habían", 3, "plural"),
    ),
}

_PT_AUXILIARIES: dict[str, tuple[tuple[str, int, str], ...]] = {
    "iterative_compound": (
        ("tenho", 1, "singular"),
        ("tens", 2, "singular"),
        ("tem", 3, "singular"),
        ("temos", 1, "plural"),
        ("tendes", 2, "plural"),
        ("têm", 3, "plural"),
    ),
    "pluperfect": (
        ("tinha", 1, "singular"),
        ("tinhas", 2, "singular"),
        ("tinha", 3, "singular"),
        ("tínhamos", 1, "plural"),
        ("tínheis", 2, "plural"),
        ("tinham", 3, "plural"),
    ),
}


def _build_paradigm(language: str) -> dict[str, tuple[PredicateForm, ...]]:
    lemma_map = _ES_LEMMAS if language == "es" else _PT_LEMMAS
    forms: dict[str, list[PredicateForm]] = {}

    for family, lemmas in lemma_map.items():
        for lemma in lemmas:
            generated = _irregular_forms(language, family, lemma)
            if not generated:
                generated = _regular_forms(language, family, lemma)

            for normalized, form in generated:
                forms.setdefault(normalized, []).append(form)

            participle = _participle(language, lemma)
            normalized_participle, participle_form = _form(
                family,
                lemma,
                language,
                None,
                None,
                "participle",
                "participle",
                participle,
                voice="participle",
            )
            forms.setdefault(normalized_participle, []).append(participle_form)

    return {surface: tuple(entries) for surface, entries in forms.items()}


PARADIGMS: dict[str, dict[str, tuple[PredicateForm, ...]]] = {
    "es": _build_paradigm("es"),
    "pt": _build_paradigm("pt"),
}


def _compound_match(
    tokens: tuple[Token, ...],
    index: int,
    language: str,
) -> list[PredicateMatch]:
    if index + 1 >= len(tokens):
        return []

    aux_table = _ES_AUXILIARIES if language == "es" else _PT_AUXILIARIES
    aux = tokens[index]
    participle = tokens[index + 1]

    results: list[PredicateMatch] = []
    for tense_aspect, auxiliaries in aux_table.items():
        for aux_surface, person, number in auxiliaries:
            if aux.normalized != _normalize_word(aux_surface):
                continue
            for form in PARADIGMS[language].get(participle.normalized, ()):
                if form.tense_aspect != "participle":
                    continue
                compound_form = PredicateForm(
                    family=form.family,
                    lemma=form.lemma,
                    language=language,
                    person=person,
                    number=number,
                    tense_aspect=tense_aspect,
                    mood="indicative",
                    voice="active",
                    accent_required=_has_acute(aux_surface),
                )
                results.append(
                    PredicateMatch(
                        form=compound_form,
                        token_start=index,
                        token_end=index + 2,
                        accent_ambiguous=(
                            compound_form.accent_required and not aux.had_acute
                        ),
                    )
                )
    return results


_ES_NOMINAL_DETERMINERS = frozenset(
    {"el", "la", "los", "las", "un", "una", "unos", "unas", "este", "esta", "ese", "esa", "mi", "mis", "su", "sus"}
)
_PT_NOMINAL_DETERMINERS = frozenset(
    {"o", "a", "os", "as", "um", "uma", "uns", "umas", "este", "esta", "esse", "essa", "meu", "minha", "meus", "minhas", "seu", "sua"}
)


def _looks_nominal(
    tokens: tuple[Token, ...],
    index: int,
    language: str,
) -> bool:
    activity = _ES_ACTIVITY if language == "es" else _PT_ACTIVITY
    if tokens[index].normalized not in activity:
        return False

    determiners = (
        _ES_NOMINAL_DETERMINERS
        if language == "es"
        else _PT_NOMINAL_DETERMINERS
    )
    if index > 0:
        previous = tokens[index - 1]
        if previous.normalized in determiners:
            return True
        if previous.normalized.isdigit() or previous.is_txid:
            return True
    if index + 1 < len(tokens) and tokens[index + 1].is_txid:
        return True
    return False


def find_predicates(
    tokens: Iterable[Token],
    language: str,
) -> tuple[PredicateMatch, ...]:
    token_tuple = tuple(tokens)
    if language not in PARADIGMS:
        raise ValueError(f"unsupported language: {language}")

    matches: list[PredicateMatch] = []
    compound_consumed: set[int] = set()
    for index, token in enumerate(token_tuple):
        compounds = _compound_match(token_tuple, index, language)
        if compounds:
            matches.extend(compounds)
            compound_consumed.add(index + 1)

        if index in compound_consumed:
            continue
        if _looks_nominal(token_tuple, index, language):
            continue

        for form in PARADIGMS[language].get(token.normalized, ()):
            if form.tense_aspect == "participle":
                continue
            matches.append(
                PredicateMatch(
                    form=form,
                    token_start=index,
                    token_end=index + 1,
                    accent_ambiguous=form.accent_required and not token.had_acute,
                )
            )

    return tuple(matches)


_ES_ACTIVITY = frozenset(
    {
        "cargo",
        "cargos",
        "cobro",
        "cobros",
        "compra",
        "compras",
        "pago",
        "pagos",
        "movimiento",
        "movimientos",
        "operacion",
        "operaciones",
        "transaccion",
        "transacciones",
        "transferencia",
        "transferencias",
        "debito",
        "debitos",
        "retiro",
        "retiros",
        "consumo",
        "consumos",
    }
)

_PT_ACTIVITY = frozenset(
    {
        "cobranca",
        "cobrancas",
        "compra",
        "compras",
        "pagamento",
        "pagamentos",
        "lancamento",
        "lancamentos",
        "operacao",
        "operacoes",
        "transacao",
        "transacoes",
        "transferencia",
        "transferencias",
        "pix",
        "debito",
        "debitos",
        "saque",
        "saques",
        "gasto",
        "gastos",
        "ted",
        "boleto",
        "boletos",
        "movimentacao",
        "movimentacoes",
    }
)

_ES_INSTRUMENT = frozenset({"tarjeta", "cuenta", "billetera", "wallet"})
_PT_INSTRUMENT = frozenset({"cartao", "conta", "carteira", "wallet"})

_ES_SELF = frozenset({"yo", "me", "mi", "mio", "mia", "mios", "mias", "nosotros", "nosotras"})
_PT_SELF = frozenset({"eu", "me", "mim", "meu", "minha", "meus", "minhas", "nos"})

_ES_THIRD = frozenset({"alguien", "tercero", "tercera", "persona"})
_PT_THIRD = frozenset({"alguem", "terceiro", "terceira", "pessoa"})

_ES_RELATIONAL_NOUNS = frozenset(
    {
        "hermano", "hermana", "madre", "padre", "mama", "papa",
        "hijo", "hija", "esposo", "esposa", "pareja",
        "amigo", "amiga", "vecino", "vecina",
        "empleado", "empleada", "primo", "prima", "tio", "tia",
        "abuelo", "abuela",
    }
)
_PT_RELATIONAL_NOUNS = frozenset(
    {
        "irmao", "irma", "mae", "pai",
        "filho", "filha", "marido", "esposa", "parceiro", "parceira",
        "amigo", "amiga", "vizinho", "vizinha",
        "funcionario", "funcionaria", "primo", "prima", "tio", "tia", "avo",
    }
)

_ES_NEG_QUANT = frozenset({"nadie", "ninguno", "ninguna", "ningunos", "ningunas"})
_PT_NEG_QUANT = frozenset({"ninguem", "nenhum", "nenhuma", "nenhuns", "nenhumas"})

_ES_AUTH_NOUN = frozenset({"autorizacion", "permiso", "consentimiento"})
_PT_AUTH_NOUN = frozenset({"autorizacao", "permissao", "consentimento", "anuencia"})

_ES_FRAUD = frozenset({"fraude", "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"})
_PT_FRAUD = frozenset({"fraude", "golpe", "fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"})

_ES_DESCRIPTOR = frozenset({"nombre", "comercio", "establecimiento", "descriptor", "descripcion"})
_PT_DESCRIPTOR = frozenset({"nome", "comercio", "estabelecimento", "descritor", "descricao"})

_ES_SECURITY = frozenset({"seguridad", "proteccion", "alerta", "alertas", "notificacion", "notificaciones", "medidas", "controles"})
_PT_SECURITY = frozenset({"seguranca", "protecao", "alerta", "alertas", "notificacao", "notificacoes", "medidas", "controles", "cuidados"})

_ES_UNCERTAINTY = frozenset({"quizas", "talvez"})
_PT_UNCERTAINTY = frozenset({"talvez"})

_ES_CONTRAST = frozenset({"pero", "sino", "aunque"})
_PT_CONTRAST = frozenset({"mas", "porem", "embora"})


def _next_predicate_index(
    index: int,
    predicates: tuple[PredicateMatch, ...],
    *,
    max_gap: int = 2,
) -> int | None:
    for predicate in predicates:
        if predicate.token_start < index:
            continue
        if predicate.token_start - index <= max_gap:
            return predicate.token_start
        break
    return None


def _is_conditional_marker(
    index: int,
    tokens: tuple[Token, ...],
    predicates: tuple[PredicateMatch, ...],
    language: str,
) -> bool:
    token = tokens[index]
    word = token.normalized
    if language == "es":
        if word != "si" or token.had_acute:
            return False
    else:
        if word not in {"se", "caso"}:
            return False

    if index > 0:
        previous = tokens[index - 1].normalized
        if previous not in {".", "?", "!", ";", ":", "-", "¿", "¡", "pero", "mas", "porem"}:
            return False

    for predicate in predicates:
        if predicate.token_start <= index:
            continue
        if predicate.token_start - index > 5:
            break
        if language == "pt" and word == "caso" and predicate.form.mood != "subjunctive":
            continue
        return True
    return False


def tag_tokens(
    tokens: Iterable[Token],
    language: str,
    predicates: Iterable[PredicateMatch] = (),
) -> tuple[frozenset[LexicalTag], ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    if language not in {"es", "pt"}:
        raise ValueError(f"unsupported language: {language}")

    activity = _ES_ACTIVITY if language == "es" else _PT_ACTIVITY
    instrument = _ES_INSTRUMENT if language == "es" else _PT_INSTRUMENT
    self_words = _ES_SELF if language == "es" else _PT_SELF
    third_party = _ES_THIRD if language == "es" else _PT_THIRD
    neg_quant = _ES_NEG_QUANT if language == "es" else _PT_NEG_QUANT
    auth_noun = _ES_AUTH_NOUN if language == "es" else _PT_AUTH_NOUN
    fraud = _ES_FRAUD if language == "es" else _PT_FRAUD
    descriptor = _ES_DESCRIPTOR if language == "es" else _PT_DESCRIPTOR
    security = _ES_SECURITY if language == "es" else _PT_SECURITY
    uncertainty = _ES_UNCERTAINTY if language == "es" else _PT_UNCERTAINTY
    contrast = _ES_CONTRAST if language == "es" else _PT_CONTRAST

    predicate_starts = {predicate.token_start for predicate in predicate_tuple}
    tags: list[frozenset[LexicalTag]] = []
    for index, token in enumerate(token_tuple):
        current: set[LexicalTag] = set()
        word = token.normalized

        if token.is_txid:
            current.add(LexicalTag.TXID)
            current.add(LexicalTag.ACTIVITY)
        if word in activity and index not in predicate_starts:
            current.add(LexicalTag.ACTIVITY)
        if word in instrument:
            current.add(LexicalTag.INSTRUMENT)
        if word in self_words:
            current.add(LexicalTag.SELF)
        if (
            language == "pt"
            and word in {"a", "gente"}
            and (
                (word == "a" and index + 1 < len(token_tuple) and token_tuple[index + 1].normalized == "gente")
                or (word == "gente" and index > 0 and token_tuple[index - 1].normalized == "a")
            )
        ):
            current.add(LexicalTag.SELF)
        if word in third_party:
            current.add(LexicalTag.THIRD_PARTY)
        if word in neg_quant:
            current.add(LexicalTag.NEG_QUANTIFIER)
        if word in auth_noun:
            current.add(LexicalTag.AUTH_NOUN)
        if word in fraud:
            current.add(LexicalTag.FRAUD_MARKER)
        if word in descriptor:
            current.add(LexicalTag.DESCRIPTOR_NOUN)
        if word in security:
            current.add(LexicalTag.SECURITY_INFO)
        if word in uncertainty:
            current.add(LexicalTag.UNCERTAINTY)
        if word in contrast:
            current.add(LexicalTag.CONTRAST)

        if language == "es":
            if word == "no":
                next_predicate = _next_predicate_index(index + 1, predicate_tuple, max_gap=1)
                if next_predicate is not None:
                    current.add(LexicalTag.NEGATOR)
            if word in {"ni"}:
                current.add(LexicalTag.COORD_NEGATION)
            if word in {"mio", "mia", "mios", "mias"}:
                current.add(LexicalTag.OWNERSHIP)
            if _is_conditional_marker(index, token_tuple, predicate_tuple, language):
                current.add(LexicalTag.CONDITIONAL)
            if token.surface == "¿":
                current.add(LexicalTag.QUESTION_OPEN)
            if token.surface == "?":
                current.add(LexicalTag.QUESTION_CLOSE)
        else:
            if word == "nao":
                current.add(LexicalTag.NEGATOR)
            if word == "nem":
                current.add(LexicalTag.COORD_NEGATION)
            if word in {"meu", "minha", "meus", "minhas"}:
                current.add(LexicalTag.OWNERSHIP)
            if _is_conditional_marker(index, token_tuple, predicate_tuple, language):
                current.add(LexicalTag.CONDITIONAL)

        tags.append(frozenset(current))

    return tuple(tags)


def _spanish_mi_pair_allows_self_role(
    tokens: tuple[Token, ...],
    mi_index: int,
) -> bool:
    """Distinguish accented pronoun mí from possessive mi before a noun."""

    token = tokens[mi_index]
    if token.normalized != "mi":
        return True
    if token.had_acute:
        return True
    if mi_index + 1 >= len(tokens):
        return True

    following = tokens[mi_index + 1].normalized
    if following == "parte":
        return True

    nominal_heads = (
        _ES_ACTIVITY
        | _ES_INSTRUMENT
        | _ES_RELATIONAL_NOUNS
        | _ES_AUTH_NOUN
        | _ES_DESCRIPTOR
        | _ES_SECURITY
    )
    return following not in nominal_heads


def find_self_evidence(
    tokens: Iterable[Token],
    predicates: Iterable[PredicateMatch],
    language: str,
) -> tuple[SelfEvidence, ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    evidence: list[SelfEvidence] = []

    if language == "es":
        subject_words = {"yo", "nosotros", "nosotras"}
        possessor_words = {"mi", "mio", "mia", "mios", "mias"}
        dative_words = {"me"}
        agent_pairs = {("por", "mi")}
        source_pairs = {("de", "mi")}
        source_triplets = {("de", "mi", "parte")}
        dative_pairs = {("a", "mi"), ("para", "mi")}
    elif language == "pt":
        subject_words = {"eu", "nos"}
        possessor_words = {"meu", "minha", "meus", "minhas"}
        dative_words = {"me"}
        agent_pairs = {("por", "mim")}
        source_pairs = {("de", "mim")}
        source_triplets = {("da", "minha", "parte")}
        dative_pairs = {("a", "mim"), ("para", "mim"), ("pra", "mim")}
    else:
        raise ValueError(f"unsupported language: {language}")

    words = [token.normalized for token in token_tuple]

    for index, word in enumerate(words):
        if word in subject_words and not (
            language == "pt"
            and word == "nos"
            and not token_tuple[index].had_acute
        ):
            evidence.append(SelfEvidence(SelfRole.SUBJECT, index, index + 1))
        if language == "pt" and index + 1 < len(words) and (word, words[index + 1]) == ("a", "gente"):
            evidence.append(SelfEvidence(SelfRole.SUBJECT, index, index + 2))
        if word in possessor_words and not (
            language == "es" and word == "mi" and token_tuple[index].had_acute
        ):
            evidence.append(SelfEvidence(SelfRole.POSSESSOR, index, index + 1))
        if word in dative_words:
            evidence.append(SelfEvidence(SelfRole.DATIVE, index, index + 1))

        if index + 1 < len(words):
            pair = (word, words[index + 1])
            if pair in agent_pairs:
                evidence.append(SelfEvidence(SelfRole.AGENT, index, index + 2))
            if pair in source_pairs and (
                language != "es"
                or _spanish_mi_pair_allows_self_role(token_tuple, index + 1)
            ):
                evidence.append(SelfEvidence(SelfRole.SOURCE, index, index + 2))
            if pair in dative_pairs and (
                language != "es"
                or _spanish_mi_pair_allows_self_role(token_tuple, index + 1)
            ):
                evidence.append(SelfEvidence(SelfRole.DATIVE, index, index + 2))

        if index + 2 < len(words):
            triplet = (word, words[index + 1], words[index + 2])
            if triplet in source_triplets:
                evidence.append(SelfEvidence(SelfRole.SOURCE, index, index + 3))

    for predicate in predicate_tuple:
        if predicate.form.person != 1:
            continue
        evidence.append(
            SelfEvidence(
                SelfRole.SUBJECT,
                predicate.token_start,
                predicate.token_end,
                implicit_from_predicate=True,
                ambiguous=predicate.accent_ambiguous,
            )
        )

    unique: dict[tuple[SelfRole, int, int, bool, bool], SelfEvidence] = {}
    for item in evidence:
        unique[
            (
                item.role,
                item.token_start,
                item.token_end,
                item.implicit_from_predicate,
                item.ambiguous,
            )
        ] = item
    return tuple(unique.values())


def _colon_has_finite_predicate(
    token_index: int,
    tokens: tuple[Token, ...],
    predicates: tuple[PredicateMatch, ...],
    text: str,
) -> bool:
    next_boundary = len(tokens)
    for index in range(token_index + 1, len(tokens)):
        if _is_primary_boundary(text, tokens[index]):
            next_boundary = index
            break

    return any(
        predicate.token_start > token_index
        and predicate.token_start < next_boundary
        and predicate.form.person is not None
        for predicate in predicates
    )


def segment_clauses(
    text: str,
    tokens: Iterable[Token],
    predicates: Iterable[PredicateMatch] = (),
) -> tuple[ClauseSegment, ...]:
    token_tuple = tuple(tokens)
    predicate_tuple = tuple(predicates)
    if not token_tuple:
        return ()

    boundaries: list[int] = []
    for index, token in enumerate(token_tuple):
        is_boundary = _is_primary_boundary(text, token)
        if token.normalized == ":":
            is_boundary = _colon_has_finite_predicate(
                index,
                token_tuple,
                predicate_tuple,
                text,
            )
        if is_boundary:
            boundaries.append(index)

    segments: list[ClauseSegment] = []
    start = 0
    segment_index = 0
    for boundary in boundaries:
        if boundary > start:
            segments.append(
                ClauseSegment(
                    index=segment_index,
                    token_start=start,
                    token_end=boundary,
                    source_start=token_tuple[start].start,
                    source_end=token_tuple[boundary - 1].end,
                )
            )
            segment_index += 1
        start = boundary + 1

    if start < len(token_tuple):
        segments.append(
            ClauseSegment(
                index=segment_index,
                token_start=start,
                token_end=len(token_tuple),
                source_start=token_tuple[start].start,
                source_end=token_tuple[-1].end,
            )
        )

    return tuple(segments)


def analyze_foundation(text: str, language: str) -> FoundationAnalysis:
    """Return RF1H-B1 structural primitives without classifying authorization."""

    tokens = tokenize_with_source(text)
    predicates = find_predicates(tokens, language)
    tags = tag_tokens(tokens, language, predicates)
    self_evidence = find_self_evidence(tokens, predicates, language)
    clauses = segment_clauses(text, tokens, predicates)
    return FoundationAnalysis(
        tokens=tokens,
        clauses=clauses,
        predicates=predicates,
        tags=tags,
        self_evidence=self_evidence,
    )


class PropositionFamily(str, Enum):
    OWNERSHIP_DENIAL = "ownership_denial"
    PERFORMANCE_DENIAL = "performance_denial"
    ORIGINATION_DENIAL = "origination_denial"
    AUTHORIZATION_DENIAL = "authorization_denial"
    THIRD_PARTY_UNAUTHORIZED_USE = "third_party_unauthorized_use"
    FRAUD_CHARACTERIZATION = "fraud_characterization"
    ACTIVITY_NONRECOGNITION = "activity_nonrecognition"
    COMPROMISE_LINKED_ACTIVITY = "compromise_linked_activity"


@dataclass(frozen=True)
class PositiveProposition:
    """Unresolved RF1H-B2 positive proposition.

    Scope/exclusion and retraction fields are intentionally present now so B3 can
    resolve propositions without changing the proposition audit shape.
    """

    family: PropositionFamily
    rule: str
    language: str
    clause_index: int
    token_start: int
    token_end: int
    source_start: int
    source_end: int
    activity_token_span: tuple[int, int] | None
    activity_ref: str
    predicate_token_span: tuple[int, int] | None
    evidence_token_spans: tuple[tuple[int, int], ...]
    mode: str = "unresolved"
    exclusion_provenance: tuple[str, ...] = ()
    retraction_provenance: tuple[str, ...] = ()


_ES_COPULA = frozenset({"es", "son", "era", "eran", "fue", "fueron"})
_PT_COPULA = frozenset({"e", "sao", "era", "eram", "foi", "foram"})

_ES_ALIENATION_WORDS = frozenset({"ajeno", "ajena", "ajenos", "ajenas"})
_PT_ALIENATION_WORDS = frozenset({"alheio", "alheia", "alheios", "alheias"})

_ES_ALIENATION_PHRASES = (
    ("de", "otra", "persona"),
    ("de", "otras", "personas"),
    ("de", "un", "tercero"),
    ("de", "terceros"),
)
_PT_ALIENATION_PHRASES = (
    ("de", "outra", "pessoa"),
    ("de", "outras", "pessoas"),
    ("de", "um", "terceiro"),
    ("de", "terceiros"),
)

_ES_DENIAL_WORDS = frozenset({"no", "nunca", "jamas"})
_PT_DENIAL_WORDS = frozenset({"nao", "nunca", "jamais"})


def _in_clause(span_start: int, span_end: int, clause: ClauseSegment) -> bool:
    return span_start >= clause.token_start and span_end <= clause.token_end


def _negative_indices(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[int, ...]:
    denial_words = _ES_DENIAL_WORDS if language == "es" else _PT_DENIAL_WORDS
    indices: list[int] = []
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized in denial_words:
            indices.append(index)
            continue
        if analysis.tags[index] & {
            LexicalTag.NEGATOR,
            LexicalTag.NEG_QUANTIFIER,
            LexicalTag.COORD_NEGATION,
        }:
            indices.append(index)
    return tuple(dict.fromkeys(indices))


def _activity_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.ACTIVITY in analysis.tags[index]
    )


def _nearest_activity_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch | None,
) -> tuple[int, int] | None:
    spans = _activity_spans(analysis, clause)
    if not spans:
        return None
    if predicate is None:
        return spans[0]
    return min(
        spans,
        key=lambda span: min(
            abs(span[0] - predicate.token_start),
            abs(span[0] - (predicate.token_end - 1)),
        ),
    )


def _self_roles_in_clause(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[SelfEvidence, ...]:
    return tuple(
        item
        for item in analysis.self_evidence
        if _in_clause(item.token_start, item.token_end, clause)
    )


_ES_DENIAL_BRIDGE_WORDS = frozenset(
    {
        "yo", "nosotros", "nosotras",
        "me", "te", "se", "lo", "la", "los", "las", "le", "les",
        "de", "mi", "mis", "nuestro", "nuestra", "nuestros", "nuestras",
        "nunca", "jamas", "tampoco", "ni",
    }
)
_PT_DENIAL_BRIDGE_WORDS = frozenset(
    {
        "eu", "nos",
        "me", "te", "se", "o", "a", "os", "as", "lhe", "lhes",
        "de", "do", "da", "dos", "das", "meu", "minha", "meus", "minhas",
        "nunca", "jamais", "tambem", "tampouco", "nem", "que",
    }
)
_DENIAL_BINDING_BARRIERS = frozenset({",", ";", "?", "¿", "!", "¡", ":"})


def _bound_denial_index_for_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    token_start: int,
    token_end: int,
    language: str,
) -> int | None:
    bridge_words = (
        _ES_DENIAL_BRIDGE_WORDS
        if language == "es"
        else _PT_DENIAL_BRIDGE_WORDS
    )
    candidates: list[int] = []

    for index in _negative_indices(analysis, clause, language):
        if index <= token_start:
            if token_start - index > 5:
                continue
            between = range(index + 1, token_start)
            if any(
                analysis.tokens[item].surface in _DENIAL_BINDING_BARRIERS
                for item in between
            ):
                continue
            non_bridge = tuple(
                item
                for item in between
                if analysis.tokens[item].normalized not in bridge_words
            )
            if non_bridge:
                token_tags = analysis.tags[index]
                has_prior_correlative = (
                    LexicalTag.COORD_NEGATION in token_tags
                    and any(
                        prior < index
                        and LexicalTag.COORD_NEGATION in analysis.tags[prior]
                        for prior in _negative_indices(
                            analysis,
                            clause,
                            language,
                        )
                    )
                )
                if not has_prior_correlative:
                    continue
            candidates.append(index)
            continue

        if index >= token_end:
            if index - token_end > 2:
                continue
            between = range(token_end, index)
            if any(
                analysis.tokens[item].surface in _DENIAL_BINDING_BARRIERS
                for item in between
            ):
                continue
            candidates.append(index)

    if not candidates:
        return None
    return min(
        candidates,
        key=lambda index: min(
            abs(index - token_start),
            abs(index - token_end),
        ),
    )



def _bound_denial_index(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> int | None:
    return _bound_denial_index_for_span(
        analysis,
        clause,
        predicate.token_start,
        predicate.token_end,
        language,
    )


def _span_has_bound_denial(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    token_start: int,
    token_end: int,
    language: str,
) -> bool:
    return _bound_denial_index_for_span(
        analysis,
        clause,
        token_start,
        token_end,
        language,
    ) is not None

def _predicate_has_denial(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    return _bound_denial_index(
        analysis,
        clause,
        predicate,
        language,
    ) is not None


def _source_span_for_token_span(
    analysis: FoundationAnalysis,
    span: tuple[int, int],
) -> tuple[int, int]:
    start, end = span
    return analysis.tokens[start].start, analysis.tokens[end - 1].end


def _make_proposition(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    *,
    family: PropositionFamily,
    rule: str,
    language: str,
    evidence_spans: Iterable[tuple[int, int]],
    activity_span: tuple[int, int] | None,
    predicate: PredicateMatch | None,
    activity_ref: str | None = None,
) -> PositiveProposition:
    evidence = tuple(evidence_spans)
    concrete_spans = list(evidence)
    if activity_span is not None and activity_span not in concrete_spans:
        concrete_spans.append(activity_span)
    if predicate is not None:
        predicate_span = (predicate.token_start, predicate.token_end)
        if predicate_span not in concrete_spans:
            concrete_spans.append(predicate_span)
    else:
        predicate_span = None

    token_start = min(span[0] for span in concrete_spans)
    token_end = max(span[1] for span in concrete_spans)
    source_start = analysis.tokens[token_start].start
    source_end = analysis.tokens[token_end - 1].end

    return PositiveProposition(
        family=family,
        rule=rule,
        language=language,
        clause_index=clause.index,
        token_start=token_start,
        token_end=token_end,
        source_start=source_start,
        source_end=source_end,
        activity_token_span=activity_span,
        activity_ref=(
            activity_ref
            if activity_ref is not None
            else ("explicit_activity" if activity_span is not None else "topic_transaction")
        ),
        predicate_token_span=predicate_span,
        evidence_token_spans=tuple(concrete_spans),
    )


def _ownership_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_spans = _activity_spans(analysis, clause)
    if not activity_spans:
        return []

    copulas = _ES_COPULA if language == "es" else _PT_COPULA
    ownership_indices = [
        index
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.OWNERSHIP in analysis.tags[index]
    ]
    negatives = _negative_indices(analysis, clause, language)
    output: list[PositiveProposition] = []

    for copula_index in range(clause.token_start, clause.token_end):
        token = analysis.tokens[copula_index]
        if token.normalized not in copulas:
            continue
        if language == "pt" and token.normalized == "e" and not token.had_acute:
            continue

        neg_index = next(
            (
                index
                for index in reversed(negatives)
                if index < copula_index and copula_index - index <= 3
            ),
            None,
        )
        if neg_index is None:
            continue
        owner_index = next(
            (
                index
                for index in ownership_indices
                if index > copula_index and index - copula_index <= 3
            ),
            None,
        )
        if owner_index is None:
            continue

        activity_span = min(
            activity_spans,
            key=lambda span: abs(span[0] - copula_index),
        )
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.OWNERSHIP_DENIAL,
                rule="P1",
                language=language,
                evidence_spans=(
                    activity_span,
                    (neg_index, neg_index + 1),
                    (copula_index, copula_index + 1),
                    (owner_index, owner_index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _alienation_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_spans = _activity_spans(analysis, clause)
    if not activity_spans:
        return []

    words = [token.normalized for token in analysis.tokens]
    singletons = _ES_ALIENATION_WORDS if language == "es" else _PT_ALIENATION_WORDS
    phrases = _ES_ALIENATION_PHRASES if language == "es" else _PT_ALIENATION_PHRASES
    marker_spans: list[tuple[int, int]] = []

    for index in range(clause.token_start, clause.token_end):
        if words[index] in singletons:
            marker_spans.append((index, index + 1))

    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                marker_spans.append((index, index + width))

    output: list[PositiveProposition] = []
    for marker_span in marker_spans:
        activity_span = min(
            activity_spans,
            key=lambda span: abs(span[0] - marker_span[0]),
        )
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.OWNERSHIP_DENIAL,
                rule="P1b",
                language=language,
                evidence_spans=(activity_span, marker_span),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _role_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    allowed: frozenset[SelfRole],
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (item.token_start, item.token_end)
        for item in _self_roles_in_clause(analysis, clause)
        if item.role in allowed
    )


def _bound_self_evidence(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    allowed: frozenset[SelfRole],
) -> SelfEvidence | None:
    candidates: list[SelfEvidence] = []

    for item in _self_roles_in_clause(analysis, clause):
        if item.role not in allowed:
            continue

        if item.implicit_from_predicate:
            if (
                item.token_start == predicate.token_start
                and item.token_end == predicate.token_end
                and predicate.form.person == 1
            ):
                candidates.append(item)
            continue

        if item.role is SelfRole.SUBJECT and predicate.form.person != 1:
            continue

        distance = min(
            abs(item.token_start - predicate.token_end),
            abs(predicate.token_start - item.token_end),
        )
        if distance > 5:
            continue

        left = min(item.token_start, predicate.token_start)
        right = max(item.token_end, predicate.token_end)
        intervening = any(
            other.token_start >= left
            and other.token_end <= right
            and not (
                other.token_start == predicate.token_start
                and other.token_end == predicate.token_end
            )
            and not (
                other.token_start >= item.token_start
                and other.token_end <= item.token_end
            )
            and other.form.person is not None
            and not other.accent_ambiguous
            for other in analysis.predicates
            if _in_clause(other.token_start, other.token_end, clause)
        )
        if intervening:
            continue

        candidates.append(item)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda item: (
            0 if item.implicit_from_predicate else 1,
            min(
                abs(item.token_start - predicate.token_end),
                abs(predicate.token_start - item.token_end),
            ),
        ),
    )


_DENIAL_ASSERTIVE_TENSES = frozenset(
    {"preterite", "present_perfect", "pluperfect", "participle"}
)
_ES_DIRECTIVE_MARKERS = (
    ("por", "favor"),
    ("para", "que"),
    ("ojala",),
)
_PT_DIRECTIVE_MARKERS = (
    ("por", "favor"),
    ("para", "que"),
    ("tomara", "que"),
)


def _phrase_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    phrase: tuple[str, ...],
    *,
    max_gap: int = 6,
) -> bool:
    width = len(phrase)
    start = max(clause.token_start, predicate.token_start - max_gap)
    words = [token.normalized for token in analysis.tokens]
    for index in range(start, predicate.token_start - width + 1):
        if tuple(words[index : index + width]) == phrase:
            return True
    return False


def _relative_specific_activity_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]
    for index in range(
        max(clause.token_start, predicate.token_start - 6),
        predicate.token_start,
    ):
        if words[index] != "que":
            continue
        activity_span = next(
            (
                span
                for span in _activity_spans(analysis, clause)
                if span[1] <= index
                and index - span[1] <= 2
                and _customer_anchored_activity(
                    analysis,
                    clause,
                    span,
                    language,
                )
            ),
            None,
        )
        if activity_span is not None:
            return True
    return False


def _explicit_self_subject_binds(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
) -> bool:
    for item in _self_roles_in_clause(analysis, clause):
        if item.role is not SelfRole.SUBJECT or item.implicit_from_predicate:
            continue
        distance = min(
            abs(item.token_start - predicate.token_end),
            abs(predicate.token_start - item.token_end),
        )
        if distance > 5:
            continue
        left = min(item.token_start, predicate.token_start)
        right = max(item.token_end, predicate.token_end)
        if any(
            other.token_start >= left
            and other.token_end <= right
            and not (
                other.token_start == predicate.token_start
                and other.token_end == predicate.token_end
            )
            and other.form.person is not None
            and not other.accent_ambiguous
            for other in analysis.predicates
            if _in_clause(other.token_start, other.token_end, clause)
        ):
            continue
        return True
    return False


def _has_directive_marker_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    markers = (
        _ES_DIRECTIVE_MARKERS
        if language == "es"
        else _PT_DIRECTIVE_MARKERS
    )
    words = [token.normalized for token in analysis.tokens]
    for marker in markers:
        width = len(marker)
        for index in range(
            clause.token_start,
            max(clause.token_start, predicate.token_start - width + 1),
        ):
            if tuple(words[index : index + width]) == marker:
                return True
    return False


def _denial_reference_allowed(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> bool:
    form = predicate.form

    if (
        predicate.accent_ambiguous
        and predicate.token_end - predicate.token_start == 1
        and not analysis.tokens[predicate.token_start].had_acute
        and analysis.tokens[predicate.token_start].normalized in {"de", "da"}
    ):
        return False

    if predicate.accent_ambiguous and form.person == 1:
        if not _explicit_self_subject_binds(analysis, clause, predicate):
            return False
        if _has_directive_marker_before_predicate(
            analysis,
            clause,
            predicate,
            language,
        ):
            return False

    if form.tense_aspect in _DENIAL_ASSERTIVE_TENSES:
        return True

    if form.mood == "subjunctive":
        introducer = ("sin", "que") if language == "es" else ("sem", "que")
        return _phrase_before_predicate(
            analysis,
            clause,
            predicate,
            introducer,
        )

    if form.tense_aspect in {"present", "imperfect"}:
        return _relative_specific_activity_before_predicate(
            analysis,
            clause,
            predicate,
            language,
        )

    return False


def _predicate_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    *,
    predicate_family: PredicateFamily,
    proposition_family: PropositionFamily,
    rule: str,
    self_roles: frozenset[SelfRole],
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not predicate_family:
            continue
        if not _denial_reference_allowed(
            analysis,
            clause,
            predicate,
            language,
        ):
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            self_roles,
        )
        if self_evidence is None:
            continue

        activity_span = _nearest_activity_span(analysis, clause, predicate)
        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=proposition_family,
                rule=rule,
                language=language,
                evidence_spans=(denial_span, nearest_self),
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "topic_transaction"
                ),
            )
        )
    return output




_ES_KNOWN_ACTORS = frozenset(
    {
        "hermano",
        "hermana",
        "esposo",
        "esposa",
        "pareja",
        "amigo",
        "amiga",
        "hijo",
        "hija",
        "empleado",
        "empleada",
    }
)
_PT_KNOWN_ACTORS = frozenset(
    {
        "irmao",
        "irma",
        "marido",
        "esposa",
        "parceiro",
        "parceira",
        "amigo",
        "amiga",
        "filho",
        "filha",
        "funcionario",
        "funcionaria",
    }
)


def _authorization_participle_forms(language: str) -> frozenset[str]:
    forms: set[str] = set()
    for surface, entries in PARADIGMS[language].items():
        if not any(
            entry.family is PredicateFamily.AUTHORIZE
            and entry.tense_aspect == "participle"
            for entry in entries
        ):
            continue
        forms.add(surface)
        if surface.endswith("o"):
            stem = surface[:-1]
            forms.update({stem + "a", stem + "os", stem + "as"})
    return frozenset(forms)


_AUTH_PARTICIPLES = {
    "es": _authorization_participle_forms("es"),
    "pt": _authorization_participle_forms("pt"),
}


def _auth_noun_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.AUTH_NOUN in analysis.tags[index]
    )


def _known_actor_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    actor_words = _ES_KNOWN_ACTORS if language == "es" else _PT_KNOWN_ACTORS
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if analysis.tokens[index].normalized in actor_words
    )


def _permission_denial_backlink(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[ClauseSegment, tuple[int, int], tuple[int, int] | None, PredicateMatch] | None:
    if clause.index <= 0:
        return None

    prior = analysis.clauses[clause.index - 1]
    actor_spans = _known_actor_spans(analysis, prior, language)
    if not actor_spans:
        return None

    prior_activity = _nearest_activity_span(analysis, prior, None)
    prior_instruments = tuple(
        (index, index + 1)
        for index in range(prior.token_start, prior.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )
    prior_self_possession = _role_spans(
        analysis,
        prior,
        frozenset({SelfRole.POSSESSOR}),
    )

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, prior):
            continue
        if predicate.form.family is PredicateFamily.PERFORM and prior_activity is not None:
            return prior, actor_spans[0], prior_activity, predicate
        if predicate.form.family is PredicateFamily.USE_ACCESS:
            if prior_instruments and prior_self_possession:
                return prior, actor_spans[0], prior_activity, predicate
    return None


def _authorization_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    auth_nouns = _auth_noun_spans(analysis, clause)

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family not in {
            PredicateFamily.AUTHORIZE,
            PredicateFamily.GIVE_PERMISSION,
        }:
            continue
        if not _denial_reference_allowed(
            analysis,
            clause,
            predicate,
            language,
        ):
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
        )
        if self_evidence is None:
            continue

        if predicate.form.family is PredicateFamily.GIVE_PERMISSION:
            nearby_auth_nouns = tuple(
                span
                for span in auth_nouns
                if 0 <= span[0] - predicate.token_end <= 4
                or 0 <= predicate.token_start - span[1] <= 2
            )
            if not nearby_auth_nouns:
                continue
        else:
            nearby_auth_nouns = ()

        activity_span = _nearest_activity_span(analysis, clause, predicate)
        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )

        evidence: list[tuple[int, int]] = [denial_span, nearest_self]
        if nearby_auth_nouns:
            evidence.append(nearby_auth_nouns[0])

        rule = "P4"
        activity_ref = (
            "explicit_activity"
            if activity_span is not None
            else "topic_transaction"
        )

        if (
            predicate.form.family is PredicateFamily.GIVE_PERMISSION
            and activity_span is None
        ):
            backlink = _permission_denial_backlink(analysis, clause, language)
            if backlink is None:
                continue
            _, actor_span, prior_activity, prior_predicate = backlink
            evidence.extend(
                [
                    actor_span,
                    (prior_predicate.token_start, prior_predicate.token_end),
                ]
            )
            if prior_activity is not None:
                activity_span = prior_activity
                activity_ref = "linked_prior_activity"
            else:
                activity_ref = "linked_instrument_use"
            rule = "P4-R3-permission-backlink"

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule=rule,
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output


def _possessive_authorization_absence(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    words = [token.normalized for token in analysis.tokens]
    introducer = "sin" if language == "es" else "sem"
    activity_span = _nearest_activity_span(analysis, clause, None)
    if activity_span is None:
        return []

    possessor_spans = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    auth_nouns = _auth_noun_spans(analysis, clause)
    output: list[PositiveProposition] = []

    for possessor_span in possessor_spans:
        possessor_index = possessor_span[0]
        if possessor_index <= clause.token_start:
            continue
        if words[possessor_index - 1] != introducer:
            continue
        auth_span = next(
            (
                span
                for span in auth_nouns
                if span[0] == possessor_span[1]
            ),
            None,
        )
        if auth_span is None:
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule="P4",
                language=language,
                evidence_spans=(
                    activity_span,
                    (possessor_index - 1, possessor_index),
                    possessor_span,
                    auth_span,
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _unauthorized_participle_denials(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    activity_span = _nearest_activity_span(analysis, clause, None)
    if activity_span is None:
        return []

    negatives = _negative_indices(analysis, clause, language)
    output: list[PositiveProposition] = []
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized not in _AUTH_PARTICIPLES[language]:
            continue
        neg_index = next(
            (
                candidate
                for candidate in reversed(negatives)
                if candidate < index and index - candidate <= 2
            ),
            None,
        )
        if neg_index is None:
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.AUTHORIZATION_DENIAL,
                rule="P4",
                language=language,
                evidence_spans=(
                    activity_span,
                    (neg_index, neg_index + 1),
                    (index, index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output




_ES_PERMISSION_ABSENCE_PHRASES = (
    ("sin", "preguntarme"),
    ("sin", "avisarme"),
    ("a", "escondidas"),
)
_PT_PERMISSION_ABSENCE_PHRASES = (
    ("sem", "me", "perguntar"),
    ("sem", "me", "avisar"),
    ("escondido",),
    ("escondida",),
)


def _customer_instrument_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    instruments = tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )

    linked: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for instrument in instruments:
        possessor = next(
            (
                span
                for span in possessors
                if min(
                    abs(span[0] - instrument[0]),
                    abs(span[1] - instrument[0]),
                )
                <= 2
            ),
            None,
        )
        if possessor is not None:
            linked.append((instrument, possessor))
    return tuple(linked)


_ES_UNKNOWN_ACTOR_WORDS = frozenset({"alguien", "tercero", "tercera"})
_PT_UNKNOWN_ACTOR_WORDS = frozenset({"alguem", "terceiro", "terceira"})


def _unknown_actor_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    actor_words = (
        _ES_UNKNOWN_ACTOR_WORDS
        if language == "es"
        else _PT_UNKNOWN_ACTOR_WORDS
    )
    person_phrase = ("otra", "persona") if language == "es" else ("outra", "pessoa")
    spans: list[tuple[int, int]] = []

    for index in range(clause.token_start, clause.token_end):
        if words[index] in actor_words:
            spans.append((index, index + 1))
        if (
            index + 1 < clause.token_end
            and (words[index], words[index + 1]) == person_phrase
        ):
            spans.append((index, index + 2))

    return tuple(spans)


def _permission_absence_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    phrases = (
        _ES_PERMISSION_ABSENCE_PHRASES
        if language == "es"
        else _PT_PERMISSION_ABSENCE_PHRASES
    )
    spans: list[tuple[int, int]] = []

    introducer = "sin" if language == "es" else "sem"
    auth_nouns = _auth_noun_spans(analysis, clause)
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    for possessor in possessors:
        possessor_index = possessor[0]
        if possessor_index <= clause.token_start:
            continue
        if words[possessor_index - 1] != introducer:
            continue
        auth_span = next(
            (span for span in auth_nouns if span[0] == possessor[1]),
            None,
        )
        if auth_span is not None:
            spans.append((possessor_index - 1, auth_span[1]))

    for auth_span in auth_nouns:
        if auth_span[0] <= clause.token_start:
            continue
        if words[auth_span[0] - 1] == introducer:
            spans.append((auth_span[0] - 1, auth_span[1]))

    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                spans.append((index, index + width))

    negative_indices = set(_negative_indices(analysis, clause, language))
    filtered = tuple(
        span
        for span in dict.fromkeys(spans)
        if span[0] <= clause.token_start
        or (span[0] - 1) not in negative_indices
    )
    return filtered


def _permission_absence_for_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    permission_spans: tuple[tuple[int, int], ...],
) -> tuple[int, int] | None:
    local_spans = tuple(
        span
        for span in permission_spans
        if min(
            abs(span[0] - predicate.token_end),
            abs(predicate.token_start - span[1]),
        )
        <= 6
    )
    ordered = sorted(
        local_spans,
        key=lambda span: min(
            abs(span[0] - predicate.token_end),
            abs(predicate.token_start - span[1]),
        ),
    )

    for span in ordered:
        left = min(span[0], predicate.token_start)
        right = max(span[1], predicate.token_end)
        intervening_action = any(
            candidate.token_start > left
            and candidate.token_start < right
            and not (
                candidate.token_start == predicate.token_start
                and candidate.token_end == predicate.token_end
            )
            and candidate.form.family in {
                PredicateFamily.PERFORM,
                PredicateFamily.USE_ACCESS,
            }
            for candidate in analysis.predicates
            if _in_clause(candidate.token_start, candidate.token_end, clause)
        )
        if not intervening_action:
            return span

    return None


def _third_party_action_allowed(predicate: PredicateMatch) -> bool:
    """Return whether a finite action can represent a non-customer actor."""

    return predicate.form.person != 1


def _third_party_unauthorized_use(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    customer_instruments = _customer_instrument_spans(analysis, clause)
    if not customer_instruments:
        return []

    unknown_actors = _unknown_actor_spans(analysis, clause, language)
    known_actors = _known_actor_spans(analysis, clause, language)
    absence_spans = _permission_absence_spans(analysis, clause, language)
    activity_span = _nearest_activity_span(analysis, clause, None)
    output: list[PositiveProposition] = []

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not PredicateFamily.USE_ACCESS:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if not _third_party_action_allowed(predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue

        actor_span: tuple[int, int] | None = None
        permission_span: tuple[int, int] | None = None
        actor_kind: str | None = None

        preceding_unknown = tuple(
            span for span in unknown_actors if span[0] < predicate.token_start
        )
        if preceding_unknown:
            actor_span = min(
                preceding_unknown,
                key=lambda span: predicate.token_start - span[0],
            )
            actor_kind = "unknown"
        else:
            preceding_known = tuple(
                span for span in known_actors if span[0] < predicate.token_start
            )
            local_permission = _permission_absence_for_predicate(
                analysis,
                clause,
                predicate,
                absence_spans,
            )
            if preceding_known and local_permission is not None:
                actor_span = min(
                    preceding_known,
                    key=lambda span: predicate.token_start - span[0],
                )
                permission_span = local_permission
                actor_kind = "known"

        if actor_span is None or actor_kind is None:
            continue

        instrument_span, possessor_span = min(
            customer_instruments,
            key=lambda item: min(
                abs(item[0][0] - predicate.token_start),
                abs(item[0][0] - predicate.token_end),
            ),
        )

        evidence: list[tuple[int, int]] = [
            actor_span,
            instrument_span,
            possessor_span,
        ]
        if permission_span is not None:
            evidence.append(permission_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else f"{actor_kind}_actor_instrument_use"
                ),
            )
        )

    return output




_ES_FRAUD_NOUNS = frozenset({"fraude", "golpe"})
_PT_FRAUD_NOUNS = frozenset({"fraude", "golpe"})
_ES_FRAUD_ADJECTIVES = frozenset(
    {"fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"}
)
_PT_FRAUD_ADJECTIVES = frozenset(
    {"fraudulento", "fraudulenta", "fraudulentos", "fraudulentas"}
)

_ES_ACTIVITY_FEMININE = frozenset(
    {"compra", "compras", "operacion", "operaciones", "transaccion", "transacciones",
     "transferencia", "transferencias"}
)
_PT_ACTIVITY_FEMININE = frozenset(
    {"cobranca", "cobrancas", "compra", "compras", "operacao", "operacoes",
     "transacao", "transacoes", "transferencia", "transferencias",
     "movimentacao", "movimentacoes", "ted"}
)

_ES_SPECIFIC_DETERMINERS = frozenset(
    {"este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
     "aquel", "aquella", "aquellos", "aquellas", "el", "la", "los", "las"}
)
_PT_SPECIFIC_DETERMINERS = frozenset(
    {"este", "esta", "estes", "estas", "esse", "essa", "esses", "essas",
     "aquele", "aquela", "aqueles", "aquelas", "o", "a", "os", "as"}
)

_ES_THIRD_POSSESSIVES = frozenset({"su", "sus"})
_PT_THIRD_POSSESSIVES = frozenset({"seu", "sua", "seus", "suas"})

_ES_EXPERIENCER_VERBS = frozenset({"tengo", "veo", "recibo", "recibi"})
_PT_EXPERIENCER_VERBS = frozenset({"tenho", "vejo", "recebo", "recebi"})
_ES_DATIVE_EXPERIENCER_VERBS = frozenset({"aparece", "aparecio", "salio"})
_PT_DATIVE_EXPERIENCER_VERBS = frozenset({"aparece", "apareceu", "saiu"})

_ES_PREPOSITIONAL_ACTIVITY = frozenset({"de", "del", "sobre", "para", "por", "con", "en"})
_PT_PREPOSITIONAL_ACTIVITY = frozenset({"de", "do", "da", "sobre", "para", "por", "com", "em", "no", "na"})

_ES_NON_ACTIVITY_FRAUD_HEADS = frozenset(
    {"correo", "email", "mensaje", "sms", "enlace", "link", "sitio", "pagina",
     "llamada", "comercio", "establecimiento", "descriptor", "nombre"}
)
_PT_NON_ACTIVITY_FRAUD_HEADS = frozenset(
    {"email", "mensagem", "sms", "link", "site", "pagina", "ligacao",
     "comercio", "estabelecimento", "descritor", "nome"}
)


def _activity_number(word: str) -> str:
    return "plural" if word.endswith("s") and word not in {"pix"} else "singular"


def _activity_gender(word: str, language: str) -> str:
    feminine = _ES_ACTIVITY_FEMININE if language == "es" else _PT_ACTIVITY_FEMININE
    return "feminine" if word in feminine else "masculine"


def _fraud_adjective_agrees(activity_word: str, fraud_word: str, language: str) -> bool:
    number = _activity_number(activity_word)
    gender = _activity_gender(activity_word, language)

    expected = {
        ("masculine", "singular"): "fraudulento",
        ("feminine", "singular"): "fraudulenta",
        ("masculine", "plural"): "fraudulentos",
        ("feminine", "plural"): "fraudulentas",
    }[(gender, number)]
    return fraud_word == expected


def _third_person_relational_phrase_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    relational_nouns = (
        _ES_RELATIONAL_NOUNS
        if language == "es"
        else _PT_RELATIONAL_NOUNS
    )
    if language == "es":
        prepositions = {"de", "del", "a", "para"}
        possessives = {"mi", "mis", "su", "sus"}
    else:
        prepositions = {"de", "do", "da", "dos", "das", "a", "ao", "aos", "para", "pra"}
        possessives = {"meu", "minha", "meus", "minhas", "seu", "sua", "seus", "suas"}

    spans: list[tuple[int, int]] = []
    for index in range(clause.token_start, clause.token_end - 2):
        if words[index] not in prepositions:
            continue
        if words[index + 1] not in possessives:
            continue
        if (
            language == "es"
            and words[index + 1] == "mi"
            and analysis.tokens[index + 1].had_acute
        ):
            continue
        if words[index + 2] not in relational_nouns:
            continue
        spans.append((index, index + 3))
    return tuple(spans)


def _explicit_third_person_activity_possession(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    words = [token.normalized for token in analysis.tokens]
    index = activity_span[0]
    third_possessives = (
        _ES_THIRD_POSSESSIVES if language == "es" else _PT_THIRD_POSSESSIVES
    )
    if index > clause.token_start and words[index - 1] in third_possessives:
        return True

    if language == "es":
        third_patterns = {
            ("de", "ella"),
            ("de", "ellos"),
            ("de", "ellas"),
            ("de", "otra"),
        }
    else:
        third_patterns = {
            ("de", "outra"),
            ("da", "outra"),
        }

    for start in range(index + 1, min(clause.token_end - 1, index + 4)):
        if (words[start], words[start + 1]) in third_patterns:
            return True
        if language == "pt" and words[start] in {"dela", "dele", "delas", "deles"}:
            return True

    if any(
        min(abs(span[0] - index), abs(span[1] - index)) <= 8
        for span in _third_person_relational_phrase_spans(
            analysis,
            clause,
            language,
        )
    ):
        return True

    return False


def _customer_anchored_activity(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    activity_span: tuple[int, int],
    language: str,
) -> bool:
    if _explicit_third_person_activity_possession(
        analysis, clause, activity_span, language
    ):
        return False

    index = activity_span[0]
    token = analysis.tokens[index]
    words = [item.normalized for item in analysis.tokens]
    if token.is_txid:
        return True

    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    if any(
        span[1] <= index and index - span[1] <= 1
        for span in possessors
    ):
        return True

    determiners = (
        _ES_SPECIFIC_DETERMINERS
        if language == "es"
        else _PT_SPECIFIC_DETERMINERS
    )
    if index > clause.token_start and words[index - 1] in determiners:
        return True

    if index > clause.token_start:
        previous = analysis.tokens[index - 1]
        if previous.normalized.isdigit() or previous.is_txid:
            return True

    experiencer_verbs = (
        _ES_EXPERIENCER_VERBS if language == "es" else _PT_EXPERIENCER_VERBS
    )
    for verb_index in range(max(clause.token_start, index - 5), index):
        if words[verb_index] in experiencer_verbs:
            return True

    dative_verbs = (
        _ES_DATIVE_EXPERIENCER_VERBS
        if language == "es"
        else _PT_DATIVE_EXPERIENCER_VERBS
    )
    dative_spans = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.DATIVE}),
    )
    if dative_spans:
        for verb_index in range(max(clause.token_start, index - 5), index):
            if words[verb_index] in dative_verbs:
                return True

    return False




_ES_EXCEEDED_AMOUNT_MARKERS = (
    ("mas", "de", "lo", "que"),
)
_PT_EXCEEDED_AMOUNT_MARKERS = (
    ("mais", "do", "que"),
    ("alem", "do", "que"),
)
_ES_GRANT_DATIVE_WORDS = frozenset({"le", "les"})
_PT_GRANT_DATIVE_WORDS = frozenset({"lhe", "lhes"})


def _phrase_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    phrases: tuple[tuple[str, ...], ...],
) -> tuple[tuple[int, int], ...]:
    words = [token.normalized for token in analysis.tokens]
    spans: list[tuple[int, int]] = []
    for phrase in phrases:
        width = len(phrase)
        for index in range(clause.token_start, clause.token_end - width + 1):
            if tuple(words[index : index + width]) == phrase:
                spans.append((index, index + width))
    return tuple(spans)


def _nearest_known_actor_before_predicate(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    predicate: PredicateMatch,
) -> tuple[int, int] | None:
    actors = tuple(
        span
        for span in _known_actor_spans(analysis, clause, language)
        if span[0] < predicate.token_start
    )
    if not actors:
        return None
    return min(
        actors,
        key=lambda span: predicate.token_start - span[0],
    )


def _first_person_authorization_after_marker(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    marker_span: tuple[int, int],
) -> PredicateMatch | None:
    candidates = tuple(
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.form.family is PredicateFamily.AUTHORIZE
        and predicate.form.person == 1
        and predicate.token_start >= marker_span[1]
        and predicate.token_start - marker_span[1] <= 5
        and _source_accent_selects_predicate(analysis, predicate)
    )
    if not candidates:
        return None
    return min(candidates, key=lambda predicate: predicate.token_start)


def _exceeded_amount_authorization(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    markers = (
        _ES_EXCEEDED_AMOUNT_MARKERS
        if language == "es"
        else _PT_EXCEEDED_AMOUNT_MARKERS
    )
    marker_spans = _phrase_spans(analysis, clause, markers)
    if not marker_spans:
        return []

    output: list[PositiveProposition] = []
    for marker_span in marker_spans:
        authorization = _first_person_authorization_after_marker(
            analysis,
            clause,
            marker_span,
        )
        if authorization is None:
            continue

        actions = tuple(
            predicate
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
            and predicate.form.family in {
                PredicateFamily.PERFORM,
                PredicateFamily.USE_ACCESS,
            }
            and predicate.token_end <= marker_span[0]
            and marker_span[0] - predicate.token_end <= 6
            and _source_accent_selects_predicate(analysis, predicate)
        )
        if not actions:
            continue
        action = max(actions, key=lambda predicate: predicate.token_start)
        if not _third_party_action_allowed(action):
            continue
        if _predicate_has_denial(analysis, clause, action, language):
            continue

        actor_span = _nearest_known_actor_before_predicate(
            analysis,
            clause,
            language,
            action,
        )
        if actor_span is None:
            continue

        activity_span = _nearest_activity_span(analysis, clause, action)
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5-exceeded-authorization-amount",
                language=language,
                evidence_spans=(
                    actor_span,
                    marker_span,
                    (action.token_start, action.token_end),
                    (authorization.token_start, authorization.token_end),
                ),
                activity_span=activity_span,
                predicate=action,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "known_actor_exceeded_authorized_amount"
                ),
            )
        )
    return output


def _limited_grant_recipient(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    action: PredicateMatch,
) -> tuple[int, int] | None:
    words = [token.normalized for token in analysis.tokens]
    dative_words = (
        _ES_GRANT_DATIVE_WORDS
        if language == "es"
        else _PT_GRANT_DATIVE_WORDS
    )

    grants = tuple(
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, clause)
        and predicate.form.family is PredicateFamily.GIVE_PERMISSION
        and predicate.form.person == 1
        and predicate.token_end < action.token_start
        and action.token_start - predicate.token_end <= 14
        and _source_accent_selects_predicate(analysis, predicate)
    )
    for grant in reversed(grants):
        instrument_span = next(
            (
                (index, index + 1)
                for index in range(grant.token_end, action.token_start)
                if LexicalTag.INSTRUMENT in analysis.tags[index]
            ),
            None,
        )
        if instrument_span is None:
            continue

        purpose_index = next(
            (
                index
                for index in range(instrument_span[1], action.token_start)
                if words[index] == "para"
            ),
            None,
        )
        if purpose_index is None:
            continue

        dative_span = next(
            (
                (index, index + 1)
                for index in range(
                    max(clause.token_start, grant.token_start - 2),
                    min(action.token_start, grant.token_end + 3),
                )
                if words[index] in dative_words
            ),
            None,
        )
        if dative_span is not None:
            return dative_span

        known_actor = next(
            (
                span
                for span in _known_actor_spans(analysis, clause, language)
                if grant.token_start <= span[0] < action.token_start
            ),
            None,
        )
        if known_actor is not None:
            return known_actor

    return None


def _exceeded_purpose_authorization(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    permission_spans = _permission_absence_spans(
        analysis,
        clause,
        language,
    )
    if not permission_spans:
        return []

    output: list[PositiveProposition] = []
    for action in analysis.predicates:
        if not _in_clause(action.token_start, action.token_end, clause):
            continue
        if action.form.family is not PredicateFamily.PERFORM:
            continue
        if not _third_party_action_allowed(action):
            continue
        if not _source_accent_selects_predicate(analysis, action):
            continue
        if _predicate_has_denial(analysis, clause, action, language):
            continue

        later_permission = tuple(
            span
            for span in permission_spans
            if span[0] >= action.token_end
            and span[0] - action.token_end <= 6
        )
        if not later_permission:
            continue
        permission_span = min(later_permission, key=lambda span: span[0])

        grant_recipient = _limited_grant_recipient(
            analysis,
            clause,
            language,
            action,
        )
        if grant_recipient is None:
            continue

        actor_span = _nearest_known_actor_before_predicate(
            analysis,
            clause,
            language,
            action,
        )
        if actor_span is None:
            actor_span = grant_recipient

        activity_span = _nearest_activity_span(analysis, clause, action)
        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.THIRD_PARTY_UNAUTHORIZED_USE,
                rule="P5-exceeded-authorization-purpose",
                language=language,
                evidence_spans=(
                    actor_span,
                    permission_span,
                    (action.token_start, action.token_end),
                ),
                activity_span=activity_span,
                predicate=action,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "known_actor_exceeded_authorized_purpose"
                ),
            )
        )
    return output


def _exceeded_authorization_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    return [
        *_exceeded_amount_authorization(analysis, clause, language),
        *_exceeded_purpose_authorization(analysis, clause, language),
    ]


def _fraud_marker_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], ...]:
    nouns = _ES_FRAUD_NOUNS if language == "es" else _PT_FRAUD_NOUNS
    adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if analysis.tokens[index].normalized in nouns | adjectives
    )


def _fraud_attributive_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    output: list[PositiveProposition] = []

    for activity_span in _activity_spans(analysis, clause):
        if not _customer_anchored_activity(analysis, clause, activity_span, language):
            continue
        marker_index = activity_span[1]
        if marker_index >= clause.token_end:
            continue
        marker_word = analysis.tokens[marker_index].normalized
        if marker_word not in adjectives:
            continue
        if _span_has_bound_denial(
            analysis,
            clause,
            marker_index,
            marker_index + 1,
            language,
        ):
            continue
        activity_word = analysis.tokens[activity_span[0]].normalized
        if not _fraud_adjective_agrees(activity_word, marker_word, language):
            continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.FRAUD_CHARACTERIZATION,
                rule="P6-attributive",
                language=language,
                evidence_spans=(activity_span, (marker_index, marker_index + 1)),
                activity_span=activity_span,
                predicate=None,
            )
        )
    return output


def _fraud_copular_propositions(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    words = [token.normalized for token in analysis.tokens]
    copulas = _ES_COPULA if language == "es" else _PT_COPULA
    fraud_nouns = _ES_FRAUD_NOUNS if language == "es" else _PT_FRAUD_NOUNS
    fraud_adjectives = (
        _ES_FRAUD_ADJECTIVES if language == "es" else _PT_FRAUD_ADJECTIVES
    )
    non_activity_heads = (
        _ES_NON_ACTIVITY_FRAUD_HEADS
        if language == "es"
        else _PT_NON_ACTIVITY_FRAUD_HEADS
    )
    prepositions = (
        _ES_PREPOSITIONAL_ACTIVITY
        if language == "es"
        else _PT_PREPOSITIONAL_ACTIVITY
    )
    output: list[PositiveProposition] = []

    for copula_index in range(clause.token_start, clause.token_end):
        token = analysis.tokens[copula_index]
        if token.normalized not in copulas:
            continue
        if language == "pt" and token.normalized == "e" and not token.had_acute:
            continue
        if _span_has_bound_denial(
            analysis,
            clause,
            copula_index,
            copula_index + 1,
            language,
        ):
            continue

        marker_index = next(
            (
                index
                for index in range(copula_index + 1, min(clause.token_end, copula_index + 7))
                if words[index] in fraud_nouns | fraud_adjectives
            ),
            None,
        )
        if marker_index is None:
            continue

        candidate_activities = [
            span
            for span in _activity_spans(analysis, clause)
            if span[0] < copula_index
            and copula_index - span[0] <= 8
            and _customer_anchored_activity(analysis, clause, span, language)
        ]
        if not candidate_activities:
            continue

        activity_span = max(candidate_activities, key=lambda span: span[0])
        activity_index = activity_span[0]
        if (
            activity_index > clause.token_start
            and words[activity_index - 1] in prepositions
        ):
            continue

        head_between = any(
            words[index] in non_activity_heads
            for index in range(activity_span[1], copula_index)
        )
        if head_between:
            continue

        predicate_path_blocked = any(
            words[index] in non_activity_heads
            or LexicalTag.ACTIVITY in analysis.tags[index]
            or (
                words[index] in copulas
                and not (
                    language == "pt"
                    and words[index] == "e"
                    and not analysis.tokens[index].had_acute
                )
            )
            for index in range(copula_index + 1, marker_index)
        )
        if predicate_path_blocked:
            continue

        marker_word = words[marker_index]
        if marker_word in fraud_adjectives:
            activity_word = words[activity_index]
            if not _fraud_adjective_agrees(activity_word, marker_word, language):
                continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.FRAUD_CHARACTERIZATION,
                rule="P6-copular",
                language=language,
                evidence_spans=(
                    activity_span,
                    (copula_index, copula_index + 1),
                    (marker_index, marker_index + 1),
                ),
                activity_span=activity_span,
                predicate=None,
            )
        )

    return output


def _fraud_characterizations(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    return [
        *_fraud_attributive_propositions(analysis, clause, language),
        *_fraud_copular_propositions(analysis, clause, language),
    ]




_ES_ACTIVITY_ANAPHORS = frozenset(
    {"lo", "la", "los", "las", "esto", "eso", "aquello", "este", "esta", "ese", "esa"}
)
_PT_ACTIVITY_ANAPHORS = frozenset(
    {"isso", "isto", "aquilo", "este", "esta", "esse", "essa", "o", "a"}
)


def _p7_nominal_target(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[str, tuple[int, int] | None]:
    tagged: list[tuple[int, str]] = []
    for index in range(predicate.token_end, clause.token_end):
        if LexicalTag.ACTIVITY in analysis.tags[index]:
            tagged.append((index, "activity"))
        if LexicalTag.DESCRIPTOR_NOUN in analysis.tags[index]:
            tagged.append((index, "descriptor"))

    if tagged:
        index, kind = min(tagged, key=lambda item: item[0])
        return kind, (index, index + 1)

    tagged_before: list[tuple[int, str]] = []
    for index in range(clause.token_start, predicate.token_start):
        if LexicalTag.ACTIVITY in analysis.tags[index]:
            tagged_before.append((index, "activity"))
        if LexicalTag.DESCRIPTOR_NOUN in analysis.tags[index]:
            tagged_before.append((index, "descriptor"))

    if tagged_before:
        index, kind = min(tagged_before, key=lambda item: item[0])
        return kind, (index, index + 1)

    return "none", None


def _p7_has_activity_anaphor(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    predicate: PredicateMatch,
    language: str,
) -> tuple[int, int] | None:
    anaphors = _ES_ACTIVITY_ANAPHORS if language == "es" else _PT_ACTIVITY_ANAPHORS
    words = [token.normalized for token in analysis.tokens]

    candidates: list[int] = []
    for index in range(
        max(clause.token_start, predicate.token_start - 3),
        min(clause.token_end, predicate.token_end + 4),
    ):
        if words[index] in anaphors:
            candidates.append(index)

    if not candidates:
        return None

    index = min(
        candidates,
        key=lambda item: min(
            abs(item - predicate.token_start),
            abs(item - predicate.token_end),
        ),
    )
    return (index, index + 1)


def _nearest_preceding_activity_or_txid(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], str] | None:
    prior_clauses = [
        prior for prior in analysis.clauses
        if prior.index < clause.index
    ]
    for prior in reversed(prior_clauses):
        for index in range(prior.token_end - 1, prior.token_start - 1, -1):
            if analysis.tokens[index].is_txid:
                return (index, index + 1), "linked_prior_txid"
            if LexicalTag.ACTIVITY not in analysis.tags[index]:
                continue
            activity_span = (index, index + 1)
            if _customer_anchored_activity(
                analysis,
                prior,
                activity_span,
                language,
            ):
                return activity_span, "linked_prior_activity"
    return None


def _activity_nonrecognition(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not PredicateFamily.RECOGNIZE:
            continue
        if not _predicate_has_denial(analysis, clause, predicate, language):
            continue

        self_evidence = _bound_self_evidence(
            analysis,
            clause,
            predicate,
            frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
        )
        if self_evidence is None:
            continue

        target_kind, target_span = _p7_nominal_target(
            analysis,
            clause,
            predicate,
            language,
        )
        if target_kind == "descriptor":
            continue

        denial_index = _bound_denial_index(
            analysis,
            clause,
            predicate,
            language,
        )
        if denial_index is None:
            continue
        denial_span = (denial_index, denial_index + 1)
        nearest_self = (
            self_evidence.token_start,
            self_evidence.token_end,
        )
        evidence: list[tuple[int, int]] = [denial_span, nearest_self]
        activity_span: tuple[int, int] | None = None
        activity_ref = "topic_transaction"
        rule = "P7"

        if target_kind == "activity" and target_span is not None:
            if not _customer_anchored_activity(
                analysis,
                clause,
                target_span,
                language,
            ):
                continue
            activity_span = target_span
            activity_ref = "explicit_activity"
            evidence.append(target_span)
        else:
            anaphor_span = _p7_has_activity_anaphor(
                analysis,
                clause,
                predicate,
                language,
            )
            if anaphor_span is not None:
                evidence.append(anaphor_span)

            prior = _nearest_preceding_activity_or_txid(
                analysis,
                clause,
                language,
            )
            if prior is not None:
                activity_span, activity_ref = prior
                evidence.append(activity_span)
                rule = "P7-R3-activity-anaphora"
            elif anaphor_span is not None or predicate.form.person == 1:
                activity_ref = "topic_transaction"
                rule = "P7-R3-topic-default"
            else:
                continue

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.ACTIVITY_NONRECOGNITION,
                rule=rule,
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output




_ES_COMPROMISE_PARTICIPLES = frozenset(
    {
        "robado", "robada", "robados", "robadas",
        "clonado", "clonada", "clonados", "clonadas",
        "hackeado", "hackeada", "hackeados", "hackeadas",
    }
)
_PT_COMPROMISE_PARTICIPLES = frozenset(
    {
        "roubado", "roubada", "roubados", "roubadas",
        "furtado", "furtada", "furtados", "furtadas",
        "clonado", "clonada", "clonados", "clonadas",
        "hackeado", "hackeada", "hackeados", "hackeadas",
        "invadido", "invadida", "invadidos", "invadidas",
    }
)


def _instrument_spans(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (index, index + 1)
        for index in range(clause.token_start, clause.token_end)
        if LexicalTag.INSTRUMENT in analysis.tags[index]
    )


def _self_dative_near_span(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    span: tuple[int, int],
    *,
    max_before_gap: int,
) -> tuple[int, int] | None:
    datives = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.DATIVE}),
    )
    preceding = tuple(
        item
        for item in datives
        if item[1] <= span[0]
        and span[0] - item[1] <= max_before_gap
        and not any(
            predicate.token_start >= item[1]
            and predicate.token_end <= span[0]
            and predicate.form.person is not None
            and not predicate.accent_ambiguous
            for predicate in analysis.predicates
            if _in_clause(predicate.token_start, predicate.token_end, clause)
        )
        and not any(
            analysis.tokens[index].normalized == "que"
            for index in range(item[1], span[0])
        )
    )
    if not preceding:
        return None
    return min(preceding, key=lambda item: span[0] - item[1])


def _nearest_eligible_compromise_instrument(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
    anchor_span: tuple[int, int],
) -> tuple[tuple[int, int], tuple[int, int] | None] | None:
    possessors = _role_spans(
        analysis,
        clause,
        frozenset({SelfRole.POSSESSOR}),
    )
    explicit_customer: dict[tuple[int, int], tuple[int, int]] = {}
    for instrument in _instrument_spans(analysis, clause):
        direct_possessor = next(
            (
                possessor
                for possessor in possessors
                if possessor[1] == instrument[0]
                or possessor[0] == instrument[1]
            ),
            None,
        )
        if direct_possessor is not None:
            explicit_customer[instrument] = direct_possessor

    candidates: list[
        tuple[tuple[int, int], tuple[int, int] | None]
    ] = []
    for instrument in _instrument_spans(analysis, clause):
        if _explicit_third_person_activity_possession(
            analysis,
            clause,
            instrument,
            language,
        ):
            continue
        if instrument in explicit_customer:
            candidates.append((instrument, explicit_customer[instrument]))
            continue

        dative = _self_dative_near_span(
            analysis,
            clause,
            anchor_span,
            max_before_gap=2,
        )
        if dative is not None:
            candidates.append((instrument, dative))

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda item: min(
            abs(item[0][0] - anchor_span[0]),
            abs(item[0][0] - anchor_span[1]),
        ),
    )


def _source_accent_selects_predicate(
    analysis: FoundationAnalysis,
    predicate: PredicateMatch,
) -> bool:
    if predicate.token_end - predicate.token_start != 1:
        return True

    token = analysis.tokens[predicate.token_start]
    if not token.had_acute:
        return True

    same_span_family = tuple(
        candidate
        for candidate in analysis.predicates
        if candidate.token_start == predicate.token_start
        and candidate.token_end == predicate.token_end
        and candidate.form.family is predicate.form.family
    )
    if not any(candidate.form.accent_required for candidate in same_span_family):
        return True

    return predicate.form.accent_required


def _first_person_compromise(
    analysis: FoundationAnalysis,
    clause: ClauseSegment,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []
    activity_span = _nearest_activity_span(analysis, clause, None)

    for predicate in analysis.predicates:
        if not _in_clause(predicate.token_start, predicate.token_end, clause):
            continue
        if predicate.form.family is not PredicateFamily.COMPROMISE:
            continue
        if not _source_accent_selects_predicate(analysis, predicate):
            continue
        if _predicate_has_denial(analysis, clause, predicate, language):
            continue

        # P8 models the customer as affected owner/experiencer, not actor.
        if predicate.form.person == 1:
            continue

        predicate_span = (predicate.token_start, predicate.token_end)
        instrument_evidence = _nearest_eligible_compromise_instrument(
            analysis,
            clause,
            language,
            predicate_span,
        )
        if instrument_evidence is None:
            continue

        instrument_span, customer_span = instrument_evidence
        evidence: list[tuple[int, int]] = [instrument_span]
        if customer_span is not None:
            evidence.append(customer_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
                rule="P8-first-person-compromise",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "customer_instrument_compromise"
                ),
            )
        )

    participles = (
        _ES_COMPROMISE_PARTICIPLES
        if language == "es"
        else _PT_COMPROMISE_PARTICIPLES
    )
    for index in range(clause.token_start, clause.token_end):
        if analysis.tokens[index].normalized not in participles:
            continue

        participle_span = (index, index + 1)
        directly_negated = _span_has_bound_denial(
            analysis,
            clause,
            index,
            index + 1,
            language,
        )
        copulas = _ES_COPULA if language == "es" else _PT_COPULA
        negated_auxiliary = any(
            analysis.tokens[aux].normalized in copulas
            and _span_has_bound_denial(
                analysis,
                clause,
                aux,
                aux + 1,
                language,
            )
            for aux in range(max(clause.token_start, index - 3), index)
        )
        if directly_negated or negated_auxiliary:
            continue

        instrument_evidence = _nearest_eligible_compromise_instrument(
            analysis,
            clause,
            language,
            participle_span,
        )
        if instrument_evidence is None:
            continue

        instrument_span, customer_span = instrument_evidence
        evidence: list[tuple[int, int]] = [instrument_span, participle_span]
        if customer_span is not None:
            evidence.append(customer_span)

        output.append(
            _make_proposition(
                analysis,
                clause,
                family=PropositionFamily.COMPROMISE_LINKED_ACTIVITY,
                rule="P8-first-person-compromise-participle",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=None,
                activity_ref=(
                    "explicit_activity"
                    if activity_span is not None
                    else "customer_instrument_compromise"
                ),
            )
        )

    return output




_D1_INHERITABLE_FAMILIES: dict[
    PredicateFamily,
    PropositionFamily,
] = {
    PredicateFamily.PERFORM: PropositionFamily.PERFORMANCE_DENIAL,
    PredicateFamily.ORIGINATE: PropositionFamily.ORIGINATION_DENIAL,
    PredicateFamily.AUTHORIZE: PropositionFamily.AUTHORIZATION_DENIAL,
    PredicateFamily.RECOGNIZE: PropositionFamily.ACTIVITY_NONRECOGNITION,
}


def _d1_is_whitespace_dash(text: str, token: Token) -> bool:
    if token.surface not in {"-", "–", "—"}:
        return False
    before_ok = token.start == 0 or text[token.start - 1].isspace()
    after_ok = token.end == len(text) or text[token.end].isspace()
    return before_ok and after_ok


def _d1_separator_indices(
    analysis: FoundationAnalysis,
    text: str,
) -> tuple[int, ...]:
    output: list[int] = []
    for index, token in enumerate(analysis.tokens):
        if token.surface == ",":
            if not _is_numeric_punctuation(text, token):
                output.append(index)
            continue
        if token.surface == ";":
            output.append(index)
            continue
        if _d1_is_whitespace_dash(text, token):
            output.append(index)
    return tuple(output)


def _d1_segment_bounds(
    analysis: FoundationAnalysis,
    text: str,
    separator_index: int,
) -> tuple[ClauseSegment, ClauseSegment] | None:
    prefix_start = 0
    for index in range(separator_index - 1, -1, -1):
        if _is_primary_boundary(text, analysis.tokens[index]):
            prefix_start = index + 1
            break

    suffix_end = len(analysis.tokens)
    for index in range(separator_index + 1, len(analysis.tokens)):
        if _is_primary_boundary(text, analysis.tokens[index]):
            suffix_end = index
            break

    if prefix_start >= separator_index or separator_index + 1 >= suffix_end:
        return None

    prefix = ClauseSegment(
        index=-1,
        token_start=prefix_start,
        token_end=separator_index,
        source_start=analysis.tokens[prefix_start].start,
        source_end=analysis.tokens[separator_index - 1].end,
    )
    suffix = ClauseSegment(
        index=-1,
        token_start=separator_index + 1,
        token_end=suffix_end,
        source_start=analysis.tokens[separator_index + 1].start,
        source_end=analysis.tokens[suffix_end - 1].end,
    )
    return prefix, suffix


def _d1_closed_continuation(
    analysis: FoundationAnalysis,
    suffix: ClauseSegment,
    language: str,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    finite_predicate = any(
        _in_clause(predicate.token_start, predicate.token_end, suffix)
        and predicate.form.person is not None
        for predicate in analysis.predicates
    )
    if finite_predicate:
        return None

    words = [
        analysis.tokens[index].normalized
        for index in range(suffix.token_start, suffix.token_end)
        if analysis.tokens[index].surface != ","
    ]
    if not words:
        return None

    if language == "es":
        starts_closed = (
            len(words) >= 2 and words[0] == "ni" and words[1] in {"yo", "nosotros", "nosotras"}
        ) or (
            len(words) >= 2 and words[0] in {"yo", "nosotros", "nosotras"} and words[1] == "tampoco"
        )
    else:
        starts_closed = (
            len(words) >= 2 and words[0] == "nem" and words[1] in {"eu", "nos"}
        ) or (
            len(words) >= 2
            and words[0] in {"eu", "nos"}
            and (
                words[1] == "tampouco"
                or (
                    len(words) >= 3
                    and words[1] == "tambem"
                    and words[2] == "nao"
                )
            )
        )
    if not starts_closed:
        return None

    self_spans = _role_spans(
        analysis,
        suffix,
        frozenset({SelfRole.SUBJECT}),
    )
    if not self_spans:
        return None

    coord_word = "ni" if language == "es" else "nem"
    marker_index = next(
        (
            index
            for index in range(suffix.token_start, suffix.token_end)
            if analysis.tokens[index].normalized in {
                coord_word,
                "tampoco",
                "tampouco",
                "tambem",
                "nao",
            }
        ),
        None,
    )
    if marker_index is None:
        return None

    return self_spans[0], (marker_index, marker_index + 1)


def _d1_prior_frame(
    analysis: FoundationAnalysis,
    prefix: ClauseSegment,
    language: str,
) -> tuple[PredicateMatch, tuple[int, int] | None, tuple[int, int], PropositionFamily] | None:
    candidates = [
        predicate
        for predicate in analysis.predicates
        if _in_clause(predicate.token_start, predicate.token_end, prefix)
        and predicate.form.family in _D1_INHERITABLE_FAMILIES
        and predicate.form.person is not None
        and _predicate_has_denial(analysis, prefix, predicate, language)
    ]
    if not candidates:
        return None

    predicate = max(candidates, key=lambda item: item.token_start)
    denial_index = _bound_denial_index(
        analysis,
        prefix,
        predicate,
        language,
    )
    if denial_index is None:
        return None

    denial_span = (denial_index, denial_index + 1)
    activity_span = _nearest_activity_span(analysis, prefix, predicate)
    family = _D1_INHERITABLE_FAMILIES[predicate.form.family]
    return predicate, activity_span, denial_span, family


def _elliptical_continuations(
    analysis: FoundationAnalysis,
    text: str,
    language: str,
) -> list[PositiveProposition]:
    output: list[PositiveProposition] = []

    for separator_index in _d1_separator_indices(analysis, text):
        bounds = _d1_segment_bounds(analysis, text, separator_index)
        if bounds is None:
            continue
        prefix, suffix = bounds

        continuation = _d1_closed_continuation(
            analysis,
            suffix,
            language,
        )
        if continuation is None:
            continue
        self_span, continuation_marker = continuation

        frame = _d1_prior_frame(
            analysis,
            prefix,
            language,
        )
        if frame is None:
            continue
        predicate, activity_span, denial_span, family = frame

        if family is PropositionFamily.ACTIVITY_NONRECOGNITION:
            if activity_span is None:
                activity_ref = "topic_transaction"
            elif not _customer_anchored_activity(
                analysis,
                prefix,
                activity_span,
                language,
            ):
                continue
            else:
                activity_ref = "linked_prior_activity"
        else:
            activity_ref = (
                "linked_prior_activity"
                if activity_span is not None
                else "topic_transaction"
            )

        evidence = [
            denial_span,
            self_span,
            continuation_marker,
            (predicate.token_start, predicate.token_end),
        ]
        if activity_span is not None:
            evidence.append(activity_span)

        containing_clause = next(
            (
                clause
                for clause in analysis.clauses
                if _in_clause(self_span[0], self_span[1], clause)
            ),
            suffix,
        )

        output.append(
            _make_proposition(
                analysis,
                containing_clause,
                family=family,
                rule="R3-D1-elliptical-continuation",
                language=language,
                evidence_spans=evidence,
                activity_span=activity_span,
                predicate=predicate,
                activity_ref=activity_ref,
            )
        )

    return output


def build_positive_propositions(
    text: str,
    language: str,
) -> tuple[PositiveProposition, ...]:
    """Construct unresolved RF1H-B2 positive propositions.

    This API is intentionally internal to the grammar engine. It does not apply
    B3 scope/exclusion or message-level retraction and is not wired into the
    production boolean classifier.
    """

    analysis = analyze_foundation(text, language)
    propositions: list[PositiveProposition] = []

    for clause in analysis.clauses:
        propositions.extend(_ownership_denials(analysis, clause, language))
        propositions.extend(_alienation_denials(analysis, clause, language))
        propositions.extend(
            _predicate_denials(
                analysis,
                clause,
                language,
                predicate_family=PredicateFamily.PERFORM,
                proposition_family=PropositionFamily.PERFORMANCE_DENIAL,
                rule="P2",
                self_roles=frozenset({SelfRole.SUBJECT, SelfRole.AGENT}),
            )
        )
        propositions.extend(
            _predicate_denials(
                analysis,
                clause,
                language,
                predicate_family=PredicateFamily.ORIGINATE,
                proposition_family=PropositionFamily.ORIGINATION_DENIAL,
                rule="P3",
                self_roles=frozenset({SelfRole.SOURCE}),
            )
        )
        propositions.extend(_authorization_denials(analysis, clause, language))
        propositions.extend(
            _possessive_authorization_absence(analysis, clause, language)
        )
        propositions.extend(
            _unauthorized_participle_denials(analysis, clause, language)
        )
        propositions.extend(
            _third_party_unauthorized_use(analysis, clause, language)
        )
        propositions.extend(
            _exceeded_authorization_propositions(
                analysis,
                clause,
                language,
            )
        )
        propositions.extend(
            _fraud_characterizations(analysis, clause, language)
        )
        propositions.extend(
            _activity_nonrecognition(analysis, clause, language)
        )
        propositions.extend(
            _first_person_compromise(analysis, clause, language)
        )

    propositions.extend(
        _elliptical_continuations(analysis, text, language)
    )

    unique: dict[
        tuple[str, str, int, int, int, str, tuple[int, int] | None],
        PositiveProposition,
    ] = {}
    for proposition in propositions:
        key = (
            proposition.family.value,
            proposition.rule,
            proposition.clause_index,
            proposition.token_start,
            proposition.token_end,
            proposition.activity_ref,
            proposition.predicate_token_span,
        )
        unique[key] = proposition
    return tuple(unique.values())


def dump_positive_propositions(
    text: str,
    language: str,
) -> tuple[dict[str, object], ...]:
    """Return a compact source-grounded debug view for proposition-level tests."""

    propositions = build_positive_propositions(text, language)
    return tuple(
        {
            "family": proposition.family.value,
            "rule": proposition.rule,
            "clause_index": proposition.clause_index,
            "activity_ref": proposition.activity_ref,
            "source": text[proposition.source_start : proposition.source_end],
            "mode": proposition.mode,
        }
        for proposition in propositions
    )
