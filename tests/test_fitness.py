import unittest
from genetic_algorithm import calculate_fitness

class TestFitness(unittest.TestCase):
    def test_fitness_components(self):
        individual = [(100, 100), (200, 200), (150, 300), (400, 100), (50, 50)]
        priorities = {0: 1, 1: 2, 2: 1, 3: 1, 4: 2}
        city_to_id_map = {0: (100, 100), 1: (200, 200), 2: (150, 300), 3: (400, 100), 4: (50, 50)}
        hospital_coords = (400, 200)

        fitness_score = calculate_fitness(individual, priorities, city_to_id_map, hospital_coords)
        
        self.assertIsInstance(fitness_score, (float, int))
        self.assertGreater(fitness_score, 0)