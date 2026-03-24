import json
import os
import re
from typing import Any, Dict, Optional, Tuple, List
from schemas import CONFIG_SCHEMA_EXAMPLE
from genetic_algorithm import default_problems
import openai


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
Você é um tradutor de intenção -> configuração de Algoritmo Genético (AG) para roteirização.
Retorne APENAS um JSON válido no schema abaixo (campos podem ser parciais; defaults serão aplicados no código):

{json.dumps(CONFIG_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)}

Regras de saída (obrigatórias):
- Responda SOMENTE com JSON (sem markdown, sem explicação).
- Não invente campos fora do schema.
- mutation_prob deve estar entre 0 e 1.
- top_for_selection >= 2.
- weights.* devem ser números >= 0.
- Se fornecer weights, prefira que somem ~ 1.0.
- NÃO zere explicitamente pesos (0.0) a menos que o usuário peça para ignorar aquele critério.

Guia de mapeamento (use como heurística):
- “mais rápida / menor distância” -> aumentar weights.distance, reduzir weights.priority (mas não zerar).
- “priorizar urgência / crítico primeiro” -> aumentar weights.priority.
- “carro aguenta pouco / capacidade baixa” -> reduzir vehicle_capacity e aumentar weights.capacity.
- “mais exploração” -> aumentar mutation_prob e n_generations; diminuir top_for_selection (mantendo >=2).
- “mais estabilidade / menos aleatório” -> diminuir mutation_prob; aumentar top_for_selection.

Exemplos:
Usuário: "Quero priorizar urgência mais que distância"
Saída (exemplo): {{"weights": {{"distance": 0.2, "priority": 0.7, "capacity": 0.1}}, "mutation_prob": 0.2, "n_generations": 80}}

Usuário: "Meu carro aguenta pouco, mas ainda quero uma rota curta"
Saída (exemplo): {{"vehicle_capacity": 10, "weights": {{"distance": 0.4, "priority": 0.2, "capacity": 0.4}}}}

Usuário: "Quero mais exploração, tenta achar soluções diferentes"
Saída (exemplo): {{"mutation_prob": 0.45, "n_generations": 120, "top_for_selection": 6, "weights": {{"distance": 0.3, "priority": 0.5, "capacity": 0.2}}}}

Objetivo do usuário:
{user_text}
""".strip()

    raw = call_llm(prompt, provider=provider)
    cfg = _extract_json_object(raw)
    validate_config_shape(cfg)

    # Pós-processamento leve: evita pesos zerados explicitamente.
    # (O normalize_config ainda faz clamp/normalização no headless.)
    if isinstance(cfg.get("weights"), dict):
        for k in ("distance", "priority", "capacity"):
            if k in cfg["weights"] and cfg["weights"][k] == 0:
                cfg["weights"][k] = 0.01
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


def llm_suggest_tuned_config(
    *,
    current_config: Dict[str, Any],
    last_result: Dict[str, Any],
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Etapa 5 (extra): sugere ajustes de hyperparâmetros do AG baseado no resultado anterior.
    Retorna JSON (parcial) no schema de config.
    """
    prompt = f"""
Você é um assistente de auto-tuning para um Algoritmo Genético (AG) de roteirização.
Você receberá a config atual e o resultado da execução (inclui histórico do melhor fitness por geração).
Sua tarefa é sugerir UMA nova configuração (JSON) para a próxima execução.

Schema permitido (JSON, campos opcionais):
{json.dumps(CONFIG_SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)}

Regras IMPORTANTES:
- Responda SOMENTE com JSON (sem markdown, sem explicação).
- Retorne somente campos que deseja alterar (pode ser parcial).
- mutation_prob deve estar entre 0 e 1.
- top_for_selection >= 2.
- weights.* >= 0. Se fornecer weights, prefira que somem ~ 1.0 (o código normaliza).
- Seja conservador: ajuste poucos parâmetros por vez (2-4 mudanças no máximo).
- Se o fitness estagnou cedo (pouca melhora por muitas gerações), aumente exploração (mutation_prob e/ou n_generations).
- Se o fitness oscila muito (piorando e melhorando), aumente estabilidade (top_for_selection e/ou reduza mutation_prob).

Config atual:
{json.dumps(current_config, ensure_ascii=False, indent=2)}

Resultado anterior:
{json.dumps(last_result, ensure_ascii=False, indent=2)}
""".strip()

    raw = call_llm(prompt, provider=provider)
    cfg = _extract_json_object(raw)
    validate_config_shape(cfg)
    return cfg



def llm_generate_driver_instructions(
    *,
    routes: Dict[str, Any],
    priorities: Dict[int, int],
    demands: Dict[int, int],
    vehicle_capacity: float,
    depot_coords: Tuple[float, float],
    provider: Optional[str] = None,
) -> str:
    """
    Gera instruções detalhadas para motoristas baseadas nas rotas otimizadas.
    """
    # Calcular carga de cada veículo
    vehicle_loads = {}
    for vehicle_name, route in routes.items():
        total_load = 0
        for coord in route:
            # Encontrar ID correspondente à coordenada
            city_id = None
            for cid, city_coord in enumerate(default_problems[15]):
                if city_coord == coord and cid in demands:
                    city_id = cid
                    break
            if city_id is not None:
                total_load += demands[city_id]
        vehicle_loads[vehicle_name] = total_load
    
    prompt = f"""
Você é um coordenador de logística médica. Crie instruções detalhadas para os motoristas
baseado nas rotas otimizadas abaixo.

ROTAS OTIMIZADAS:
{json.dumps(routes, ensure_ascii=False, indent=2)}

PRIORIDADES (0=crítico, 1=regular, 2=insumo):
{json.dumps(priorities, ensure_ascii=False, indent=2)}

DEMANDAS (unidades por ponto):
{json.dumps(demands, ensure_ascii=False, indent=2)}

CAPACIDADE DOS VEÍCULOS: {vehicle_capacity} unidades

CARGA POR VEÍCULO:
{json.dumps(vehicle_loads, ensure_ascii=False, indent=2)}

Coordenadas do Depósito: {depot_coords}

REGRAS:
- Seja claro e profissional
- Inclua ordem de entrega e pontos críticos
- Mencione capacidade do veículo e carga total
- Destaque entregas urgentes (prioridade 0)
- Adicione dicas de segurança e eficiência
- Verifique se a carga não excede a capacidade
- Formate como um briefing operacional separado por veículo
""".strip()
    
    return call_llm(prompt, provider=provider).strip()


def llm_generate_efficiency_report(
    *,
    current_result: Dict[str, Any],
    historical_results: List[Dict[str, Any]] = None,
    provider: Optional[str] = None,
) -> str:
    """
    Cria relatório de eficiência diário/semanal com base nos resultados.
    """
    prompt = f"""
Você é um analista de logística. Crie um relatório de eficiência baseado nos dados abaixo.

Resultado Atual:
{json.dumps(current_result, ensure_ascii=False, indent=2)}

Resultados Históricos:
{json.dumps(historical_results or [], ensure_ascii=False, indent=2)}

Regras:
- Analise tendências de desempenho
- Compare com resultados anteriores
- Destaque economias de tempo/distância
- Sugira KPIs importantes
- Use linguagem executiva-friendly
- Inclua recomendações acionáveis
""".strip()
    
    return call_llm(prompt, provider=provider).strip()


def llm_suggest_improvements(
    *,
    results_pattern: List[Dict[str, Any]],
    current_config: Dict[str, Any],
    provider: Optional[str] = None,
) -> str:
    """
    Sugere melhorias no processo com base em padrões identificados.
    """
    prompt = f"""
Você é um consultor de otimização logística. Analise os padrões abaixo e sugira melhorias.

Padrões de Resultados:
{json.dumps(results_pattern, ensure_ascii=False, indent=2)}

Configuração Atual:
{json.dumps(current_config, ensure_ascii=False, indent=2)}

Regras:
- Identifique padrões de performance
- Sugira ajustes nos pesos do algoritmo
- Recomende mudanças operacionais
- Proponha experimentos A/B
- Foque em melhorias práticas e implementáveis
""".strip()
    
    return call_llm(prompt, provider=provider).strip()

def ask_llm_about_routes(route_v1, route_v2, question):
    client = openai.OpenAI()

    context = f"""
Você está analisando rotas de entrega hospitalar.

Motorista 1:
{route_v1}

Motorista 2:
{route_v2}

Responda perguntas com base nessas rotas.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Especialista em logística hospitalar."},
            {"role": "user", "content": context + f"\nPergunta: {question}"}
        ]
    )

    return response.choices[0].message.content