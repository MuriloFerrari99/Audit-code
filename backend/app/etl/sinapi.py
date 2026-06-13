"""ETL de referência SINAPI (T-070, fontes-dados.md / ground-truth.md Camada 1).

Carrega um CSV (código/UF/período/unidade/preço/regime) para sinapi_reference.
Referência é pública (sem RLS). Idempotente por (código, UF, período, regime).

Uso: python -m app.etl.sinapi /caminho/sinapi.csv
"""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.core.db import admin_session
from app.core.logging import get_logger
from app.models.catalog import SinapiReference

log = get_logger("etl.sinapi")


def load_sinapi_csv(path: str | Path) -> int:
    path = Path(path)
    count = 0
    with admin_session() as s, path.open() as fh:
        for row in csv.DictReader(fh):
            existing = s.execute(
                select(SinapiReference).where(
                    SinapiReference.sinapi_code == row["sinapi_code"],
                    SinapiReference.state == row["state"],
                    SinapiReference.period == row["period"],
                    SinapiReference.regime == row.get("regime", "desonerado"),
                )
            ).scalar_one_or_none()
            if existing:
                existing.price = Decimal(row["price"])
                existing.unit = row.get("unit")
            else:
                s.add(
                    SinapiReference(
                        sinapi_code=row["sinapi_code"],
                        state=row["state"],
                        period=row["period"],
                        unit=row.get("unit"),
                        price=Decimal(row["price"]),
                        regime=row.get("regime", "desonerado"),
                    )
                )
            count += 1
    log.info("etl.sinapi.loaded", rows=count, file=str(path))
    return count


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "../reference-data/sinapi_sample.csv"
    print("linhas carregadas:", load_sinapi_csv(target))
