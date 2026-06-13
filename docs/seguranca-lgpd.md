# Segurança e LGPD

> Proposta de estrutura completa (do zero, conforme decisão do founder). Princípios: **isolamento absoluto, minimização, base legal documentada, segredos fora do repo, anonimização rígida do benchmark**. Posicionamento: tratamos dado **do cliente, sob contrato e autorização**.

## 1. Papéis LGPD

| Papel | Quem | Base |
|-------|------|------|
| **Controlador** | a construtora/incorporadora (cliente) — define finalidade do tratamento do próprio dado | titular do dado de negócio |
| **Operador** | **nós** — tratamos o dado em nome e por instrução do cliente | contrato de operador |
| **Encarregado (DPO)** | designado de nossa parte (contato no site/contrato) | art. 41 LGPD |

A maior parte do dado é **dado de pessoa jurídica / transacional** (pedidos, notas, preços), não dado pessoal sensível. Onde houver dado pessoal (ex.: nome de comprador/aprovador, sócios no QSA da dimensão 4), aplica-se minimização e finalidade específica.

## 2. Base legal (proposta)

- **Execução de contrato** (art. 7º, V) entre operador e controlador para o tratamento do dado de negócio do cliente.
- **Legítimo interesse** (art. 7º, IX) para a dimensão de integridade (consulta a bases públicas CEIS/CNEP/Receita) — com teste de proporcionalidade documentado, dado que a finalidade (prevenir fraude/risco) é legítima e usa fontes públicas.
- **Dados públicos** (CEIS/CNEP/PNCP/SINAPI/Receita): tratamento de dado tornado público pelo poder público, observada a finalidade.
- Tudo registrado em **Registro de Operações de Tratamento (ROPA)** por finalidade.

## 3. Contrato e autorização

- **DPA (Data Processing Agreement)** anexo ao contrato: finalidade, escopo do dado, instruções do controlador, subprocessadores (ex.: provedor de embeddings, infra), prazo, retorno/eliminação ao fim.
- **Autorização de acesso ao ERP:** o cliente provisiona usuário de API **somente leitura** e nos autoriza a ler. Documentado.
- **Subprocessadores divulgados:** provedor de embeddings (API externa), provedor de LLM (Anthropic), infra de hospedagem. Cliente informado; opção de objeção em enterprise.

## 4. Isolamento multi-tenant

- **RLS no Postgres** (MVP): toda tabela de dado de cliente com `tenant_id` + policy; app sem `BYPASSRLS`; `tenant_id` setado por request/job. (Ver [modelo-dados.md](./modelo-dados.md) §3.)
- **Teste de isolamento** como critério de aceite (suíte que prova que tenant A não lê B).
- **Caminho enterprise:** schema-per-tenant para clientes que exijam isolamento físico.
- **Segredos por tenant** namespaced; credencial do tenant A inacessível ao contexto do tenant B.
- **Logs e métricas** carregam `tenant_id` mas não vazam dado entre tenants; sem PII sensível em log.

## 5. Anonimização do benchmark (proteção do fosso)

O benchmark cross-cliente é o ativo mais sensível em privacidade. Regras:

1. **Schema fisicamente separado** (`benchmark`), **sem `tenant_id`** e sem qualquer chave que reidentifique o cliente.
2. **k-anonimato:** uma célula de agregação `(insumo, região, período, faixa de qty)` só entra no pool quando atinge o mínimo (`[ASSUNÇÃO]` **≥3 tenants e ≥5 fornecedores distintos**). Células abaixo do k são suprimidas.
3. **Pipeline de anonimização separado:** um ETL dedicado lê o dado identificável (com permissão), agrega, aplica k-anonimato e **só emite o agregado** para o schema de benchmark. O caminho identificável → benchmark não existe diretamente.
4. **Fornecedor anonimizado:** identidade do fornecedor entra como **bucket/hash**, não como CNPJ, no pool.
5. **Sem engenharia reversa:** revisão para garantir que combinações raras não permitam reidentificar (supressão de outliers/células pequenas).
6. **Opt-out contratual:** cliente pode optar por não contribuir ao pool (com impacto no preço/feature), respeitando a escolha.

Resultado: o preço identificável de um cliente **nunca** alcança outro cliente; só a referência agregada e anônima.

## 6. Gestão de segredos

- **Nada de credencial no repositório.** `.gitignore` cobre `.env*`, chaves, certificados. Pre-commit hook de *secret scanning*.
- **Local (dev nesta máquina):** `.env` fora do versionamento.
- **Servidor:** secret manager. Como o deploy é em servidor próprio/cloud-agnóstico, proposta: **secret manager auto-hospedável** (ex.: HashiCorp Vault ou Infisical), ou os secrets do orquestrador (Docker secrets) no início — abstraído atrás de um `SecretProvider` para trocar sem mudar código.
- **`ANTHROPIC_API_KEY`:** verificado como **ausente** do ambiente desta sessão e dos perfis de shell (`.zshrc`, `.zprofile`, `.bashrc`, `.bash_profile`, `.profile`) no início — evitando cobrança de API não intencional. A chave de produção será injetada só via secret provider, nunca exportada solta.
- **Certificados NF-e (Fase 1):** cofre dedicado para A1/A3, criptografado, acesso auditado, namespaced por tenant.
- **Rotação:** credenciais e chaves rotacionáveis; rotação não exige deploy.

## 7. Criptografia

- **Em trânsito:** TLS em tudo (reverse proxy com TLS no servidor; APIs externas via HTTPS).
- **Em repouso:** disco/volume criptografado; campos especialmente sensíveis (certificados, credenciais) com envelope encryption por tenant.
- **Backups:** criptografados, testados (restore drill), retenção definida.

## 8. Controle de acesso

- **Usuários por tenant** com papéis (admin, controladoria, suprimentos, leitura).
- **SSO** (SAML/OIDC) na trilha enterprise.
- **Princípio do menor privilégio** interno (nossa equipe): acesso a dado de cliente logado e justificado; produção sem acesso amplo por padrão.
- **MFA** para acesso administrativo.

## 9. Trilha de auditoria do próprio sistema

- `audit_log` **append-only**: quem (user/system/agent) fez o quê, sobre qual entidade, quando. Inclui: leituras de sync, geração de achado, revisão humana, execução de agente, acesso administrativo.
- Imutável e exportável — o cliente enterprise pode auditar o nosso acesso ao dado dele.

## 10. Minimização e retenção

- **Minimização:** só ingerimos as entidades necessárias às regras; não puxamos dado pessoal além do necessário; prompts de LLM recebem o mínimo.
- **Retenção:** configurável por tenant; default proposto: dado transacional pelo período contratual + janela legal; ao fim do contrato, **retorno ou eliminação** conforme DPA.
- **Direitos do titular:** quando houver dado pessoal, suporte a acesso/correção/eliminação via controlador (cliente), já que somos operador.

## 11. Resposta a incidente

- Plano de resposta a incidente (detecção, contenção, notificação ao controlador, à ANPD e titulares quando aplicável, dentro do prazo legal).
- Logs e trilha suportam a investigação.

## 12. LATAM-readiness de privacidade (sem construir agora)

- O design (papéis, base legal documentada, ROPA, DPA, anonimização) é compatível com leis locais futuras (ex.: LFPDPPP no México). Trocar a base legal/feed por país é configuração, não rewrite. (Ver [latam-readiness.md](./latam-readiness.md).)

## 13. Checklist de segurança para o MVP

- [ ] RLS ativo + suíte de teste de isolamento passando.
- [ ] `.env`/segredos fora do repo; secret scanning no pre-commit.
- [ ] `ANTHROPIC_API_KEY` nunca no repo; injetada via secret provider.
- [ ] TLS no servidor; criptografia em repouso.
- [ ] `audit_log` append-only funcionando.
- [ ] DPA + ROPA redigidos antes do primeiro cliente pagante.
- [ ] Pipeline de anonimização do benchmark com k-anonimato (quando ligar a Camada 2).
