"""
Solucionador del rompecabezas de barras de madera con clavijas.

Piezas:
  * 10 barras de madera con agujeros pasantes.
  * 12 clavijas de metal sueltas, que se meten AL FINAL.
  * Un marco en forma de rombo donde caben 5 barras abajo (filas) y 5 encima,
    cruzadas (columnas).

Cada cruce fila/columna es una casilla de una cuadrícula de 5x5. Una clavija
entra en la casilla (fila r, columna c) solo si la barra de abajo en la fila r
y la barra de arriba en la columna c tienen agujero justo ahí. Como hay 12
clavijas y 24 agujeros, en una solución TODOS los agujeros quedan alineados.

Cualquier barra puede ir abajo o arriba (para pasar de una capa a otra se
voltea) y en dos sentidos (normal o girada 180°). El programa prueba todos los
acomodos, imprime las soluciones con una estrategia paso a paso y genera
`rompecabezas.html` para jugar en 3D.

Si alguna posición de agujero no coincide con tus piezas, corrígela abajo y
vuelve a ejecutar:  python solver.py
"""

import json
import re
import sys
from itertools import combinations, permutations, product
from pathlib import Path

# Agujeros en las posiciones 1..5, contadas desde el extremo marcado de cada barra.
BARS = [
    {"id": "A", "name": "Roble claro",   "color": "#c99a5c", "pos": [1, 3, 4, 5]},
    {"id": "B", "name": "Wengué oscuro", "color": "#3b2a20", "pos": [4]},
    {"id": "C", "name": "Nogal",         "color": "#6e3f2a", "pos": [1, 4, 5]},
    {"id": "D", "name": "Cedro rojo",    "color": "#8f4a30", "pos": [3, 5]},
    {"id": "E", "name": "Iroko veteado", "color": "#7a5236", "pos": [1, 2]},
    {"id": "F", "name": "Palo de rosa",  "color": "#5a3324", "pos": [1, 3, 5]},
    {"id": "G", "name": "Roble rojo",    "color": "#a0602f", "pos": [5]},
    {"id": "H", "name": "Wengué rayado", "color": "#3e3127", "pos": [1, 4]},
    {"id": "I", "name": "Padouk oscuro", "color": "#6a3228", "pos": [1, 2, 3]},
    {"id": "J", "name": "Fresno",        "color": "#cfa46c", "pos": [1, 3, 4]},
]
N = 5
PEGS = 12
BAR = {b["id"]: b for b in BARS}


def orient(bid, flip):
    """Agujeros (0..4) de una barra en sentido normal o girada 180°."""
    base = [p - 1 for p in BAR[bid]["pos"]]
    return frozenset(N - 1 - p if flip else p for p in base)


def is_symmetric(bid):
    return orient(bid, 0) == orient(bid, 1)


def flips(bid):
    # Una barra simétrica girada es idéntica: solo se cuenta una vez.
    return (0,) if is_symmetric(bid) else (0, 1)


def n_holes(bid):
    return len(BAR[bid]["pos"])


def solve():
    solutions = []
    ids = [b["id"] for b in BARS]
    for bottom in combinations(ids, N):
        # Abajo y arriba deben tener 12 agujeros cada capa (uno por clavija).
        if sum(n_holes(i) for i in bottom) != PEGS:
            continue
        top = [i for i in ids if i not in bottom]
        for order in permutations(bottom):
            for fl in product(*(flips(i) for i in order)):
                rows = list(zip(order, fl))
                need = [set() for _ in range(N)]  # filas con agujero, por columna
                for r, (bid, f) in enumerate(rows):
                    for c in orient(bid, f):
                        need[c].add(r)

                def place(c, used, acc):
                    if c == N:
                        solutions.append({"rows": rows, "cols": list(acc)})
                        return
                    for bid in top:
                        if bid in used:
                            continue
                        for f in flips(bid):
                            if orient(bid, f) == need[c]:
                                place(c + 1, used | {bid}, acc + [(bid, f)])

                place(0, frozenset(), [])
    return solutions


# ---------- Simetrías del rombo ----------
def _norm(bid, f):
    return 0 if is_symmetric(bid) else f


def rotate180(sol):
    """Girar todo el rompecabezas 180° sobre la mesa."""
    rot = lambda lst: [(b, _norm(b, 1 - f)) for b, f in reversed(lst)]
    return {"rows": rot(sol["rows"]), "cols": rot(sol["cols"])}


def turn_over(sol):
    """Voltear todo el rompecabezas: la capa de arriba pasa abajo y las columnas se vuelven filas."""
    return {"rows": list(sol["cols"]), "cols": list(sol["rows"])}


def key(sol):
    return json.dumps({"rows": [list(x) for x in sol["rows"]], "cols": [list(x) for x in sol["cols"]]})


def variants(sol):
    """Las 4 versiones equivalentes: tal cual, girada, volteada, volteada y girada."""
    return [sol, rotate180(sol), turn_over(sol), rotate180(turn_over(sol))]


def hole_cells(sol):
    return {(r, c) for r, (bid, f) in enumerate(sol["rows"]) for c in orient(bid, f)}


# ---------- Texto ----------
def lst(xs):
    xs = [str(x) for x in xs]
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def where(word, xs):
    return f"la {word} {xs[0]}" if len(xs) == 1 else f"las {word}s {lst(xs)}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def sense(f):
    return ", girada" if f else ""


def strategy(sol, bottom_sets):
    rows, cols = sol["rows"], sol["cols"]
    cells = hole_cells(sol)
    bottom = sorted(b for b, _ in rows)
    top = sorted(b for b, _ in cols)
    steps = []

    steps.append({
        "type": "plan", "id": None, "slot": None, "flip": 0,
        "title": f"Abajo {' '.join(bottom)} · arriba {' '.join(top)}",
        "text": "Cada capa suma 12 agujeros.",
    })

    # Capa de abajo: de la barra con más agujeros a la de menos.
    order = sorted(range(N), key=lambda r: (-n_holes(rows[r][0]), r))
    for r in order:
        bid, f = rows[r]
        at = sorted(c + 1 for c in orient(bid, f))
        steps.append({"type": "row", "id": bid, "slot": r, "flip": f,
                      "title": f"{bid} → fila {r + 1}{sense(f)}",
                      "text": f"Agujeros en {where('columna', at)}."})

    # Capa de arriba: primero la columna con menos opciones.
    remaining, done = set(top), set()
    while len(done) < N:
        best = None
        for c in range(N):
            if c in done:
                continue
            req = frozenset(r for r in range(N) if (r, c) in cells)
            cands = [(b, f) for b in sorted(remaining) for f in flips(b) if orient(b, f) == req]
            k2 = (len(cands), -len(req), c)
            if best is None or k2 < best[0]:
                best = (k2, c, req, cands)
        _, c, req, cands = best
        bid, f = cols[c]
        text = f"La columna pide agujeros en {where('fila', sorted(r + 1 for r in req))}"
        text += ": solo encaja esta." if len(cands) == 1 else "."
        steps.append({"type": "col", "id": bid, "slot": c, "flip": f,
                      "title": f"{bid} → columna {c + 1}{sense(f)}", "text": text})
        remaining.discard(bid)
        done.add(c)

    steps.append({"type": "pegs", "id": None, "slot": None, "flip": 0,
                  "title": "Mete las 12 clavijas", "text": ""})
    return steps


def intro(n_solutions, n_families, bottom_sets):
    b = [b["id"] for b in BARS]
    total = sum(n_holes(i) for i in b)
    return [
        f"Hay {total} agujeros y {PEGS} clavijas. Cada clavija atraviesa dos barras (una de abajo y una de arriba), "
        f"así que en la solución todos los agujeros quedan alineados: 12 abajo y 12 arriba.",
        "Agujeros por barra: " + ", ".join(f"{i}={n_holes(i)}" for i in b) + ".",
        f"Primer filtro: elige 5 barras que sumen 12 agujeros para la capa de abajo. Hay {len(bottom_sets)} grupos así, "
        "pero no todos funcionan.",
        "Regla clave: los agujeros de la barra de arriba en una columna deben coincidir EXACTAMENTE con las filas "
        "donde la capa de abajo tiene agujero en esa columna.",
        "Las clavijas van al final: ponerlas antes te dice qué barra va abajo, y eso es justo lo difícil.",
        f"Simetrías: girar todo 180° o voltear el rompecabezas completo (lo de arriba pasa abajo) da otra solución. "
        f"Por eso las {n_solutions} soluciones se agrupan en {n_families} familias de 4.",
    ]


def ascii_grid(sol):
    cells = hole_cells(sol)
    lines = ["        " + "  ".join(f"{b}{'↑' if f else '↓'}" for b, f in sol["cols"])]
    for r, (bid, f) in enumerate(sol["rows"]):
        marks = "   ".join("●" if (r, c) in cells else "·" for c in range(N))
        lines.append(f"  {bid}{'←' if f else '→'}    {marks}")
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # flechas y acentos en la consola de Windows
    sols = solve()
    index = {key(s): i for i, s in enumerate(sols)}

    # Agrupar en familias de 4 (giro / volteo)
    families, seen = [], set()
    for i, s in enumerate(sols):
        if i in seen:
            continue
        members = []
        for v in variants(s):
            j = index[key(v)]
            if j not in members:
                members.append(j)
        seen.update(members)
        families.append(members)

    bottom_sets = sorted({tuple(sorted(b for b, _ in s["rows"])) for s in sols})
    candidate_sets = [c for c in combinations([b["id"] for b in BARS], N) if sum(n_holes(i) for i in c) == PEGS]

    data_sols = []
    for i, s in enumerate(sols):
        fam = next(k for k, m in enumerate(families) if i in m)
        data_sols.append({
            "rows": [{"id": a, "flip": b} for a, b in s["rows"]],
            "cols": [{"id": a, "flip": b} for a, b in s["cols"]],
            "family": fam,
            "steps": strategy(s, candidate_sets),
        })

    print(f"Soluciones encontradas: {len(sols)}")
    print(f"Familias (iguales salvo girar 180° o voltear todo): {len(families)}")
    print(f"Grupos de 5 barras con 12 agujeros: {len(candidate_sets)}; de ellos funcionan como capa de abajo: {len(bottom_sets)}\n")
    print("Leyenda: → / ↓ sentido normal, ← / ↑ girada 180°, ● agujeros alineados (lleva clavija)\n")
    for line in intro(len(sols), len(families), candidate_sets):
        print(" •", line)
    for k, members in enumerate(families):
        i = members[0]
        print(f"\n=== Familia {k + 1} · solución {i + 1} (variantes: {', '.join(str(m + 1) for m in members)}) ===")
        print(ascii_grid(sols[i]))
        print("Estrategia:")
        for n, st in enumerate(data_sols[i]["steps"], 1):
            print(f"  {n:2}. {st['title']}: {st['text']}")

    data = {
        "bars": [dict(b, pos=sorted(orient(b["id"], 0)), sym=is_symmetric(b["id"])) for b in BARS],
        "pegs": PEGS,
        "solutions": data_sols,
        "families": families,
        "intro": intro(len(sols), len(families), candidate_sets),
    }
    here = Path(__file__).parent
    template = (here / "plantilla.html").read_text(encoding="utf-8")
    html = template.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    out = here / "rompecabezas.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nHTML generado: {out}")

    # Versión para publicar en la web: sin <html>/<head>/<body>, que el hosting agrega solo.
    web = re.sub(r"<!doctype html>\s*|</?html[^>]*>\s*|</?head>\s*|</?body>\s*|<meta (charset|name=\"viewport\")[^>]*>\s*",
                 "", html, flags=re.I)
    (here / "rompecabezas_web.html").write_text(web, encoding="utf-8")


if __name__ == "__main__":
    main()
