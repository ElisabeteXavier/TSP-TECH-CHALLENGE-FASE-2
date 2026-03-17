"""
Script para rodar o algoritmo genético SEM interface gráfica.
Útil para entender o fluxo e validar o funcionamento.
Roda N gerações e exibe o progresso no terminal.
"""
import random
import itertools
import numpy as np
from genetic_algorithm import (
    mutate, order_crossover, generate_random_population,
    calculate_fitness, sort_population, default_problems, build_distance_matrix
)
from hospital_data import priorities

# Configuração
N_GENERATIONS = 50
POPULATION_SIZE = 100
MUTATION_PROBABILITY = 0.5

# Dados do problema
cities_locations = default_problems[15]
HOSPITAL_COORDS = cities_locations[0]
city_to_id_map = {location: i for i, location in enumerate(cities_locations)}
distance_matrix = build_distance_matrix(cities_locations)  # Aula 4: uma vez no início

print("=" * 60)
print("TSP - Otimização de Rotas Médicas (Modo Console)")
print("=" * 60)
print(f"Pontos de entrega: {len(cities_locations)} (incl. hospital)")
print(f"População: {POPULATION_SIZE} | Mutação: {MUTATION_PROBABILITY}")
print(f"Gerações: {N_GENERATIONS}")
print("=" * 60)

# População inicial
population = generate_random_population(cities_locations, POPULATION_SIZE)
best_fitness_values = []

for generation in range(1, N_GENERATIONS + 1):
    # Avaliar fitness de cada indivíduo
    population_fitness = [
        calculate_fitness(ind, priorities, city_to_id_map, HOSPITAL_COORDS, distance_matrix)
        for ind in population
    ]

    # Ordenar: menor fitness = melhor
    population, population_fitness = sort_population(population, population_fitness)

    best_solution = population[0]
    best_fitness = population_fitness[0]
    best_fitness_values.append(best_fitness)

    # Nova geração (elitismo + crossover + mutação)
    new_population = [population[0]]  # Elitismo: mantém o melhor

    while len(new_population) < POPULATION_SIZE:
        prob = 1 / np.array(population_fitness)
        parent1, parent2 = random.choices(population, weights=prob, k=2)
        child = order_crossover(parent1, parent2)  # Corrigido: usa 2 pais
        child = mutate(child, MUTATION_PROBABILITY)
        new_population.append(child)

    population = new_population

    # Log a cada 5 gerações ou na primeira/última
    if generation <= 3 or generation % 10 == 0 or generation == N_GENERATIONS:
        print(f"Geração {generation:3d}: melhor fitness = {best_fitness:.2f}")

print("=" * 60)
print(f"Melhor fitness final: {best_fitness:.2f}")
print("Para rodar com visualização gráfica: python tsp.py")
print("(Feche a janela ou pressione Q para sair)")
print("=" * 60)
