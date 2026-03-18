import json
import os
import re
from typing import Any, Dict, Optional


CONFIG_SCHEMA_EXAMPLE: Dict[str, Any] = {
    "population_size": 100,
    "n_generations": 80,
    "mutation_prob": 0.3,
    "top_for_selection": 10,
    "vehicle_capacity": 15,
    "weights": {"distance": 0.3, "priority": 0.5, "capacity": 0.2},
}


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extrai o primeiro objeto JSON de uma resposta que pode conter texto extra.
    (Defensivo contra o modelo "falando demais".)
    """
    if not isinstance(text, str):
        raise ValueError("Resposta do LLM não é texto.")

    # Heurística: pega o primeiro bloco {...} com match guloso mínimo
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("Não foi possível extrair um JSON da resposta do LLM.")
    return json.loads(m.group(0))


def _openai_chat_completion(prompt: str, model: str) -> str:
    """
    Implementação sem dependência externa (usa urllib) para OpenAI Chat Completions.
    Requer OPENAI_API_KEY.
    """
    import urllib.request

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Defina OPENAI_API_KEY no ambiente para usar OpenAI.")

    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Você é um assistente que responde exatamente no formato solicitado."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
    parsed = json.loads(body)
    return parsed["choices"][0]["message"]["content"]


def call_llm(prompt: str, provider: Optional[str] = None) -> str:
    """
    Chamador único do LLM. Por padrão, tenta OpenAI via HTTP.
    provider:
      - "openai": usa OPENAI_API_KEY e o endpoint /v1/chat/completions
    """
    provider = (provider or os.getenv("LLM_PROVIDER") or "openai").lower().strip()

    if provider == "openai":
        model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        return _openai_chat_completion(prompt, model=model)

    raise RuntimeError(f"Provider LLM não suportado: {provider}. Use LLM_PROVIDER=openai.")


def llm_to_config(user_text: str, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Converte intenção (texto) -> parâmetros do AG.
    Retorna SOMENTE dict (config) no schema esperado.
    """
    prompt = f"""
Você é um gerador de configurações para um Algoritmo Genético (AG) de roteirização.
Sua tarefa: dado o objetivo do usuário, retorne APENAS um JSON válido seguindo exatamente este schema:

{json.dumps(CONFIG_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)}

Regras:
- Responda SOMENTE com JSON (sem markdown, sem explicação).
- Sempre inclua todos os campos do schema.
- weights.* devem somar aproximadamente 1.0 (pode ter pequenas diferenças por arredondamento).
- mutation_prob deve estar entre 0 e 1.
- top_for_selection deve ser >= 2.

Objetivo do usuário:
{user_text}
""".strip()

    raw = call_llm(prompt, provider=provider)
    return _extract_json_object(raw)


def llm_to_explanation(result_dict: Dict[str, Any], provider: Optional[str] = None) -> str:
    """
    Converte resultado estruturado (JSON) -> explicação humana.
    """
    prompt = f"""
Explique o resultado abaixo em português simples, como se estivesse explicando para uma criança.
Seja curto (6 a 10 linhas), sem termos técnicos pesados.

Resultado (JSON):
{json.dumps(result_dict, ensure_ascii=False, indent=2)}
""".strip()

    return call_llm(prompt, provider=provider).strip()

