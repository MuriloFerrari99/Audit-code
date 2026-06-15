"""Rotas de ingestão por upload (NF-e). Ver docs/modulo-upload.md."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import CurrentUser, get_current_user
from app.connectors.upload.load import load_nfe_files, load_spreadsheet

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/nfe")
async def upload_nfe(
    files: list[UploadFile],
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Sobe um ou mais XMLs de NF-e -> canônico (Invoice + itens + retenções).
    Depois, POST /rules/run audita. XML inválido vira dead_letter (visível)."""
    payload = [(f.filename or "nfe.xml", await f.read()) for f in files]
    return load_nfe_files(user.tenant_id, payload)


@router.post("/planilha")
async def upload_planilha(
    file: UploadFile,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Sobe uma planilha de lançamentos (CSV/XLSX) -> canônico (Bill).
    Colunas são auto-detectadas (o mapeamento volta no resumo p/ conferência).
    Linha sem valor vira dead_letter. Depois, POST /rules/run audita."""
    content = await file.read()
    return load_spreadsheet(user.tenant_id, file.filename or "planilha.csv", content)
