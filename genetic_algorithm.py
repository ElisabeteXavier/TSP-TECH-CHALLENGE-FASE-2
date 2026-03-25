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

def split_deliveries_multi_vehicles(
    path: List[Tuple[float, float]],
    depot_coords: Tuple[float, float],
    n_vehicles: int = 2,
    demands: Dict[int, int] = None,
    city_to_id_map: Dict[Tuple[float, float], int] = None,
    vehicle_capacity: float = None,
) -> Tuple[List[List[Tuple[float, float]]], Dict[str, Any]]:
    """
    Divide entregas entre N veículos usando estratégia adaptativa.
    - 2 veículos: corte por mediana + balanceamento por capacidade
    - 3+ veículos: divisão sequencial balanceada por capacidade
    """
    deliveries = [p for p in path if p != depot_coords]
    
    if not deliveries:
        return [[] for _ in range(n_vehicles)], {"strategy": "empty", "fallback": False}
    
    use_capacity = (
        demands is not None and
        city_to_id_map is not None and
        vehicle_capacity is not None and
        vehicle_capacity > 0
    )
    
    if n_vehicles == 2:
        vehicles_routes, split_info = _split_by_median(
            deliveries, depot_coords,
            demands=demands, city_to_id_map=city_to_id_map,
            vehicle_capacity=vehicle_capacity, use_capacity=use_capacity
        )
        return vehicles_routes, split_info
    
    return _split_sequential(
        deliveries, n_vehicles,
        demands=demands, city_to_id_map=city_to_id_map,
        vehicle_capacity=vehicle_capacity, use_capacity=use_capacity
    )


def _split_by_median(
    deliveries: List[Tuple[float, float]],
    depot_coords: Tuple[float, float],
    demands: Dict[int, int] = None,
    city_to_id_map: Dict[Tuple[float, float], int] = None,
    vehicle_capacity: float = None,
    use_capacity: bool = False,
) -> Tuple[List[List[Tuple[float, float]]], Dict[str, Any]]:
    """
    Divisão por mediana (para 2 veículos).
    Se use_capacity=True, distribui por capacidade para evitar estouro.
    """
    dx = [p[0] - depot_coords[0] for p in deliveries]
    dy = [p[1] - depot_coords[1] for p in deliveries]
    
    use_x = _std(dx) >= _std(dy)
    axis = "x" if use_x else "y"
    axis_values = [p[0] if use_x else p[1] for p in deliveries]
    threshold = _median(axis_values)
    
    # Ordena por eixo para manter coerência geográfica
    sorted_pairs = sorted(zip(deliveries, axis_values), key=lambda x: x[1])
    
    vehicle_1 = []
    vehicle_2 = []
    load_1 = 0.0
    load_2 = 0.0
    fallback = False
    
    def _demand(coord: Tuple[float, float]) -> float:
        if not use_capacity or not city_to_id_map or not demands:
            return 0.0
        cid = city_to_id_map.get(coord, 0)
        return float(demands.get(cid, 0))
    
    if use_capacity and vehicle_capacity and vehicle_capacity > 0:
        # Distribuição por capacidade na ORDEM DO PATH (não axis) — o GA otimiza o path,
        # então o split deve depender da ordem para que fitness varie entre indivíduos
        cap = float(vehicle_capacity)
        for p in deliveries:
            d = _demand(p)
            # Coloca no veículo que tem mais espaço e que comporta a demanda
            fits_1 = load_1 + d <= cap
            fits_2 = load_2 + d <= cap
            if fits_1 and fits_2:
                # Ambos comportam: escolhe o com menor carga (balanceia)
                if load_1 <= load_2:
                    vehicle_1.append(p)
                    load_1 += d
                else:
                    vehicle_2.append(p)
                    load_2 += d
            elif fits_1:
                vehicle_1.append(p)
                load_1 += d
            elif fits_2:
                vehicle_2.append(p)
                load_2 += d
            else:
                # Nenhum comporta (entrega única > capacidade): coloca no menos carregado
                fallback = True
                if load_1 <= load_2:
                    vehicle_1.append(p)
                    load_1 += d
                else:
                    vehicle_2.append(p)
                    load_2 += d
    else:
        # Comportamento original: corte por mediana
        for p, v in sorted_pairs:
            if v <= threshold:
                vehicle_1.append(p)
            else:
                vehicle_2.append(p)
    
    if len(vehicle_1) == 0 or len(vehicle_2) == 0:
        fallback = True
        vehicle_1, vehicle_2 = [], []
        for i, p in enumerate(deliveries):
            if i % 2 == 0:
                vehicle_1.append(p)
            else:
                vehicle_2.append(p)
    
    return [vehicle_1, vehicle_2], {"axis": axis, "threshold": threshold, "fallback": fallback}


def _split_sequential(
    deliveries: List[Tuple[float, float]],
    n_vehicles: int,
    demands: Dict[int, int] = None,
    city_to_id_map: Dict[Tuple[float, float], int] = None,
    vehicle_capacity: float = None,
    use_capacity: bool = False,
) -> Tuple[List[List[Tuple[float, float]]], Dict[str, Any]]:
    """Divisão sequencial balanceada (para 3+ veículos), respeitando capacidade quando disponível."""
    vehicles = [[] for _ in range(n_vehicles)]
    loads = [0.0] * n_vehicles
    
    def _demand(coord: Tuple[float, float]) -> float:
        if not use_capacity or not city_to_id_map or not demands:
            return 0.0
        cid = city_to_id_map.get(coord, 0)
        return float(demands.get(cid, 0))
    
    cap = float(vehicle_capacity) if (use_capacity and vehicle_capacity and vehicle_capacity > 0) else float("inf")
    fallback = False
    
    for i, point in enumerate(deliveries):
        d = _demand(point)
        if use_capacity and cap < float("inf"):
            # Encontra o veículo com menor carga que comporta
            best_idx = None
            best_load = float("inf")
            for j in range(n_vehicles):
                if loads[j] + d <= cap and loads[j] < best_load:
                    best_idx = j
                    best_load = loads[j]
            if best_idx is not None:
                vehicles[best_idx].append(point)
                loads[best_idx] += d
            else:
                # Nenhum comporta: coloca no menos carregado
                fallback = True
                idx = min(range(n_vehicles), key=lambda j: loads[j])
                vehicles[idx].append(point)
                loads[idx] += d
        else:
            # Sequencial simples (round-robin)
            idx = i % n_vehicles
            vehicles[idx].append(point)
            loads[idx] += d
    
    for i in range(n_vehicles):
        if not vehicles[i]:
            fallback = True
            max_idx = max(range(n_vehicles), key=lambda j: len(vehicles[j]))
            if vehicles[max_idx]:
                point = vehicles[max_idx].pop()
                vehicles[i].append(point)
    
    return vehicles, {"strategy": "sequential", "fallback": fallback}


def calculate_fitness(
    path: List[Tuple[float, float]],
    priorities: Dict[int, int],
    city_to_id_map: Dict[Tuple[float, float], int],
    hospital_coords: Tuple[float, float],
    distance_matrix: List[List[float]] = None,
    demands: Dict[int, int] = None,
    vehicle_capacity: float = None,
    weights: Dict[str, float] = None,
    vehicle_max_autonomy: float = None, 
    n_vehicles: int = 2,
) -> Dict[str, Any]:
    """
    Fitness unificado para qualquer número de veículos.
    """
    if weights is None:
        weights = {}
    
    w_dist = float(weights.get("distance", 0.3))
    w_prio = float(weights.get("priority", 0.5 if (demands is not None and vehicle_capacity is not None) else 0.7))
    w_cap = float(weights.get("capacity", 0.2))
    w_auto = float(weights.get("autonomy", 0.2))
    
    # Divide as rotas entre os veículos (respeitando capacidade)
    vehicles_routes, split_info = split_deliveries_multi_vehicles(
        path, hospital_coords, n_vehicles,
        demands=demands, city_to_id_map=city_to_id_map,
        vehicle_capacity=vehicle_capacity,
    )
    
    # Calcula métricas totais
    total_distance = 0.0
    total_priority_penalty = 0.0
    total_capacity_penalty = 0.0
    total_autonomy_penalty = 0.0
    
    routes_dict = {}
    metrics_dict = {"total_distance": 0.0, "priority_penalty": 0.0, "capacity_penalty": 0.0}
    
    for i, route in enumerate(vehicles_routes):
        vehicle_id = f"vehicle_{i+1}"
        routes_dict[vehicle_id] = route
        
        if route:
            dist = calculate_total_distance(
            route, hospital_coords,
            city_to_id_map=city_to_id_map,
            distance_matrix=distance_matrix)

            if vehicle_max_autonomy is not None:
                autonomy_penalty = calculate_autonomy_penalty(
                    dist,
                    vehicle_max_autonomy
                )
                total_autonomy_penalty += autonomy_penalty

            prio = calculate_priority_penalty(route, priorities, city_to_id_map, hospital_coords)
            
            total_distance += dist
            total_priority_penalty += prio
            
            metrics_dict[f"distance_v{i+1}"] = float(dist)
            
            if demands is not None and vehicle_capacity is not None:
                cap = calculate_capacity_penalty(route, demands, city_to_id_map, hospital_coords, vehicle_capacity)
                total_capacity_penalty += cap
        else:
            metrics_dict[f"distance_v{i+1}"] = 0.0
    
    metrics_dict["total_distance"] = total_distance
    metrics_dict["priority_penalty"] = total_priority_penalty  
    metrics_dict["capacity_penalty"] = total_capacity_penalty
    metrics_dict["autonomy_penalty"] = total_autonomy_penalty
    
    # Calcula fitness final
    if demands is not None and vehicle_capacity is not None:
        fitness = (
            w_dist * total_distance +
            w_prio * total_priority_penalty +
            w_cap * total_capacity_penalty +
            w_auto * total_autonomy_penalty
        )
    else:
        fitness = w_dist * total_distance + w_prio * total_priority_penalty
    
    return {
        "fitness": float(fitness),
        "split": split_info,
        "routes": routes_dict,
        "metrics": {
            **metrics_dict,
            "fitness_final": float(fitness),
        },
    }

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


def calculate_autonomy_penalty(route_distance, max_autonomy, weight=10):
    if route_distance <= max_autonomy:
        return 0

    excess_ratio = (route_distance - max_autonomy) / max_autonomy

    # Penalidade baseada em porcentagem + crescimento exponencial
    return weight * (excess_ratio ** 2) * max_autonomy