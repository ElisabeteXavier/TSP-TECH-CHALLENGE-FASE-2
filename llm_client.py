import json
import os
import re
from typing import Any, Dict, Optional

from schemas import CONFIG_SCHEMA_EXAMPLE


def validate_config_shape(cfg: Dict[str, Any]) -> None:
    """
    Valida apenas o "shape" (campos e tipos básicos) da configuração retornada pelo LLM.
    A normalização (defaults/limites) fica com o run_headless.normalize_config.
    """
    if not isinstance(cfg, dict):
        raise ValueError("Config do LLM precisa ser um objeto JSON (dict).")

    # Etapa 3: o LLM pode devolver JSON parcial; o headless aplica defaults.
    # Aqui validamos apenas que, se 'weights' vier, tem shape de dict.
    if "weights" in cfg and not isinstance(cfg.get("weights"), dict):
        raise ValueError("Campo 'weights' deve ser um objeto quando presente.")


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


def _openai_compatible_chat_completion(*, prompt: str, model: str, api_key: str, base_url: str) -> str:
    """
    Implementação sem dependência externa (usa urllib) para endpoints compatíveis com OpenAI.
    Ex.: OpenAI e Groq (OpenAI-compatible).
    """
    import ssl
    import urllib.request

    if not api_key:
        raise RuntimeError("API key ausente para o provider configurado.")

    url = base_url.rstrip("/") + "/chat/completions"
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
            "Accept": "application/json",
            # Alguns provedores/WAFs bloqueiam requests sem User-Agent.
            "User-Agent": "fiap-tech-challenge/llm-client (python urllib)",
        },
        method="POST",
    )

    # macOS às vezes não tem o bundle de CA disponível para o Python instalado.
    # Se certifi estiver presente, usamos o CA bundle dele para evitar CERTIFICATE_VERIFY_FAILED.
    context = None
    try:
        import certifi  # type: ignore

        context = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        context = ssl.create_default_context()

    import urllib.error

    try:
        with urllib.request.urlopen(req, timeout=60, context=context) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = "<sem corpo de erro>"
        raise RuntimeError(f"HTTP {e.code} ao chamar LLM: {err_body}") from None

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
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Defina OPENAI_API_KEY no ambiente para usar OpenAI.")
        return _openai_compatible_chat_completion(
            prompt=prompt,
            model=model,
            api_key=api_key,
            base_url="https://api.openai.com/v1",
        )

    if provider == "groq":
        model = os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Defina GROQ_API_KEY no ambiente para usar Groq.")
        return _openai_compatible_chat_completion(
            prompt=prompt,
            model=model,
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    raise RuntimeError(f"Provider LLM não suportado: {provider}. Use LLM_PROVIDER=groq|openai.")


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
    cfg = _extract_json_object(raw)
    validate_config_shape(cfg)
    return cfg


def llm_to_explanation(result_dict: Dict[str, Any], provider: Optional[str] = None) -> str:
    """
    Converte resultado estruturado (JSON) -> explicação humana.
    """
    prompt = f"""
Explique o resultado abaixo em português simples, como se estivesse explicando para uma criança.
Seja curto (6 a 10 linhas), sem termos técnicos pesados.

Regras IMPORTANTES:
- Não diga "quilômetros", "km" ou qualquer unidade do mundo real.
- A distância aqui é em "unidades do mapa" (pense em pixels/coordenadas), então use o termo "unidades".
- Não invente fatos que não estejam no JSON.

Resultado (JSON):
{json.dumps(result_dict, ensure_ascii=False, indent=2)}
""".strip()

    return call_llm(prompt, provider=provider).strip()

