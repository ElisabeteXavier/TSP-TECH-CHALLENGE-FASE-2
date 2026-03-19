# 🚚 Otimizador de Rotas Médicas com Algoritmo Genético (2 Veículos)

Projeto acadêmico de otimização de rotas para distribuição médica, considerando múltiplos critérios:
- 📏 distância total percorrida;
- 🚨 prioridade de atendimento;
- 📦 capacidade do veículo.

A solução evolui o cenário de **1 veículo** para **2 veículos**, com divisão automática de entregas por **corte espacial dinâmico**.

---

## 📌 Visão Geral

Este projeto busca minimizar o custo logístico de entregas partindo de um depósito (no código legado chamado de `hospital`), retornando ao depósito ao fim da rota.

Cada solução é avaliada com base em uma função de fitness multiobjetivo que combina:
1. distância;
2. prioridade;
3. capacidade.

---

## 🎯 Objetivo

Encontrar, por meio de Algoritmo Genético, rotas eficientes para dois veículos:

- Veículo 1: `depot -> a -> b -> c -> depot`
- Veículo 2: `depot -> d -> e -> f -> depot`

Com minimização de custo global:
- menor distância total;
- menor atraso de pontos críticos;
- menor violação de capacidade.

---

## 🧠 Estratégia de Modelagem

### 1) Representação

Cada indivíduo do AG representa uma ordem de visita das entregas.  
A partir dessa ordem, o sistema separa os pontos em duas rotas.

### 2) Split em 2 veículos (corte dinâmico)

A divisão de entregas usa lógica adaptativa (sem cortes fixos hardcoded):

1. Remove o depósito da lista de entregas;
2. Calcula dispersão espacial:
   - `dx = x - depot_x`
   - `dy = y - depot_y`
3. Escolhe o eixo com maior dispersão:
   - `std(dx) >= std(dy)` → corte vertical;
   - caso contrário → corte horizontal;
4. Usa mediana do eixo escolhido como threshold;
5. Atribui os pontos:
   - `<= threshold` → veículo 1
   - `> threshold` → veículo 2
6. Em caso degenerado (grupo vazio), aplica fallback balanceado.

✅ Vantagem: funciona mesmo se as coordenadas mudarem.

---

## 📐 Função de Fitness

A função de custo usada é:

\[
fitness = w_{dist}\cdot D + w_{prio}\cdot P + w_{cap}\cdot C
\]

Onde:

- `D`: distância total (`D_v1 + D_v2`);
- `P`: penalidade por atraso de prioridade;
- `C`: penalidade por excesso de capacidade.

### Distância (`D`)
Cada rota é fechada:
- `depot -> entregas -> depot`

### Prioridade (`P`)
Penaliza entregas críticas realizadas mais tarde na ordem da rota.

### Capacidade (`C`)
Para cada veículo:
\[
\max(0, carga\_total - capacidade)
\]

---

## ⚙️ Algoritmo Genético (decisões implementadas)

- **Seleção:** roleta ponderada por aptidão inversa (`1/fitness`);
- **Crossover:** Order Crossover (OX), apropriado para permutações;
- **Mutação:** troca de vizinhos (swap adjacente);
- **Elitismo:** melhor indivíduo preservado na nova geração.

---

## 🚀 Otimização de Desempenho

Foi utilizada **matriz de distâncias pré-computada** em vez de recalcular distância euclidiana a cada avaliação:

- `D[i][j] = distância entre cidade i e j`
- ganho de eficiência nas gerações do AG.

---

## 🧩 Estrutura do Projeto

- `genetic_algorithm.py` → núcleo do AG, fitness, split 2 veículos;
- `run_headless.py` → execução em modo console e saída estruturada;
- `app.py` → interface Streamlit;
- `tsp.py` → visualização com Pygame;
- `hospital_data.py` → prioridades, demandas, capacidade;
- `schemas.py` → configurações padrão e schema.

---

## ▶️ Como Executar

### 1) Criar ambiente

### ⚙️ Instalação e Configuração
```bash
python -m venv venv
source venv/bin/activate
pip install streamlit matplotlib numpy pygame
```

### 2) Streamlit
```bash
streamlit run app.py
```

### 3) Console (headless)
```bash
python run_headless.py
```

### 4) Visualização Pygame
```bash
python tsp.py
```

---

### 📊 Saída esperada
* **Evolução do fitness** por geração;
* **Rotas separadas** por veículo;
* **Métricas:**
    * Fitness final;
    * Distância total;
    * Distância por veículo;
    * Penalidade de prioridade;
    * Penalidade de capacidade.

---

### 🧪 Limitações e Melhorias Futuras
* Comparar **corte dinâmico vs. KMeans (k=2)**;
* Testar **operadores de mutação** mais robustos (ex.: inversion, 2-opt);
* Adicionar **seed** para reprodutibilidade;
* Expandir para instâncias maiores e mais veículos.

---

### ✅ Conclusão
O projeto entrega uma solução de **roteirização multiobjetivo com AG** para 2 veículos, usando divisão espacial adaptativa e matriz de distâncias para eficiência.

A abordagem é consistente com o objetivo acadêmico e permite evolução para técnicas mais avançadas de clustering e refinamento de rotas.