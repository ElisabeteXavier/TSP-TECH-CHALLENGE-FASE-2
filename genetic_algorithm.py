import random
import math
import copy 
from typing import List, Tuple, Dict, Any

default_problems = {
5: [(733, 251), (706, 87), (546, 97), (562, 49), (576, 253)],
10:[(470, 169), (602, 202), (754, 239), (476, 233), (468, 301), (522, 29), (597, 171), (487, 325), (746, 232), (558, 136)],
12:[(728, 67), (560, 160), (602, 312), (712, 148), (535, 340), (720, 354), (568, 300), (629, 260), (539, 46), (634, 343), (491, 135), (768, 161)],
15:[(512, 317), (741, 72), (552, 50), (772, 346), (637, 12), (589, 131), (732, 165), (605, 15), (730, 38), (576, 216), (589, 381), (711, 387), (563, 228), (494, 22), (787, 288)]
}

def criate_population(tamanho_pop, hospitais, usar_hotstart=True):
    populacao = []
    if usar_hotstart:
        # Adiciona o indivíduo gerado pelo KNN (rota de coordenadas)
        individuo_elite = generate_route_knn(hospitais)
        populacao.append(individuo_elite)

        # Gera os outros indivíduos de forma aleatória (rotas de coordenadas)
        while len(populacao) < tamanho_pop:
            rota_aleatoria = random.sample(hospitais, len(hospitais))
            populacao.append(rota_aleatoria)
    else:
        # Apenas população aleatória
        for _ in range(tamanho_pop):
            rota_aleatoria = random.sample(hospitais, len(hospitais))
            populacao.append(rota_aleatoria)
    return populacao

def generate_random_population(cities_location: List[Tuple[float, float]], population_size: int) -> List[List[Tuple[float, float]]]:
    """
    Generate a random population of routes for a given set of cities.

    Parameters:
    - cities_location (List[Tuple[float, float]]): A list of tuples representing the locations of cities,
      where each tuple contains the latitude and longitude.
    - population_size (int): The size of the population, i.e., the number of routes to generate.

    Returns:
    List[List[Tuple[float, float]]]: A list of routes, where each route is represented as a list of city locations.
    """
    return [random.sample(cities_location, len(cities_location)) for _ in range(population_size)]


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate the Euclidean distance between two points.

    Parameters:
    - point1 (Tuple[float, float]): The coordinates of the first point.
    - point2 (Tuple[float, float]): The coordinates of the second point.

    Returns:
    float: The Euclidean distance between the two points.
    """
    return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


def build_distance_matrix(cities_locations: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Constrói a matriz de distâncias entre todas as cidades (Aula 4).
    D[i][j] = distância euclidiana entre cidade i e cidade j.
    Calculada UMA VEZ no início; depois só consultamos D[i][j].

    Parameters:
    - cities_locations: lista de (x, y) de cada cidade (índice = id da cidade).

    Returns:
    - Matriz n x n (list of lists), onde n = len(cities_locations).
    """
    n = len(cities_locations)
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = calculate_distance(cities_locations[i], cities_locations[j])
            D[i][j] = d
            D[j][i] = d  # matriz simétrica
    return D


def calculate_total_distance(
    path: List[Tuple[float, float]],
    hospital: Tuple[float, float],
    city_to_id_map: Dict[Tuple[float, float], int] = None,
    distance_matrix: List[List[float]] = None,
) -> float:
    """
    Distância total da rota: hospital -> path[0] -> ... -> path[-1] -> hospital.
    Se distance_matrix e city_to_id_map forem passados, usa a matriz (mais rápido).
    """
    if distance_matrix is not None and city_to_id_map is not None:
        # Aula 4: apenas consultar D[i][j], sem recalcular
        hid = city_to_id_map[hospital]
        ids = [city_to_id_map[coord] for coord in path]
        dist = distance_matrix[hid][ids[0]]
        for i in range(len(ids) - 1):
            dist += distance_matrix[ids[i]][ids[i + 1]]
        dist += distance_matrix[ids[-1]][hid]
        return dist
    # Fallback: cálculo pela distância euclidiana (comportamento antigo)
    dist = calculate_distance(hospital, path[0])
    for i in range(len(path) - 1):
        dist += calculate_distance(path[i], path[i + 1])
    dist += calculate_distance(path[-1], hospital)
    return dist

def generate_route_knn(hospitais):
    # hospitais: lista de coordenadas extraídas de hospital_data.py
    nao_visitados = hospitais.copy()
    rota = []

    # Começa no hospital (assumindo que o hospital é o primeiro da lista)
    atual = nao_visitados.pop(0)
    rota.append(atual)

    while nao_visitados:
        # encontra o ponto mais próximo de acordo com a lógica KNN
        proximo = min(nao_visitados, key=lambda x: calculate_distance(atual, x))
        nao_visitados.remove(proximo)
        rota.append(proximo)
        atual = proximo

    return rota

def calculate_priority_penalty(
    path: List[Tuple[float, float]], 
    priorities: Dict[int, int], 
    city_to_id_map: Dict[Tuple[float, float], int],
    hospital_coords: Tuple[float, float]
) -> float:
    """
    Calcula o componente Fp considerando a ordem de entrega após o hospital.
    """
    total_penalty: float = 0.0
    
    # Filtramos a rota para considerar apenas as entregas (removendo o hospital)
    deliveries = [city for city in path if city != hospital_coords]
    
    # O índice 'i' representa o quanto a entrega está 'atrasada'
    for i, city_coords in enumerate(deliveries):
        city_id = city_to_id_map.get(city_coords)
        if city_id is not None:
            prio = priorities.get(city_id, 2)
            
            # Peso de urgência: Prioridade 0 (crítica) tem peso maior [2]
            urgency_weight = (3 - prio) ** 2
            
            # Penalidade = Ordem da entrega * Peso da Urgência
            total_penalty += (i + 1) * urgency_weight
            
    return total_penalty


def calculate_capacity_penalty(
    path: List[Tuple[float, float]],
    demands: Dict[int, int],
    city_to_id_map: Dict[Tuple[float, float], int],
    hospital_coords: Tuple[float, float],
    vehicle_capacity: float,
) -> float:
    """
    Penalidade por estourar a capacidade do veículo (não matar a solução).
    Carga total da rota = soma das demandas dos pontos da rota.
    Retorna 0 se carga_total <= vehicle_capacity; senão retorna o excesso (carga_total - vehicle_capacity).
    """
    deliveries = [c for c in path if c != hospital_coords]
    carga_total = 0.0
    for city_coords in deliveries:
        cid = city_to_id_map.get(city_coords)
        if cid is not None:
            carga_total += demands.get(cid, 0)
    excesso = carga_total - vehicle_capacity
    return max(0.0, excesso)


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def _std(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def split_deliveries_two_vehicles(
    path: List[Tuple[float, float]],
    depot_coords: Tuple[float, float],
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], Dict[str, Any]]:
    """
    Separa entregas em 2 veículos usando corte dinâmico:
    - escolhe eixo com maior dispersão (std de dx vs dy)
    - threshold = mediana no eixo escolhido
    """
    deliveries = [p for p in path if p != depot_coords]

    if not deliveries:
        return [], [], {"axis": "x", "threshold": 0.0, "fallback": False}

    dx = [p[0] - depot_coords[0] for p in deliveries]
    dy = [p[1] - depot_coords[1] for p in deliveries]

    use_x = _std(dx) >= _std(dy)
    axis = "x" if use_x else "y"

    axis_values = [p[0] if use_x else p[1] for p in deliveries]
    threshold = _median(axis_values)

    vehicle_1 = []
    vehicle_2 = []

    for p in deliveries:
        v = p[0] if use_x else p[1]
        if v <= threshold:
            vehicle_1.append(p)
        else:
            vehicle_2.append(p)

    # fallback para evitar grupo vazio (especialmente em casos degenerados)
    fallback = False
    if len(vehicle_1) == 0 or len(vehicle_2) == 0:
        fallback = True
        vehicle_1, vehicle_2 = [], []
        for i, p in enumerate(deliveries):
            if i % 2 == 0:
                vehicle_1.append(p)
            else:
                vehicle_2.append(p)

    return vehicle_1, vehicle_2, {"axis": axis, "threshold": threshold, "fallback": fallback}


def evaluate_two_vehicle_solution(
    path: List[Tuple[float, float]],
    priorities: Dict[int, int],
    city_to_id_map: Dict[Tuple[float, float], int],
    depot_coords: Tuple[float, float],
    distance_matrix: List[List[float]] = None,
    demands: Dict[int, int] = None,
    vehicle_capacity: float = None,
    weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    if weights is None:
        weights = {}

    w_dist = float(weights.get("distance", 0.3))
    w_prio = float(weights.get("priority", 0.5 if (demands is not None and vehicle_capacity is not None) else 0.7))
    w_cap = float(weights.get("capacity", 0.2))

    route_v1, route_v2, split_info = split_deliveries_two_vehicles(path, depot_coords)

    dist_v1 = calculate_total_distance(
        route_v1, depot_coords, city_to_id_map=city_to_id_map, distance_matrix=distance_matrix
    ) if route_v1 else 0.0
    dist_v2 = calculate_total_distance(
        route_v2, depot_coords, city_to_id_map=city_to_id_map, distance_matrix=distance_matrix
    ) if route_v2 else 0.0

    prio_v1 = calculate_priority_penalty(route_v1, priorities, city_to_id_map, depot_coords) if route_v1 else 0.0
    prio_v2 = calculate_priority_penalty(route_v2, priorities, city_to_id_map, depot_coords) if route_v2 else 0.0

    if demands is not None and vehicle_capacity is not None:
        cap_v1 = calculate_capacity_penalty(route_v1, demands, city_to_id_map, depot_coords, vehicle_capacity) if route_v1 else 0.0
        cap_v2 = calculate_capacity_penalty(route_v2, demands, city_to_id_map, depot_coords, vehicle_capacity) if route_v2 else 0.0
    else:
        cap_v1 = 0.0
        cap_v2 = 0.0

    total_distance = float(dist_v1 + dist_v2)
    total_priority_penalty = float(prio_v1 + prio_v2)
    total_capacity_penalty = float(cap_v1 + cap_v2)

    if demands is not None and vehicle_capacity is not None:
        fitness = w_dist * total_distance + w_prio * total_priority_penalty + w_cap * total_capacity_penalty
    else:
        fitness = w_dist * total_distance + w_prio * total_priority_penalty

    return {
        "fitness": float(fitness),
        "split": split_info,
        "routes": {
            "vehicle_1": route_v1,
            "vehicle_2": route_v2,
        },
        "metrics": {
            "total_distance": total_distance,
            "priority_penalty": total_priority_penalty,
            "capacity_penalty": total_capacity_penalty,
            "distance_v1": float(dist_v1),
            "distance_v2": float(dist_v2),
        },
    }

# def calculate_fitness(
#     path: List[Tuple[float, float]],
#     priorities: Dict[int, int],
#     city_to_id_map: Dict[Tuple[float, float], int],
#     hospital_coords: Tuple[float, float],
#     distance_matrix: List[List[float]] = None,
#     demands: Dict[int, int] = None,
#     vehicle_capacity: float = None,
#     weights: Dict[str, float] = None,
# ) -> float:
#     """
#     Fitness = w_dist*distância + w_prio*prioridade + w_cap*penalidade_capacidade.
#     Se demands e vehicle_capacity não forem passados, usa só distância e prioridade.
#     """
#     if weights is None:
#         weights = {}
#     w_dist = float(weights.get("distance", 0.3))
#     w_prio = float(weights.get("priority", 0.5 if (demands is not None and vehicle_capacity is not None) else 0.7))
#     w_cap = float(weights.get("capacity", 0.2))

#     distancia = calculate_total_distance(
#         path, hospital_coords,
#         city_to_id_map=city_to_id_map,
#         distance_matrix=distance_matrix,
#     )
#     prioridade = calculate_priority_penalty(path, priorities, city_to_id_map, hospital_coords)

#     if demands is not None and vehicle_capacity is not None:
#         capacidade_penalty = calculate_capacity_penalty(
#             path, demands, city_to_id_map, hospital_coords, vehicle_capacity
#         )
#         fitness = w_dist * distancia + w_prio * prioridade + w_cap * capacidade_penalty
#     else:
#         fitness = w_dist * distancia + w_prio * prioridade

#     return fitness

def calculate_fitness(
    path: List[Tuple[float, float]],
    priorities: Dict[int, int],
    city_to_id_map: Dict[Tuple[float, float], int],
    hospital_coords: Tuple[float, float],
    distance_matrix: List[List[float]] = None,
    demands: Dict[int, int] = None,
    vehicle_capacity: float = None,
    weights: Dict[str, float] = None,
) -> float:
    """
    Fitness para 2 veículos:
    - separa entregas em 2 rotas via corte dinâmico (x ou y)
    - soma distância/prioridade/capacidade dos dois veículos
    """
    evaluated = evaluate_two_vehicle_solution(
        path=path,
        priorities=priorities,
        city_to_id_map=city_to_id_map,
        depot_coords=hospital_coords,
        distance_matrix=distance_matrix,
        demands=demands,
        vehicle_capacity=vehicle_capacity,
        weights=weights,
    )
    return float(evaluated["fitness"])


def order_crossover(parent1: List[Tuple[float, float]], parent2: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Perform order crossover (OX) between two parent sequences to create a child sequence.

    Parameters:
    - parent1 (List[Tuple[float, float]]): The first parent sequence.
    - parent2 (List[Tuple[float, float]]): The second parent sequence.

    Returns:
    List[Tuple[float, float]]: The child sequence resulting from the order crossover.
    """
    length = len(parent1)

    # Choose two random indices for the crossover
    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    # Initialize the child with a copy of the substring from parent1
    child = parent1[start_index:end_index]

    # Fill in the remaining positions with genes from parent2
    remaining_positions = [i for i in range(length) if i < start_index or i >= end_index]
    remaining_genes = [gene for gene in parent2 if gene not in child]

    for position, gene in zip(remaining_positions, remaining_genes):
        child.insert(position, gene)

    return child

### demonstration: crossover test code
# Example usage:
# parent1 = [(1, 1), (2, 2), (3, 3), (4,4), (5,5), (6, 6)]
# parent2 = [(6, 6), (5, 5), (4, 4), (3, 3),  (2, 2), (1, 1)]

# # parent1 = [1, 2, 3, 4, 5, 6]
# # parent2 = [6, 5, 4, 3, 2, 1]


# child = order_crossover(parent1, parent2)
# print("Parent 1:", [0, 1, 2, 3, 4, 5, 6, 7, 8])
# print("Parent 1:", parent1)
# print("Parent 2:", parent2)
# print("Child   :", child)


# # Example usage:
# population = generate_random_population(5, 10)

# print(calculate_fitness(population[0]))


# population = [(random.randint(0, 100), random.randint(0, 100))
#           for _ in range(3)]



# TODO: implement a mutation_intensity and invert pieces of code instead of just swamping two. 
def mutate(solution:  List[Tuple[float, float]], mutation_probability: float) ->  List[Tuple[float, float]]:
    """
    Mutate a solution by inverting a segment of the sequence with a given mutation probability.

    Parameters:
    - solution (List[int]): The solution sequence to be mutated.
    - mutation_probability (float): The probability of mutation for each individual in the solution.

    Returns:
    List[int]: The mutated solution sequence.
    """
    mutated_solution = copy.deepcopy(solution)

    # Check if mutation should occur    
    if random.random() < mutation_probability:
        
        # Ensure there are at least two cities to perform a swap
        if len(solution) < 2:
            return solution
    
        # Select a random index (excluding the last index) for swapping
        index = random.randint(0, len(solution) - 2)
        
        # Swap the cities at the selected index and the next index
        mutated_solution[index], mutated_solution[index + 1] = solution[index + 1], solution[index]   
        
    return mutated_solution

### Demonstration: mutation test code    
# # Example usage:
# original_solution = [(1, 1), (2, 2), (3, 3), (4, 4)]
# mutation_probability = 1

# mutated_solution = mutate(original_solution, mutation_probability)
# print("Original Solution:", original_solution)
# print("Mutated Solution:", mutated_solution)


def sort_population(population: List[List[Tuple[float, float]]], fitness: List[float]) -> Tuple[List[List[Tuple[float, float]]], List[float]]:
    """
    Sort a population based on fitness values.

    Parameters:
    - population (List[List[Tuple[float, float]]]): The population of solutions, where each solution is represented as a list.
    - fitness (List[float]): The corresponding fitness values for each solution in the population.

    Returns:
    Tuple[List[List[Tuple[float, float]]], List[float]]: A tuple containing the sorted population and corresponding sorted fitness values.
    """
    # Combine lists into pairs
    combined_lists = list(zip(population, fitness))

    # Sort based on the values of the fitness list
    sorted_combined_lists = sorted(combined_lists, key=lambda x: x[1])

    # Separate the sorted pairs back into individual lists
    sorted_population, sorted_fitness = zip(*sorted_combined_lists)

    return sorted_population, sorted_fitness


# if __name__ == '__main__':
#     N_CITIES = 10
    
#     POPULATION_SIZE = 100
#     N_GENERATIONS = 100
#     MUTATION_PROBABILITY = 0.3
#     cities_locations = [(random.randint(0, 100), random.randint(0, 100))
#               for _ in range(N_CITIES)]
    
#     # CREATE INITIAL POPULATION
#     population = generate_random_population(cities_locations, POPULATION_SIZE)

#     # Lists to store best fitness and generation for plotting
#     best_fitness_values = []
#     best_solutions = []
    
#     for generation in range(N_GENERATIONS):
  
        
#         population_fitness = [calculate_fitness(individual) for individual in population]    
        
#         population, population_fitness = sort_population(population,  population_fitness)
        
#         best_fitness = calculate_fitness(population[0])
#         best_solution = population[0]
           
#         best_fitness_values.append(best_fitness)
#         best_solutions.append(best_solution)    

#         print(f"Generation {generation}: Best fitness = {best_fitness}")

#         new_population = [population[0]]  # Keep the best individual: ELITISM
        
#         while len(new_population) < POPULATION_SIZE:
            
#             # SELECTION
#             parent1, parent2 = random.choices(population[:10], k=2)  # Select parents from the top 10 individuals
            
#             # CROSSOVER
#             child1 = order_crossover(parent1, parent2)
            
#             ## MUTATION
#             child1 = mutate(child1, MUTATION_PROBABILITY)
            
#             new_population.append(child1)
            
    
#         print('generation: ', generation)
#         population = new_population



