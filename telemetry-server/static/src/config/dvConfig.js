// Configuração da telemetria DV (driverless). Os nomes dos sinais vêm do DV.dbc
// (gerado por tools/gen_dv_dbc.py a partir de dv-edge/dv_edge/messages.py).

export const DV_SLOTS = 16  // precisa ser igual a SLOTS em messages.py

// TODO conferir com o Controle_DV_2026 (enum real do AS state / missão)
export const DV_AS_STATES = { 0: '—', 1: 'AS Off', 2: 'AS Ready', 3: 'AS Driving', 4: 'AS Finished', 5: 'AS Emergency' }
export const DV_MISSIONS  = { 0: '—', 1: 'Acceleration', 2: 'Skidpad', 3: 'Autocross', 4: 'Trackdrive', 5: 'EBS Test', 6: 'Inspection', 7: 'Manual' }

export const DV_CONE_COLORS = { 0: '#8b93a1', 1: '#f2c230', 2: '#4c9aff', 3: '#ff8a3d', 4: '#ff5a1f' }

export const DV_PERC_TTL_MS = 600    // cone percebido some se não for reenviado nesse tempo
export const DV_MAP_TTL_MS  = 15000  // cone do mapa (reenviado a ~5 Hz por slot)
export const DV_TRAIL_POINTS = 400

// Gauges do motor de steering, somados aos gauges normais na tela de Controle
export const DV_STEER_GAUGES = [
    { signalName: 'STEER_ANGLE',   label: 'Steering',     min: -30, max: 30,  unit: '°', warnMax: 25, critMax: 28 },
    { signalName: 'STEER_CURRENT', label: 'Corr. steering', min: 0, max: 20, unit: 'A', warnMax: 12, critMax: 16 },
    { signalName: 'STEER_TEMP',    label: 'Temp. steering', min: 0, max: 100, unit: '°C', warnMax: 70, critMax: 85 },
]

