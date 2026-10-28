// Acumula cones recebidos em slots (1 cone por frame CAN) numa Map idx -> cone.
import { createEffect, createSignal, onCleanup } from 'solid-js'
import { signals } from '../../store.js'
import { DV_SLOTS } from '../../config/dvConfig.js'

export function createConeTracker(kind, ttlMs) {
    const cones = new Map()
    const [version, setVersion] = createSignal(0)

    for (let k = 0; k < DV_SLOTS; k++) {
        const p = `DV_${kind}_${String(k).padStart(2, '0')}`
        createEffect(() => {
            const idx = signals[`${p}_IDX`], x = signals[`${p}_X`], y = signals[`${p}_Y`]
            const color = signals[`${p}_COLOR`]
            if (!idx || !x || !y) return
            cones.set(idx.value, { x: x.value, y: y.value, color: color?.value ?? 0, seen: performance.now() })
            setVersion(v => v + 1)
        })
    }

    const timer = setInterval(() => {
        const now = performance.now()
        let changed = false
        for (const [i, c] of cones) if (now - c.seen > ttlMs) { cones.delete(i); changed = true }
        if (changed) setVersion(v => v + 1)
    }, 200)
    onCleanup(() => clearInterval(timer))

    return { cones, version }
}
