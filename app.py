import streamlit as st
import matplotlib.pyplot as plt

from run_headless import run_ga_headless, load_dotenv_if_present
from llm_client import llm_to_config, llm_to_explanation, llm_generate_driver_instructions, llm_generate_efficiency_report, llm_suggest_improvements,ask_llm_about_routes
from hospital_data import priorities, demands, VEHICLE_CAPACITY
from typing import Tuple
from genetic_algorithm import default_problems
import datetime
import json
import os

# Storage simples em arquivo
RESULTS_FILE = "results_history.json"
cities_locations = default_problems[15]
city_to_id_map = {location: i for i, location in enumerate(cities_locations)}


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
n_vehicles_default = 2 
st.set_page_config(page_title="Otimizador IA", layout="wide")
load_dotenv_if_present()

st.title("🚚 Otimizador Inteligente de Rotas")
st.caption(f"Algoritmo Genético + IA ({n_vehicles_default} veículos)")
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

# Slider global de número de veículos (aparece em ambos os modos)
n_vehicles = st.slider("Número de Veículos", 1, 5, 2)

if mode == "🤖 IA (texto)":
    objective = st.text_area(
        "Descreva o objetivo:",
        placeholder="Ex: priorizar urgência mais que distância"
    )
    config = {
        "n_vehicles": n_vehicles
    }
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
        "n_generations": generations,
        "n_vehicles": n_vehicles
    }

# ---------------------------
# BOTÃO
# ---------------------------
run = st.button("🚀 Gerar melhor rota")

priority_colors = {
    0: "red",     # 🔴 crítico
    1: "yellow",  # 🟡 médio
    2: "green"    # 🟢 baixo
}
def plot_routes(depot, routes_dict):
    """Plota rotas para N veículos de forma dinâmica"""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Cores para diferentes veículos
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    
    # Plota cada rota de veículo
    for i, (vehicle_id, route_coords) in enumerate(routes_dict.items()):
        if route_coords:
            color = colors[i % len(colors)]
            x = [depot[0]] + [p[0] for p in route_coords] + [depot[0]]
            y = [depot[1]] + [p[1] for p in route_coords] + [depot[1]]
            ax.plot(x, y, color=color, linewidth=2, label=f"Veículo {i+1}")
    
    # Plota pontos (cidades + depósito)
    for city in cities_locations:
        if city == depot:
            ax.scatter(*city, c="black", s=120, label="Depósito", zorder=5)
            continue
        
        city_id = city_to_id_map[city]
        priority = priorities.get(city_id, 3)
        
        ax.scatter(
            *city,
            c=priority_colors[priority],
            s=70,
            edgecolors="black",
            linewidth=0.5, 
            zorder=3,
        )
    
    ax.set_title(f"Rotas dos {len(routes_dict)} veículos")
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
    # Extrai rotas do resultado (apenas coordenadas para plotagem)
    best_routes = {}
    for key, value in result.get("best_routes", {}).items():
        if key.endswith("_coords"):
            best_routes[key] = value
    depot = result.get("depot", (0, 0))
    # Salvar rotas no session_state para o chat
    st.session_state.best_routes = best_routes
    # ---------------------------
    # MÉTRICAS
    # ---------------------------
    st.subheader("📊 Resultados")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.metric("Fitness final", f"{metrics.get('fitness_final', 0):.2f}")
    c2.metric("Distância total", f"{metrics.get('total_distance', 0):.2f}")
    n_display_vehicles = len([k for k in metrics.keys() if k.startswith('distance_v')])
    if n_display_vehicles > 0:
        c3.metric(f"Distância V1", f"{metrics.get('distance_v1', 0):.2f}")
    if n_display_vehicles > 1:
        c4.metric(f"Distância V2", f"{metrics.get('distance_v2', 0):.2f}")

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
 # Gera legenda dinâmica baseada no número de veículos
    vehicle_legends = []
    n_display_vehicles = len([k for k in best_routes.keys() if k.endswith('_coords')])
    colors = ['🔵', '🟢', '🔴', '🟠', '🟣']

    for i in range(n_display_vehicles):
        vehicle_legends.append(f"{colors[i % len(colors)]} **Veículo {i+1}**")

    vehicle_text = "      ".join(vehicle_legends)

    st.markdown(f""" 
    Hospitais(pelo nível de prioridade):
    \n🔴 **Crítico**   🟡 **Médio**      🟢 **Baixo**    
    \n⚫ **Depósito**
    \nVeículos :  
    \n{vehicle_text}
    """)
    try:
        # st.pyplot(plot_two_routes(depot, route_v1, route_v2))
        st.pyplot(plot_routes(depot, best_routes))
    except Exception as e:
        st.warning(f"Não foi possível desenhar as rotas: {e}")

    with st.expander("Ver rotas (IDs)"):
        for vehicle_id, route_ids in best_routes.items():
            if vehicle_id.endswith('_ids'):
                vehicle_name = vehicle_id.replace('_ids', '')
                st.write(f"{vehicle_name} IDs:", route_ids)
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

# Adicionar função serialize_route se não existir:
def serialize_route(route_coords):
    """Converte coordenadas da rota para string legível"""
    return [f"({x:.2f}, {y:.2f})" for x, y in route_coords]

# Corrigir a condição do chat:
if "best_routes" in st.session_state and st.session_state.best_routes:
    # ... código do chat

# ---------------------------
# CHAT COM IA
# ---------------------------
    st.subheader("💬 Chat com a IA sobre a rota")

# Substituir no chat:
# Substituir no chat:
if "best_routes" in st.session_state and st.session_state.best_routes:
    # Extrair TODAS as rotas dinamicamente
    all_routes = st.session_state.best_routes
    
    # Para o chat, passar todas as rotas como uma lista
    all_route_coords = []
    for vehicle_id, route_coords in all_routes.items():
        if vehicle_id.endswith("_coords"):
            all_route_coords.extend(route_coords)
    
    # Usar a rota combinada para o chat
    route_v1 = all_route_coords
    route_v2 = []  # Vazio, já que usamos todas em route_v1
    # Inicializa histórico
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.chat_input("Pergunte algo sobre as rotas...")

    if user_input:
        st.session_state.chat_history.append(("user", user_input))

        try:
            rota1_str = serialize_route(route_v1)
            rota2_str = serialize_route(route_v2)

            resposta = ask_llm_about_routes(
                route_v1=rota1_str,
                route_v2=rota2_str,
                question=user_input
            )

        except Exception as e:
            resposta = f"Erro: {e}"

        st.session_state.chat_history.append(("assistant", resposta))

    # Renderiza chat
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.write(msg)

else:
    st.info("Gere uma rota primeiro para usar o chat.")