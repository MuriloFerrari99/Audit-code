"""OpenSquad — pipeline de 4 agentes orientado a eventos sobre o CDM.

Extrator -> Enriquecedor -> Auditor -> Executor. Cada passo grava um
AgentReasoningLog (explicabilidade). O squad depende só do CDM e das Ports —
agnóstico a país/setor/ERP.
"""

from app.agents.squad.auditor import AuditorAgent
from app.agents.squad.base import AgentResult, SquadAgent, SquadContext, new_run_id
from app.agents.squad.enricher import EnricherAgent
from app.agents.squad.events import drain_audit_outbox, publish_audit_request
from app.agents.squad.executor import ExecutorAgent
from app.agents.squad.extractor import ExtractorAgent
from app.agents.squad.runner import SquadRunner

__all__ = [
    "SquadContext",
    "AgentResult",
    "SquadAgent",
    "new_run_id",
    "ExtractorAgent",
    "EnricherAgent",
    "AuditorAgent",
    "ExecutorAgent",
    "SquadRunner",
    "publish_audit_request",
    "drain_audit_outbox",
]
