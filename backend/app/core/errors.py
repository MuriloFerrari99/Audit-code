"""Taxonomia de erros (T-026, ADR-15).

- DataError: erro de dado (FK não resolve, campo faltante) -> dead-letter, não
  derruba o batch.
- TransientError: 5xx/429/timeout -> retry com backoff/jitter + circuit breaker.
- ProgrammingError: bug -> falha alta + alerta.
- DomainError: violação de regra de negócio (ex.: tenant ausente no contexto).
"""

from __future__ import annotations


class AppError(Exception):
    """Base de todos os erros da aplicação."""


class DataError(AppError):
    """Dado de origem inconsistente. Vai para dead-letter, revisável."""


class TransientError(AppError):
    """Falha temporária; elegível a retry."""


class ProgrammingError(AppError):
    """Erro de programação; não deve acontecer em produção."""


class DomainError(AppError):
    """Violação de invariante de negócio (ex.: isolamento, autorização)."""


class TenantContextMissing(DomainError):
    """Operação de dado de cliente sem tenant fixado no contexto (ADR-08)."""
