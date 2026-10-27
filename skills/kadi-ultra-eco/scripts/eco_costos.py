"""Estimador de costos KADI Ultra-Eco vs. ultracode (herencia del modelo de sesión).

Solo librería estándar. Salida JSON. Los precios vienen de la tabla del skill
claude-api (caché 2026-10-06); los multiplicadores de esfuerzo y los tokens
medios por agente son SUPUESTOS calibrables con datos reales (budget.spent()).

Ejemplo:
    python eco_costos.py --t1 30 --t2 8 --t3 2 --base opus --base-effort xhigh
"""

from __future__ import annotations

import argparse
import json
import math
import sys

# $ por millón de tokens: entrada, salida, lectura de caché.
PRECIOS: dict[str, dict[str, float]] = {
    "haiku": {"in": 0.10, "out": 0.50, "cache": 0.01},  # caché: SUPUESTO (10 % de la entrada)
    "sonnet": {"in": 2.00, "out": 10.00, "cache": 0.20},
    "opus": {"in": 4.00, "out": 20.00, "cache": 0.20},
    "fable": {"in": 10.00, "out": 50.00, "cache": 0.25},
}

# Tiers inmutables del skill.
TIERS: dict[str, tuple[str, str]] = {
    "T1": ("sonnet", "xhigh"),
    "T2": ("opus", "high"),
    "T3": ("fable", "high"),
}

ESFUERZOS: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")


def entero_no_negativo(s: str) -> int:
    """Tipo argparse: entero >= 0."""
    v = int(s)
    if v < 0:
        raise argparse.ArgumentTypeError("debe ser un entero >= 0")
    return v


def real_no_negativo(s: str) -> float:
    """Tipo argparse: número finito >= 0."""
    v = float(s)
    if not math.isfinite(v) or v < 0:
        raise argparse.ArgumentTypeError("debe ser un número finito >= 0")
    return v


def costo_agente(modelo: str, esfuerzo: str, a: argparse.Namespace) -> float:
    """Costo en $ de un agente medio con el modelo y esfuerzo dados."""
    p = PRECIOS[modelo]
    mult = getattr(a, f"mult_{esfuerzo}")
    entrada = a.in_tok * ((1.0 - a.cache_hit) * p["in"] + a.cache_hit * p["cache"])
    salida = a.out_tok * mult * p["out"]
    return (entrada + salida) / 1_000_000


def main() -> int:
    # La consola de Windows usa cp1252 por defecto; forzamos UTF-8 para los acentos del JSON.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--t1", type=entero_no_negativo, default=0, help="agentes T1 (sonnet/xhigh)")
    ap.add_argument("--t2", type=entero_no_negativo, default=0, help="agentes T2 (opus/high)")
    ap.add_argument("--t3", type=entero_no_negativo, default=0, help="agentes T3 (fable/high)")
    ap.add_argument("--base", choices=sorted(PRECIOS), default="opus", help="modelo de sesión que heredaría ultracode")
    ap.add_argument("--base-effort", choices=ESFUERZOS, default="xhigh", help="esfuerzo de sesión que heredaría ultracode")
    ap.add_argument("--in-tok", type=real_no_negativo, default=80_000, help="SUPUESTO: tokens de entrada medios por agente")
    ap.add_argument("--out-tok", type=real_no_negativo, default=8_000, help="SUPUESTO: tokens de salida medios por agente en esfuerzo high")
    ap.add_argument("--cache-hit", type=float, default=0.8, help="SUPUESTO: fracción de la entrada leída de caché (0-1)")
    # SUPUESTOS: tokens de salida relativos a 'high'. Calibrar con budget.spent() por tier.
    for nombre, valor in zip(ESFUERZOS, (0.45, 0.7, 1.0, 1.4, 1.9)):
        ap.add_argument(f"--mult-{nombre}", type=real_no_negativo, default=valor, help=f"SUPUESTO: multiplicador de salida para {nombre}")
    a = ap.parse_args()

    if not 0.0 <= a.cache_hit <= 1.0:
        print(json.dumps({"error": "--cache-hit debe estar entre 0 y 1"}, ensure_ascii=False))
        return 1
    conteos = {"T1": a.t1, "T2": a.t2, "T3": a.t3}
    total = sum(conteos.values())
    if total <= 0:
        print(json.dumps({"error": "indica al menos un agente con --t1/--t2/--t3"}, ensure_ascii=False))
        return 1

    por_tier = {}
    eco = 0.0
    for tier, n in conteos.items():
        modelo, esfuerzo = TIERS[tier]
        unitario = costo_agente(modelo, esfuerzo, a)
        por_tier[tier] = {"modelo": modelo, "esfuerzo": esfuerzo, "agentes": n, "usd": round(n * unitario, 4)}
        eco += n * unitario

    base = total * costo_agente(a.base, a.base_effort, a)
    ahorro = (1.0 - eco / base) * 100 if base > 0 else 0.0
    mezcla = {t: round(100 * n / total, 1) for t, n in conteos.items()}
    avisos = []
    if mezcla["T1"] < 70:
        avisos.append("T1 por debajo del 70 % objetivo")
    if mezcla["T3"] > 5:
        avisos.append("T3 por encima del 5 % objetivo")

    print(json.dumps({
        "agentes": total,
        "mezcla_pct": mezcla,
        "ultra_eco_usd": round(eco, 4),
        "ultracode_usd": round(base, 4),
        "ultracode_hereda": f"{a.base}/{a.base_effort}",
        "ahorro_pct": round(ahorro, 1),
        "por_tier": por_tier,
        "avisos": avisos,
        "supuestos": {
            "in_tok": a.in_tok, "out_tok": a.out_tok, "cache_hit": a.cache_hit,
            "multiplicadores": {e: getattr(a, f"mult_{e}") for e in ESFUERZOS},
            "nota": "estimación; calibra in/out/multiplicadores con tokens reales de tus workflows",
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
