"""Fonte única da verdade das mensagens CAN da telemetria DV.
Usada pelo codificador (Jetson) e pelo gerador do DV.dbc (servidor): nunca divergem.
Todas Intel (@1), 8 bytes, no mesmo formato dos DBCs da V2.0.
Sinal: (nome, bit_inicial, bits, signed, fator, offset, min, max, unidade)
"""
SLOTS = 16  # slots de cones por classe (1 cone por frame, 1 CAN ID por slot)
ID_POSE, ID_STATUS, ID_MISSION, ID_CONTROL, ID_STEER = 0x600, 0x601, 0x602, 0x603, 0x650
ID_MAP_BASE, ID_PERC_BASE = 0x620, 0x630  # 0x620..0x62F e 0x630..0x63F

# TODO: ID_STEER é provisório. Trocar pelo ID real que o Controle_DV_2026 envia por CAN
# (0x201 já é usado por outro DBC da V2.0). Depois rode: python3 tools/gen_dv_dbc.py
MESSAGES = {
    ID_POSE: ("DV_POSE", [
        ("DV_POSE_X",    0, 16, True,  0.01,  0, -327.68, 327.67, "m"),
        ("DV_POSE_Y",   16, 16, True,  0.01,  0, -327.68, 327.67, "m"),
        ("DV_POSE_YAW", 32, 16, True,  0.001, 0, -32.768, 32.767, "rad"),
        ("DV_SPEED",    48, 16, False, 0.01,  0, 0, 655.35, "m/s"),
    ]),
    ID_STATUS: ("DV_STATUS", [
        ("DV_MAP_CONES_N",   0, 16, False, 1,   0, 0, 65535, ""),
        ("DV_PERC_CONES_N", 16, 16, False, 1,   0, 0, 65535, ""),
        ("DV_MAP_LAT_MS",   32, 16, False, 0.1, 0, 0, 6553.5, "ms"),
        ("DV_PERC_LAT_MS",  48, 16, False, 0.1, 0, 0, 6553.5, "ms"),
    ]),
    ID_MISSION: ("DV_MISSION", [
        ("DV_LAP",        0, 8, False, 1, 0, 0, 255, ""),
        ("DV_AS_STATE",   8, 8, False, 1, 0, 0, 255, ""),
        ("DV_MISSION",   16, 8, False, 1, 0, 0, 255, ""),
        ("DV_MAP_LOCKED", 24, 8, False, 1, 0, 0, 1, ""),
    ]),
    ID_CONTROL: ("DV_CONTROL", [
        ("DV_STEER_CMD",    0, 16, True,  0.01, 0, -327.68, 327.67, "deg"),
        ("DV_SPEED_TARGET", 16, 16, False, 0.01, 0, 0, 655.35, "m/s"),
    ]),
    ID_STEER: ("DV_STEER_MOTOR", [
        ("STEER_ANGLE",    0, 16, True, 0.1, 0, -3276.8, 3276.7, "deg"),
        ("STEER_RPM",     16, 16, True, 1,   0, -32768, 32767, "rpm"),
        ("STEER_CURRENT", 32, 16, True, 0.1, 0, -3276.8, 3276.7, "A"),
        ("STEER_TEMP",    48, 8,  True, 1,   0, -128, 127, "C"),
    ]),
}

for _k in range(SLOTS):
    for _kind, _base in (("MAP", ID_MAP_BASE), ("PERC", ID_PERC_BASE)):
        _p = f"DV_{_kind}_{_k:02d}"
        MESSAGES[_base + _k] = (f"DV_{_kind}_CONE_{_k:02d}", [
            (f"{_p}_IDX",    0, 16, False, 1,    0, 0, 65535, ""),
            (f"{_p}_X",     16, 16, True,  0.01, 0, -327.68, 327.67, "m"),
            (f"{_p}_Y",     32, 16, True,  0.01, 0, -327.68, 327.67, "m"),
            (f"{_p}_COLOR", 48, 8,  False, 1,    0, 0, 255, ""),  # 0 ?, 1 amarelo, 2 azul, 3 laranja, 4 laranja grande
            (f"{_p}_FLAGS", 56, 8,  False, 1,    0, 0, 255, ""),
        ])


def encode(can_id, values):
    """values: dict nome -> valor físico. Retorna 8 bytes (satura no limite do campo)."""
    raw = 0
    for n, sb, ln, signed, f, o, *_ in MESSAGES[can_id][1]:
        r = int(round((values.get(n, 0) - o) / f))
        mn, mx = (-(1 << (ln - 1)), (1 << (ln - 1)) - 1) if signed else (0, (1 << ln) - 1)
        r = max(mn, min(mx, r))
        raw |= (r & ((1 << ln) - 1)) << sb
    return raw.to_bytes(8, "little")


def decode(can_id, data):
    raw = int.from_bytes(bytes(data[:8]).ljust(8, b"\0"), "little")
    out = {}
    for n, sb, ln, signed, f, o, *_ in MESSAGES[can_id][1]:
        r = (raw >> sb) & ((1 << ln) - 1)
        if signed and r & (1 << (ln - 1)):
            r -= 1 << ln
        out[n] = r * f + o
    return out
