
"""
Dados do contexto hospitalar para o TSP médico.
- priorities: urgência (0=crítico, 1=regular, 2=insumo).
- demands: carga em unidades que cada entrega consome do veículo.
- VEHICLE_CAPACITY: capacidade máxima do veículo por viagem.
  Restrição: soma(demands dos pontos da rota) <= VEHICLE_CAPACITY.
"""

priorities = {
    0: 0,  # HOSPITAL
    1: 2,  # 🟢 Insumo administrativo - PRIORIDADE MÍNIMA
    2: 1,  # 🟡 Medicamento regular - PRIORIDADE MÉDIA
    3: 0,  # 🔴 Crítico (Oncologia)
    4: 2,  # 🟢 Insumo comum
    5: 1,  # 🟡 Medicamento regular
    6: 0,  # 🔴 Crítico
    7: 2,  # 🟢 Insumo administrativo
    8: 1,  # 🟡 Medicamento regular
    9: 0,  # 🔴 Crítico
    10: 2, # 🟢 Insumo comum
    11: 1, # 🟡 Medicamento regular
    12: 0, # 🔴 Crítico
    13: 2, # 🟢 Insumo administrativo
    14: 1, # 🟡 Medicamento regular
    15: 0,  # 🔴 Crítico
}

# Carga (unidades) que cada ponto consome na entrega. Hospital = 0.
# Críticos = 3, regular = 2, insumo = 1 (exemplo).
demands = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 1, 5: 2, 6: 3, 7: 1, 8: 2, 9: 3,
    10: 1, 11: 2, 12: 3, 13: 1, 14: 2, 15: 3,
}

# Capacidade máxima do veículo por viagem. Rota válida se soma(demands da rota) <= este valor.
VEHICLE_CAPACITY = 15
