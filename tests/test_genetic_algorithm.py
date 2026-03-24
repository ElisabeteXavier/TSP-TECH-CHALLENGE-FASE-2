def test_mutate_integrity(self):
        # Rota de exemplo usando coordenadas conforme esperado pelo algoritmo [2]
        route = [(0,0), (1,1), (2,2), (3,3), (4,4)]
        
        # Agora passando o argumento 'mutation_probability' exigido pela função [1]
        # Usamos 1.0 para garantir que a mutação ocorra durante o teste unitário
        mutated = mutate(route.copy(), 1.0) 
        
        # Verifica se a integridade da rota foi mantida
        self.assertEqual(len(mutated), 5)
        self.assertEqual(set(route), set(mutated))
