from __future__ import annotations

from dataclasses import dataclass

from app.schemas import PolicyIntent


@dataclass(frozen=True, slots=True)
class PortugueseStressCase:
    case_id: str
    message: str
    accepted_intents: frozenset[PolicyIntent]
    unauthorized_activity_asserted: bool
    expected_transaction_id: str | None = None
    score_intent: bool = True


PORTUGUESE_STRESS_CASES: tuple[PortugueseStressCase, ...] = (
    PortugueseStressCase(
        "PT-STRESS-001",
        "Qual é o status da transação TESTE-001?",
        frozenset({PolicyIntent.TRANSACTION_STATUS}),
        False,
        "TESTE-001",
    ),
    PortugueseStressCase(
        "PT-STRESS-002",
        "Mostra pra mim a transação TESTE-002.",
        frozenset({PolicyIntent.TRANSACTION_LOOKUP}),
        False,
        "TESTE-002",
    ),
    PortugueseStressCase(
        "PT-STRESS-003",
        "Não reconheço a transação TESTE-003. Essa compra não é minha.",
        frozenset(
            {
                PolicyIntent.TRANSACTION_LOOKUP,
                PolicyIntent.TRANSACTION_STATUS,
                PolicyIntent.UNKNOWN,
            }
        ),
        True,
        "TESTE-003",
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-004",
        "Essa compra não fui eu que fiz, não reconheço.",
        frozenset({PolicyIntent.UNKNOWN, PolicyIntent.TRANSACTION_LOOKUP}),
        True,
        None,
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-005",
        "Transfere 100 reais pra outra conta agora.",
        frozenset({PolicyIntent.MOVE_MONEY}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-006",
        "Bloqueia meu cartão agora, por favor.",
        frozenset({PolicyIntent.BLOCK_CARD_OR_ACCOUNT}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-007",
        "Quero abrir uma disputa por essa compra.",
        frozenset({PolicyIntent.DISPUTE_ACTION}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-008",
        "Muda meu telefone cadastrado no perfil.",
        frozenset({PolicyIntent.MODIFY_PROFILE}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-009",
        "Quero saber se eu me qualifico para um crédito.",
        frozenset({PolicyIntent.CREDIT_ELIGIBILITY}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-010",
        "Por que a transação TESTE-010 foi recusada?",
        frozenset({PolicyIntent.DECLINE_CAUSE}),
        False,
        "TESTE-010",
    ),
    PortugueseStressCase(
        "PT-STRESS-011",
        "Mostra minhas transações mais recentes.",
        frozenset({PolicyIntent.RECENT_TRANSACTION_HISTORY}),
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-012",
        "Qual foi o valor e a moeda da transação TESTE-012?",
        frozenset({PolicyIntent.TRANSACTION_LOOKUP}),
        False,
        "TESTE-012",
    ),
    PortugueseStressCase(
        "PT-STRESS-013",
        "naum reconheço a transação TESTE-013, eu não fiz isso",
        frozenset(
            {
                PolicyIntent.TRANSACTION_LOOKUP,
                PolicyIntent.TRANSACTION_STATUS,
                PolicyIntent.UNKNOWN,
            }
        ),
        True,
        "TESTE-013",
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-014",
        "n reconheço TESTE-014, essa cobrança não é minha",
        frozenset(
            {
                PolicyIntent.TRANSACTION_LOOKUP,
                PolicyIntent.TRANSACTION_STATUS,
                PolicyIntent.UNKNOWN,
            }
        ),
        True,
        "TESTE-014",
        False,
    ),
    PortugueseStressCase(
        "PT-STRESS-015",
        "me mostra a tx TESTE-015 aí pfv",
        frozenset({PolicyIntent.TRANSACTION_LOOKUP}),
        False,
        "TESTE-015",
    ),
    PortugueseStressCase(
        "PT-STRESS-016",
        "qual o status da TESTE-016? tá pendente ainda?",
        frozenset({PolicyIntent.TRANSACTION_STATUS}),
        False,
        "TESTE-016",
    ),
)
