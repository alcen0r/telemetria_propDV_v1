# Telemetria DV integrada à V2.0

Dois dashboards, como combinado:
1. **Principal (ao vivo):** o dashboard do carro pilotado que você já tem, agora com 3 gauges do motor de steering (ângulo, corrente, temperatura) no Cockpit. Há também uma aba extra **DV Mapa/Percepção** ao vivo.
2. **Secundário (análise):** `dv-analysis/plotmap.py` lê as sessões gravadas, monta o mapa de cones a partir das coordenadas da percepção e gera um HTML no estilo do relatório "Telemetria do Mapeamento".

```
ROS2 (lidar_node, mapeamento, controle) ─► dv-edge (Jetson) ─► TCP :8080 ─► telemetry-server ─► WS ─► dashboard principal
CAN do steering ─► telemetry-edge (já existente) ───────────────┘            (DV.dbc decodifica)
                           └─► sessions/*.jsonl ─► dv-analysis/plotmap.py ─► relatorio/index.html (+ PNG do mapa)
```

## Pastas novas
| Caminho | O que é |
|---|---|
| `dv-edge/` | Programa da Jetson: ROS2 → frames CAN virtuais (mesmo protocolo do telemetry-edge: TCP 24 B/frame, NTP, reconexão, backup SQLite) e gravação de sessões `.jsonl`. `--mock` simula tudo. |
| `dv-edge/dv_edge/messages.py` | Fonte única dos IDs/bits das mensagens DV. `python3 tools/gen_dv_dbc.py` gera o `telemetry-server/dbc_data/DV.dbc`. |
| `dv-analysis/` | `plotmap.py` + módulos: carregar sessão, montar mapa (associação, voto de cor, confirmação com 3 detecções, compensação de latência), métricas e dashboard HTML. |
| `telemetry-server/static/src/components/DV/`, `config/dvConfig.js` | Aba ao vivo de mapa/percepção e gauges do steering. `App.jsx` alterado. |
| `tools/fake_server.py` | Servidor falso para testar sem o telemetry-server. |

## Rodar
```bash
# teste local, sem carro
python3 tools/fake_server.py 8080 &
cd dv-edge && python3 -m dv_edge.main --mock --server 127.0.0.1:8080    # grava dv-edge/sessions/*.jsonl

# análise (dashboard secundário)
python3 dv-analysis/plotmap.py dv-edge/sessions/*.jsonl -o relatorio    # abre relatorio/index.html
python3 dv-analysis/plotmap.py --demo -o relatorio_demo                 # dados sintéticos

# testes
python3 -m unittest discover -s dv-edge/tests && python3 -m unittest discover -s dv-analysis/tests

# carro (Jetson, ROS2 carregado)
cd dv-edge && python3 -m dv_edge.main --server 143.106.207.21:8080
# servidor: cp telemetry-server/.env.example telemetry-server/.env (preencher); cargo run --release; cd static && npm ci && npm run build
```

## Como o plotmap monta o mapa
- A percepção (`/lidar_node/cones`, Float32MultiArray) vem no **frame do carro** (x à frente, y à esquerda). O script converte para o frame do mapa com a pose.
- Como a mensagem **não tem header**, a pose usada é a de `t − latência` (padrão 0,1 s, `--latency`). No relatório do mapeamento isso vale ~0,2 m de RMSE.
- Associação por posição (0,5 m), voto de cor ponderado pela distância, cone confirmado com ≥3 detecções; os demais viram "fantasmas".
- Referência de comparação: ground truth se existir (simulador); em carro real, o mapa publicado pelo mapeamento (então mede consistência percepção × mapeamento).
- Métricas: voltas e tempos, precisão/recall/RMSE do mapa (volta 1 e final), cor, latência, cones por frame, erro do steering (comando × real), corrente e temperatura. Os limites dos alertas estão em `dv_analysis/analysis.py` (`LIM`).

## O que você precisa conferir (TODO no código)
1. **Layout de `/lidar_node/cones`:** `CONE_STRIDE = 3` em `ros_source.py` assume `[x, y, cor]` por cone.
2. **Tópicos e tipos do mapeamento/controle** em `ros_source.py` (`TOPICS`).
3. **ID e layout CAN do steering** em `messages.py` (`ID_STEER`, hoje `0x650` provisório; `0x201` já é usado por outro DBC). No carro, o steering chega pelo CAN via `telemetry-edge`; o `dv-edge` só gera esse frame no `--mock`.
4. **IP do servidor:** o telemetry-edge tem `143.106.207.95:8080` como padrão e o README fala em `143.106.207.21`. Usei `.21`; troque com `--server`.
5. **Enums de AS state/missão** em `config/dvConfig.js` e `analysis.py`.

## Segurança
O `.env` original tinha `UNIFI_API_KEY` e outros segredos; não foi incluído (há `.env.example`). Se o zip foi para o GitHub, vale girar essa chave.
