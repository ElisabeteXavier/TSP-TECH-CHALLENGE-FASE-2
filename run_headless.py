"""
Script para rodar o algoritmo genético SEM interface gráfica.
Útil para entender o fluxo e validar o funcionamento.
Roda N gerações e exibe o progresso no terminal.
"""
import argparse
import json
import os
import random
from typing import Any, Dict, Optional

import numpy as np
from genetic_algorithm import (
    mutate, order_crossover, generate_random_population,
    calculate_fitness, sort_population, default_problems, build_distance_matrix,
    calculate_total_distance, calculate_priority_penalty, calculate_capacity_penalty
)
from hospital_data import priorities, demands, VEHICLE_CAPACITY
from llm_client import llm_to_config, llm_to_explanation


DEFAULT_CONFIG: Dict[str, Any] = {
    "population_size": 100,
    "n_generations": 50,
    "mutation_prob": 0.5,
    "top_for_selection": 10,
    "vehicle_capacity": VEHICLE_CAPACITY,
    "weights": {"distance": 0.3, "priority": 0.5, "capacity": 0.2},
}


def _as_float(x: Any, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _as_int(x: Any, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def normalize_config(user_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(user_config, dict):
        cfg.update({k: v for k, v in user_config.items() if v is not None})

    cfg["population_size"] = max(2, _as_int(cfg.get("population_size"), DEFAULT_CONFIG["population_size"]))
    cfg["n_generations"] = max(1, _as_int(cfg.get("n_generations"), DEFAULT_CONFIG["n_generations"]))
    cfg["mutation_prob"] = min(1.0, max(0.0, _as_float(cfg.get("mutation_prob"), DEFAULT_CONFIG["mutation_prob"])))
    cfg["top_for_selection"] = max(2, _as_int(cfg.get("top_for_selection"), DEFAULT_CONFIG["top_for_selection"]))
    cfg["vehicle_capacity"] = _as_float(cfg.get("vehicle_capacity"), DEFAULT_CONFIG["vehicle_capacity"])

    weights = cfg.get("weights") if isinstance(cfg.get("weights"), dict) else {}
    cfg["weights"] = {
        "distance": _as_float(weights.get("distance"), DEFAULT_CONFIG["weights"]["distance"]),
        "priority": _as_float(weights.get("priority"), DEFAULT_CONFIG["weights"]["priority"]),
        "capacity": _as_float(weights.get("capacity"), DEFAULT_CONFIG["weights"]["capacity"]),
    }

    # Ajuste defensivo: top_for_selection não pode exceder população
    cfg["top_for_selection"] = min(cfg["top_for_selection"], cfg["population_size"])

    return cfg


def run_ga_headless(config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = normalize_config(config)

    # Dados do problema
    cities_locations = default_problems[15]
    hospital_coords = cities_locations[0]
    city_to_id_map = {location: i for i, location in enumerate(cities_locations)}
    distance_matrix = build_distance_matrix(cities_locations)

    population_size = cfg["population_size"]
    n_generations = cfg["n_generations"]
    mutation_prob = cfg["mutation_prob"]
    top_for_selection = cfg["top_for_selection"]
    vehicle_capacity = cfg["vehicle_capacity"]
    weights = cfg["weights"]

    print("=" * 60)
    print("TSP - Otimização de Rotas Médicas (Modo Console)")
    print("=" * 60)
    print(f"Pontos de entrega: {len(cities_locations)} (incl. hospital)")
    print(f"População: {population_size} | Mutação: {mutation_prob} | Top seleção: {top_for_selection}")
    print(f"Gerações: {n_generations} | Capacidade veículo: {vehicle_capacity}")
    print(f"Pesos fitness: {weights}")
    print("=" * 60)

    population = generate_random_population(cities_locations, population_size)
    best_fitness_history = []

    best_solution = None
    best_fitness = None

    for generation in range(1, n_generations + 1):
        population_fitness = [
            calculate_fitness(
                ind,
                priorities,
                city_to_id_map,
                hospital_coords,
                distance_matrix,
                demands=demands,
                vehicle_capacity=vehicle_capacity,
                weights=weights,
            )
            for ind in population
        ]

        population, population_fitness = sort_population(population, population_fitness)
        best_solution = population[0]
        best_fitness = float(population_fitness[0])
        best_fitness_history.append(best_fitness)

        # Nova geração (elitismo + crossover + mutação)
        new_population = [population[0]]

        pool = population[:top_for_selection]
        pool_fitness = population_fitness[:top_for_selection]
        # Evita divisão por zero (fitness muito pequeno)
        inv_fit = 1.0 / (np.array(pool_fitness, dtype=float) + 1e-9)

        while len(new_population) < population_size:
            parent1, parent2 = random.choices(pool, weights=inv_fit, k=2)
            child = order_crossover(parent1, parent2)
            child = mutate(child, mutation_prob)
            new_population.append(child)

        population = new_population

        if generation <= 3 or generation % 10 == 0 or generation == n_generations:
            print(f"Geração {generation:3d}: melhor fitness = {best_fitness:.4f}")

    # Componentes estruturados do resultado (para LLM e relatório)
    best_route_ids = [city_to_id_map[c] for c in best_solution]
    total_distance = float(
        calculate_total_distance(
            best_solution,
            hospital_coords,
            city_to_id_map=city_to_id_map,
            distance_matrix=distance_matrix,
        )
    )
    priority_penalty = float(calculate_priority_penalty(best_solution, priorities, city_to_id_map, hospital_coords))
    capacity_penalty = float(
        calculate_capacity_penalty(best_solution, demands, city_to_id_map, hospital_coords, vehicle_capacity)
    )

    result = {
        "config_used": cfg,
        "best_route": best_route_ids,
        "metrics": {
            "total_distance": total_distance,
            "priority_penalty": priority_penalty,
            "capacity_penalty": capacity_penalty,
            "fitness_final": float(best_fitness),
        },
        "history": {
            "best_fitness_by_generation": best_fitness_history,
        },
    }

    print("=" * 60)
    print(f"Melhor fitness final: {best_fitness:.4f}")
    print("Para rodar com visualização gráfica: python tsp.py")
    print("=" * 60)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Rodar AG em modo headless com config estruturada.")
    parser.add_argument("--config-json", type=str, default=None, help="Caminho para um JSON de configuração.")
    parser.add_argument("--out-json", type=str, default=None, help="Caminho para salvar o resultado em JSON.")
    parser.add_argument("--objective", type=str, default=None, help="Objetivo em linguagem natural (usa LLM).")
    parser.add_argument("--explain", action="store_true", help="Gerar explicação humana via LLM ao final.")
    args = parser.parse_args()

    user_config = None
    if args.objective:
        user_config = llm_to_config(args.objective)
    elif args.config_json:
        with open(args.config_json, "r", encoding="utf-8") as f:
            user_config = json.load(f)

    result = run_ga_headless(user_config or {})

    if args.out_json:
        out_path = args.out_json
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Resultado salvo em: {out_path}")

    if args.explain:
        try:
            explanation = llm_to_explanation(result)
            print("\n" + "-" * 60)
            print("Explicação (LLM)")
            print("-" * 60)
            print(explanation)
            print("-" * 60)
        except Exception as e:
            print("\n(Não foi possível gerar explicação via LLM.)")
            print(str(e))


if __name__ == "__main__":
    main()

"""
Exemplos:
  python run_headless.py\n
  python run_headless.py --config-json config.json --out-json result.json\n
Schema de config esperado (campos opcionais; defaults serão aplicados):\n
{\n
  \"population_size\": 100,\n
  \"n_generations\": 80,\n
  \"mutation_prob\": 0.3,\n
  \"top_for_selection\": 10,\n
  \"vehicle_capacity\": 15,\n
  \"weights\": {\"distance\": 0.3, \"priority\": 0.5, \"capacity\": 0.2}\n
}\n
"""
