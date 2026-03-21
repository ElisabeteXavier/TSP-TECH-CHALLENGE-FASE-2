import streamlit as st
import matplotlib.pyplot as plt

from run_headless import run_ga_headless, load_dotenv_if_present
from llm_client import llm_to_config, llm_to_explanation, llm_generate_driver_instructions, llm_generate_efficiency_report, llm_suggest_improvements
from hospital_data import priorities, demands, VEHICLE_CAPACITY
from typing import Tuple
from genetic_algorithm import default_problems
import datetime
import json
import os

# Storage simples em arquivo
RESULTS_FILE = "results_history.json"

def load_historical_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_result(result):
    history = load_historical_results()
    result["timestamp"] = datetime.datetime.now().isoformat()
    history.append(result)
    # Manter apenas últimos 10 resultados
    if len(history) > 10:
        history = history[-10:]
    with open(RESULTS_FILE, "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------
# CONFIG INICIAL
# ---------------------------
st.set_page_config(page_title="Otimizador IA", layout="wide")
load_dotenv_if_present()

st.title("🚚 Otimizador Inteligente de Rotas")
st.caption("Algoritmo Genético + IA (2 veículos)")


# ---------------------------
# SIDEBAR
# ---------------------------
st.sidebar.title("🧠 Estratégia")

mode = st.sidebar.radio(
    "Modo",
    ["🤖 IA (texto)", "🎛️ Manual"]
)

st.sidebar.divider()


# ---------------------------
# INPUT
# ---------------------------
st.subheader("🎯 Defina sua estratégia")

if mode == "🤖 IA (texto)":
    objective = st.text_area(
        "Descreva o objetivo:",
        placeholder="Ex: priorizar urgência mais que distância"
    )
    # No modo IA, gerações não aparecem para o usuário.
    # O backend usa o que vier da LLM ou default.
    config = {}
else:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        dist = st.slider("Peso Distância", 0.0, 1.0, 0.3)
    with col2:
        prio = st.slider("Peso Prioridade", 0.0, 1.0, 0.5)
    with col3:
        cap = st.slider("Peso Capacidade", 0.0, 1.0, 0.2)
    with col4:
        generations = st.slider("Gerações", 20, 1000, 80, step=10)

    config = {
        "weights": {
            "distance": dist,
            "priority": prio,
            "capacity": cap
        },
        "n_generations": generations
    }
    objective = None


# ---------------------------
# BOTÃO
# ---------------------------
run = st.button("🚀 Gerar melhor rota")


def plot_two_routes(depot, route_v1, route_v2):
    fig, ax = plt.subplots(figsize=(8, 6))

    # Veículo 1 (azul)
    if route_v1:
        x1 = [depot[0]] + [p[0] for p in route_v1] + [depot[0]]
        y1 = [depot[1]] + [p[1] for p in route_v1] + [depot[1]]
        ax.plot(x1, y1, marker="o", color="blue", label="Veículo 1")

    # Veículo 2 (verde)
    if route_v2:
        x2 = [depot[0]] + [p[0] for p in route_v2] + [depot[0]]
        y2 = [depot[1]] + [p[1] for p in route_v2] + [depot[1]]
        ax.plot(x2, y2, marker="o", color="green", label="Veículo 2")

    # Depósito
    ax.scatter([depot[0]], [depot[1]], color="black", s=120, label="Depósito", zorder=5)

    ax.set_title("Rotas dos 2 veículos")
    ax.legend()
    ax.grid(alpha=0.2)
    return fig


# ---------------------------
# EXECUÇÃO
# ---------------------------
if run:
    with st.spinner("Rodando otimização... 🤖"):
        try:
            if objective:
                config = llm_to_config(objective)

            result = run_ga_headless(config or {})
          #  explanation = llm_to_explanation(result)

        except Exception as e:
            st.error(f"Erro: {e}")
            st.stop()

    st.success("✅ Otimização concluída!")

    metrics = result.get("metrics", {})
    split = result.get("split", {})
    best_routes = result.get("best_routes", {})
    depot = result.get("depot", (0, 0))
    route_v1 = best_routes.get("vehicle_1_coords", [])
    route_v2 = best_routes.get("vehicle_2_coords", [])

    # ---------------------------
    # MÉTRICAS
    # ---------------------------
    st.subheader("📊 Resultados")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.metric("Fitness final", f"{metrics.get('fitness_final', 0):.2f}")
    c2.metric("Distância total", f"{metrics.get('total_distance', 0):.2f}")
    c3.metric("Distância V1", f"{metrics.get('distance_v1', 0):.2f}")
    c4.metric("Distância V2", f"{metrics.get('distance_v2', 0):.2f}")
    c5.metric("Penalidade prioridade", f"{metrics.get('priority_penalty', 0):.2f}")
    c6.metric("Penalidade capacidade", f"{metrics.get('capacity_penalty', 0):.2f}")

    st.caption(
        f"Corte: eixo={split.get('axis', 'N/A')} | "
        f"threshold={split.get('threshold', 'N/A')} | "
        f"fallback={split.get('fallback', False)}"
    )

    # ---------------------------
    # EVOLUÇÃO
    # ---------------------------
    st.subheader("📈 Evolução")
    history = result.get("history", {}).get("best_fitness_by_generation", [])
    st.line_chart(history)

    # ---------------------------
    # ROTAS
    # ---------------------------
    st.subheader("🗺️ Rotas")
    try:
        st.pyplot(plot_two_routes(depot, route_v1, route_v2))
    except Exception as e:
        st.warning(f"Não foi possível desenhar as rotas: {e}")

    with st.expander("Ver rotas (IDs)"):
        st.write("Veículo 1 IDs:", best_routes.get("vehicle_1_ids", []))
        st.write("Veículo 2 IDs:", best_routes.get("vehicle_2_ids", []))

    # # ---------------------------
    # # EXPLICAÇÃO
    # # ---------------------------
    # st.subheader("🧠 Explicação da IA")
    # st.info(explanation)
    #     # Salvar resultado para histórico
    save_result(result)
    historical_results = load_historical_results()[:-1]  # Excluir o atual

    # # ---------------------------
    # DASHBOARD DE INTELIGÊNCIA
    # ---------------------------
    st.subheader("🧠 Inteligência Operacional")

    tab1, tab2, tab3 = st.tabs(["🚐 Instruções Motoristas", "📊 Relatório Eficiência", "💡 Sugestões"])

    with tab1:
        st.write("**Instruções Detalhadas para Motoristas**")
        try:
            driver_instructions = llm_generate_driver_instructions(
        routes=best_routes,
        priorities=priorities,
        demands=demands,  # ✅ NOVO
        vehicle_capacity=VEHICLE_CAPACITY,  # ✅ NOVO
        depot_coords=depot
        )
           
            st.info(driver_instructions)
        except Exception as e:
            st.warning(f"Erro ao gerar instruções: {e}")

    with tab2:
        st.write("**Relatório de Eficiência**")
        try:
            efficiency_report = llm_generate_efficiency_report(
                current_result=result,
                historical_results=historical_results
            )
            st.info(efficiency_report)
        except Exception as e:
            st.warning(f"Erro ao gerar relatório: {e}")

    with tab3:
        st.write("**Sugestões de Melhoria**")
        try:
            improvements = llm_suggest_improvements(
                results_pattern=historical_results + [result],
                current_config=result.get("config_used", {})
            )
            st.info(improvements)
        except Exception as e:
            st.warning(f"Erro ao gerar sugestões: {e}")