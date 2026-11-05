import { For } from 'solid-js'
import { signals } from '../../store.js'
import DVMapCanvas from './DVMapCanvas.jsx'
import { createConeTracker } from './dvCones.js'
import { DV_AS_STATES, DV_MISSIONS, DV_MAP_TTL_MS, DV_PERC_TTL_MS } from '../../config/dvConfig.js'
import './DV.css'

const v = (name, digits = 0, fallback = '—') => {
    const x = signals[name]?.value
    return x === undefined ? fallback : Number(x).toFixed(digits)
}

// Tela 1 da DV: mapeamento + percepção.
function DVMapPage() {
    const map = createConeTracker('MAP', DV_MAP_TTL_MS)
    const perc = createConeTracker('PERC', DV_PERC_TTL_MS)
    const cards = () => [
        ['Estado AS', DV_AS_STATES[signals.DV_AS_STATE?.value] ?? '—', ''],
        ['Missão', DV_MISSIONS[signals.DV_MISSION?.value] ?? '—', ''],
        ['Volta', v('DV_LAP'), ''],
        ['Mapa travado', signals.DV_MAP_LOCKED?.value ? 'sim' : 'não', ''],
        ['Cones no mapa', v('DV_MAP_CONES_N'), ''],
        ['Cones percebidos', v('DV_PERC_CONES_N'), ''],
        ['Latência mapeamento', v('DV_MAP_LAT_MS', 1), 'ms'],
        ['Latência percepção', v('DV_PERC_LAT_MS', 1), 'ms'],
        ['Velocidade', v('DV_SPEED', 1), 'm/s'],
        ['Pose x / y', `${v('DV_POSE_X', 1)} / ${v('DV_POSE_Y', 1)}`, 'm'],
    ]
    return (
        <main class="dv-page">
            <section class="dv-panel dv-panel--map">
                <DVMapCanvas map={map} perc={perc} />
                <div class="dv-legend">● mapa (amarelo/azul/laranja) · ○ percebido agora · ▶ carro</div>
            </section>
            <section class="dv-cards">
                <For each={cards()}>{([label, value, unit]) => (
                    <div class="dv-card"><small>{label}</small><b>{value}</b> <span>{unit}</span></div>
                )}</For>
            </section>
        </main>
    )
}

export default DVMapPage
