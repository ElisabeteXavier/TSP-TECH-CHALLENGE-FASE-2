# 🧬 Tech Challenge – Fase 2  
## Otimização de Rotas Médicas com Algoritmos Genéticos

Este projeto faz parte do **Tech Challenge – Fase 2** e tem como objetivo desenvolver um sistema de **otimização de rotas para distribuição de medicamentos e insumos hospitalares**, utilizando **Algoritmos Genéticos** e **Inteligência Artificial (LLMs)** para geração de instruções e relatórios.

---

## 🎯 Objetivo do Projeto

Resolver um problema de **roteamento logístico hospitalar**, inspirado no problema do **Caixeiro Viajante (TSP)**, considerando restrições realistas como:

- Prioridade de entregas (medicamentos críticos x insumos regulares)
- Capacidade limitada dos veículos
- Autonomia máxima de distância
- Possibilidade de múltiplos veículos (VRP)
- Visualização das rotas otimizadas
- Geração de relatórios e instruções em linguagem natural com LLMs

---

## 🧠 Tecnologias Utilizadas

- Python 3.12
- Algoritmos Genéticos
- pygame
- matplotlib
- (futuramente) Integração com LLMs
- Ambiente virtual (venv)

---

## 📁 Estrutura do Projeto

```text
TSP-TECH-CHALLENGE-FASE-2/
│
├── venv/                 # Ambiente virtual
├── tsp.py                # Script principal
├── draw_functions.py     # Funções de visualização
├── src/                  # (opcional) módulos organizados
├── tests/                # Testes automatizados
├── README.md
├── requirements.txt
└── .gitignore
