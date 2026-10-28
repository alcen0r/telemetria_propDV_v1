import { createEffect, onCleanup, onMount } from 'solid-js'
import { signals } from '../../store.js'
import { DV_CONE_COLORS, DV_TRAIL_POINTS } from '../../config/dvConfig.js'

// Desenha cones do mapa (preenchidos), cones percebidos (anel), carro e rastro.
function DVMapCanvas(props) {
    let canvas
    const trail = []
    let raf = 0

    const draw = () => {
        raf = 0
        if (!canvas) return
        const dpr = window.devicePixelRatio || 1
        const w = canvas.clientWidth, h = canvas.clientHeight
        if (canvas.width !== w * dpr) { canvas.width = w * dpr; canvas.height = h * dpr }
        const g = canvas.getContext('2d')
        g.setTransform(dpr, 0, 0, dpr, 0, 0)
        g.clearRect(0, 0, w, h)

        const px = signals.DV_POSE_X?.value ?? 0, py = signals.DV_POSE_Y?.value ?? 0
        const yaw = signals.DV_POSE_YAW?.value ?? 0
        const last = trail[trail.length - 1]
        if (!last || Math.hypot(last[0] - px, last[1] - py) > 0.2) {
            trail.push([px, py]); if (trail.length > DV_TRAIL_POINTS) trail.shift()
        }

        // enquadra mapa + carro
        let x0 = px, x1 = px, y0 = py, y1 = py
        for (const c of props.map.cones.values()) { x0 = Math.min(x0, c.x); x1 = Math.max(x1, c.x); y0 = Math.min(y0, c.y); y1 = Math.max(y1, c.y) }
        const pad = 24, sx = (w - 2 * pad) / Math.max(10, x1 - x0), sy = (h - 2 * pad) / Math.max(10, y1 - y0)
        const s = Math.min(sx, sy), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
        const P = (x, y) => [w / 2 + (x - cx) * s, h / 2 - (y - cy) * s]

        g.strokeStyle = 'rgba(221,102,63,0.5)'; g.lineWidth = 2; g.beginPath()
        trail.forEach(([x, y], i) => { const [a, b] = P(x, y); i ? g.lineTo(a, b) : g.moveTo(a, b) })
        g.stroke()

        for (const c of props.map.cones.values()) {
            const [a, b] = P(c.x, c.y)
            g.fillStyle = DV_CONE_COLORS[c.color] ?? DV_CONE_COLORS[0]
            g.beginPath(); g.arc(a, b, 4, 0, 7); g.fill()
        }
        g.strokeStyle = '#f4f5f7'; g.lineWidth = 1.5
        for (const c of props.perc.cones.values()) {
            const [a, b] = P(c.x, c.y)
            g.beginPath(); g.arc(a, b, 8, 0, 7); g.stroke()
        }

        const [a, b] = P(px, py)
        g.save(); g.translate(a, b); g.rotate(-yaw)
        g.fillStyle = '#dd663f'; g.beginPath(); g.moveTo(14, 0); g.lineTo(-9, -8); g.lineTo(-9, 8); g.closePath(); g.fill()
        g.restore()
    }
    const schedule = () => { if (!raf) raf = requestAnimationFrame(draw) }

    createEffect(() => { props.map.version(); props.perc.version(); signals.DV_POSE_X?.value; signals.DV_POSE_Y?.value; signals.DV_POSE_YAW?.value; schedule() })
    onMount(() => { window.addEventListener('resize', schedule); schedule() })
    onCleanup(() => { window.removeEventListener('resize', schedule); if (raf) cancelAnimationFrame(raf) })

    return <canvas ref={canvas} class="dv-canvas" />
}

export default DVMapCanvas
