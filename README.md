# Classificação de Tickets usando LLM (gpt)

## Visão Geral
Serviço **FastAPI** com uma rota única — **POST /classificacao** — que:
- lê um CSV de tickets;
- para cada linha, gera resumo (≤ 3 frases) e classificação em uma única categoria usando OpenAI;
- usa, além do texto do chamado (`text_column`), os campos de contexto **canal** e **prioridade** (opcionais), que são injetados no prompt para melhorar a decisão;
- retorna JSON por item e, opcionalmente, salva um CSV com `summary` e `predicted_category`.

---

## Categorias utilizadas (exemplo típico)
O classificador opera sobre uma lista fechada definida pelo usuário. Um conjunto frequente em Service Desk é:

- **Acesso/Senha** — problemas de autenticação, bloqueio, expiração de senha.
- **Falha de Sistema** — indisponibilidade, erro de aplicação, degradação de serviço.
- **Solicitação de Serviço** — pedidos de criação/alteração de acesso, provisionamento, novas funcionalidades.
- **Informação/Dúvida** — pedidos de esclarecimento, orientações de uso.
- **Infraestrutura/Rede** — Wi-Fi, VPN, latência, cabeamento, hardware de rede.

> Observação: a lista pode ser alterada livremente no corpo da requisição; o modelo sempre escolherá uma única categoria dentre as fornecidas.


---

## Explicação de Cada Arquivo/Pasta

### app/
Módulo raiz da aplicação. Contém inicialização do FastAPI, definição e inclusão de rotas, schemas (Pydantic), serviços de integração (OpenAI) e utilitários.

#### app/main.py
- Instancia o FastAPI com título, versão e descrição.
- Carrega variáveis de ambiente com dotenv.
- Inclui o roteador principal (`app.api.routes.router`).
- Expõe **GET /health** para verificação de disponibilidade.  
**Responsabilidade**: ponto de entrada do ASGI (ex.: `uvicorn app.main:app`).

#### app/api/
Camada HTTP (controladores/rotas).

- **app/api/routes.py**  
  - Define o `APIRouter` e a rota principal **POST /classificacao**.
  - Valida a existência do arquivo CSV (`dataset_path`).
  - Carrega o CSV via `app.utils.io.load_dataframe`.
  - Valida colunas (`text_column`, `id_column` quando fornecida).
  - Seleciona as linhas (`max_rows`) e invoca o pipeline.
  - Mede tempo total e retorna `ClassificacaoResponse`.  
  **Responsabilidade**: orquestração HTTP (sem lógica de LLM/IO baixo nível).

#### app/core/
Recursos “core” que não dependem da camada HTTP.

- **app/core/prompt.py**  
  - Define `SYSTEM_TEMPLATE` e `USER_TEMPLATE` (placeholders `{text}`, `{locale}`, `{categories}`).  
  **Responsabilidade**: padronizar o prompt.

#### app/schemas/
Contratos de entrada/saída da API (Pydantic).

- **requests.py** → `ClassificacaoRequest` (campos: `dataset_path`, `text_column`, `id_column` opcional, `categories`, `max_rows`, `temperature`, `resume_locale`, `output_csv_path`, `csv_sep`, `csv_encoding`, `openai_model`).
- **responses.py** → `ItemResult` (id, summary, category) e `ClassificacaoResponse` (metadados e lista de resultados).

#### app/services/
Integrações e lógica de aplicação.

- **openai_client.py**  
  - `_post_with_retries(...)` → POST com retries e backoff.  
  - Classe `OpenAIClient` (usa `OPENAI_API_KEY`, `OPENAI_BASE_URL`).  
  - `complete(system, user)` → chama `/chat/completions`.

- **pipeline.py**  
  - `_safe_json_parse(s)` → tenta extrair JSON válido.  
  - `_inference_row(...)` → formata prompt, chama `OpenAIClient.complete`, normaliza categoria.  
  - `run_pipeline(...)` → executa em paralelo com `asyncio.Semaphore`. Salva CSV opcionalmente.

#### app/utils/
Funções utilitárias.

- **io.py**  
  - `load_dataframe(path, sep=None, encoding=None)` → leitura robusta de CSV com autodetecção.

---

## Arquivos na raiz

- **requirements.txt**  
  Lista de dependências: `fastapi`, `uvicorn[standard]`, `pydantic`, `pandas`, `python-dotenv`, `httpx`.

- **.env.example**  
  Modelo de variáveis:
  - `OPENAI_API_KEY` (obrigatória).
  - `OPENAI_BASE_URL` (opcional).
  - `MAX_CONCURRENCY` (opcional, padrão 4).

---

## Fluxo de Execução (Visão de Alto Nível)
1. Recepção HTTP (**POST /classificacao**) → validação básica (Pydantic).  
2. IO CSV (`utils.io.load_dataframe`).  
3. Validação de colunas.  
4. Seleção de linhas (`max_rows`).  
5. Pipeline:
   - Construção de prompts.
   - Chamada OpenAI com retries.
   - Concorrência controlada.
   - Normalização de categoria.
   - (Opcional) Escrita de CSV.  
6. Resposta → `ClassificacaoResponse`.

---

## Contrato da API

- **Endpoint**: `POST /classificacao`
- **Entrada**: `ClassificacaoRequest`
- **Saída**: `ClassificacaoResponse`

---

## Execução e Testes Locais

### Instalação
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt


