from dataclasses import dataclass, field
import random


@dataclass
class Node:
    symbol: str
    children: list["Node"] = field(default_factory=list)
    pattern: str | None = None


GRAMMAR = {
    "S": [
        (["B"] * 8, 0.75),
        (["B"] * 16, 0.25),
    ],
    "B": [
        (["D2", "D2"], 0.75),
        (["U1", "U2", "U1"], 0.25),
    ],
    "D2": [
        (["U1", "U1"], 0.75),
        (["U2"], 0.25),
    ],
}


def expand(symbol):
    if symbol not in GRAMMAR:
        return Node(symbol=symbol)

    productions = GRAMMAR[symbol]
    alternatives, weights = zip(*productions)

    selected = random.choices(
        alternatives,
        weights=weights,
        k=1,
    )[0]

    return Node(
        symbol=symbol,
        children=[expand(child) for child in selected],
    )


UNIT_DURATIONS = {
    "U1": 1,
    "U2": 2,
}


def linearize_units(node, start=0):
    """
    Retorna unidades abstratas com posição e duração,
    sem expandir os padrões rítmicos.
    """
    if node.symbol in UNIT_DURATIONS:
        duration = UNIT_DURATIONS[node.symbol]

        return [
            {
                "symbol": node.symbol,
                "start": start,
                "duration": duration,
            }
        ]

    units = []
    cursor = start

    for child in node.children:
        child_units = linearize_units(child, cursor)
        units.extend(child_units)
        cursor += sum(unit["duration"] for unit in child_units)

    return units


RHYTHMIC_PATTERNS = {
    "U1": {
        # "default": [(0, 1, "note")],
        "staccato": [(0, 1 / 2, "note"), (1 / 2, 1, "rest")],
        "inverted_staccato": [(0, 1 / 2, "rest"), (1 / 2, 1, "note")],
        "rest": [(0, 1, "rest")],
        "triplet": [
            (0, 1 / 3, "note"),
            (1 / 3, 1 / 3, "note"),
            (2 / 3, 1 / 3, "note"),
        ],
        "dotted_eighth_sixteenth": [
            (0, 3 / 4, "note"),
            (3 / 4, 1 / 4, "note"),
        ],
    },
    "U2": {
        "default": [(0, 2, "note")],
        "staccato": [
            (0, 1 / 2, "note"),
            (1 / 2, 2, "rest"),
        ],
        "inverted_staccato": [
            (0, 3 / 2, "rest"),
            (3 / 2, 2, "note"),
        ],
    },
}


def generate_rhythm_events(tree):
    """
    Converte as folhas U1/U2 em eventos rítmicos.

    Cada evento contém:
      start: início absoluto, em tempos de semínima
      duration: duração, em tempos de semínima
    """
    units = linearize_units(tree)
    events = []

    for unit in units:
        symbol = unit["symbol"]
        patterns = RHYTHMIC_PATTERNS[symbol]

        # Escolhe um padrão disponível para esta unidade.
        pattern_name = random.choice(list(patterns.keys()))
        pattern = patterns[pattern_name]

        for offset, duration, kind in pattern:
            if kind == "rest":
                continue

            events.append(
                {
                    "start": unit["start"] + offset,
                    "duration": duration,
                }
            )

    return events
