# src/config/ — Configurações do sistema

Esta pasta é responsável por **carregar e disponibilizar as configurações** do sistema — como qual modelo de LLM usar, qual endereço do Ollama, quanto tempo esperar por uma resposta, etc.

---

## Arquivos

### `loader.py` — Leitor de configurações
Define a classe `Settings` (usando `pydantic-settings`) que lê automaticamente as variáveis do arquivo `.env` na raiz do projeto.

Configurações disponíveis:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OLLAMA_MODEL` | `qwen3:0.6b` | Nome do modelo a usar no Ollama. Padrão compacto (~500 MB), roda inteiramente em GPU com ~1 GB de VRAM. Para melhor qualidade use `qwen3:4b` se a GPU tiver 4 GB+ de VRAM. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do servidor Ollama |
| `LOG_LEVEL` | `INFO` | Nível de detalhamento dos logs |
| `SESSIONS_DIR` | `sessions` | Pasta para salvar histórico da interface |
| `RESULTS_DIR` | `results` | Pasta para salvar relatórios de avaliação |
| `DATA_DIR` | `data` | Pasta com os YAMLs de ativos e regras |
| `MAX_RETRIES_LLM` | `3` | Quantas vezes tentar novamente em caso de falha de conexão |
| `LLM_TIMEOUT_SECONDS` | `60` | Base do timeout por caso na avaliação (o runner aguarda 2× este valor); não é repassado ao cliente do Ollama |
| `OLLAMA_NUM_PREDICT` | `1024` | Limite de tokens gerados por chamada ao LLM; impede que o modelo repita chaves indefinidamente com `format="json"` |

A função `get_settings()` retorna o objeto de configurações. Ela usa `lru_cache` — ou seja, o arquivo `.env` é lido **uma única vez** durante toda a execução do programa, não a cada chamada.

---

## Como funciona na prática?

1. Você copia `.env.example` para `.env` (instruções no README raiz)
2. Edita `.env` se quiser mudar algum valor (ex: trocar o modelo)
3. O código usa `get_settings().ollama_model` em vez de ter o nome do modelo "colado" no código

Isso garante que **nenhuma configuração sensível** fica no código-fonte.

### `__init__.py`
Marca a pasta como submódulo Python.
