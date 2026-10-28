import json


def load(path):
    """Retorna (meta, registros) de uma sessão .jsonl gravada pelo dv-edge."""
    meta, recs = {}, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "meta" in d:
                meta = d["meta"]
            else:
                recs.append(d)
    return meta, recs
