"""Runner do worker (T-067/T-043).

No MVP o worker processa: (1) jobs de sync incremental, (2) consumo do
outbox -> reavaliação de regras, (3) jobs de ML. Implementação das filas
entra nos épicos E6/E9; aqui fica o ponto de entrada.
"""

from __future__ import annotations

import time

from app.core.logging import configure_logging, get_logger

log = get_logger("worker")


def main() -> None:
    configure_logging()
    log.info("worker.start", note="placeholder — filas RQ entram em E6/E9")
    # TODO(E6/E9): conectar ao Redis e consumir as filas (sync, outbox, ml).
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
