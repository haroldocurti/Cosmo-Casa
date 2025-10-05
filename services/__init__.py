"""Pacote de serviços: expõe utilitários compartilhados.

Atualmente centraliza o acesso ao banco via `db_manager`.
"""

try:
    from .db import db_manager
except Exception:  # pragma: no cover
    db_manager = None