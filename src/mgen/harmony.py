from dataclasses import dataclass
import numpy as np
import random


@dataclass(frozen=True)
class ChordState:
    name: str
    root: int  # Semitons relativos à tônica
    quality: str
    function: str
    borrowed: bool = False


@dataclass(frozen=True)
class HarmonicContext:
    tonic: int  # 0 = C, 1 = C#/Db, ..., 11 = B
    mode: str = "major"


# Vocabulário inicial em relação à tônica.
CHORDS = {
    "Imaj7": ChordState("Imaj7", 0, "maj7", "tonic"),
    "IIm7": ChordState("IIm7", 2, "m7", "predominant"),
    "IIIm7": ChordState("IIIm7", 4, "m7", "tonic"),
    "IVmaj7": ChordState("IVmaj7", 5, "maj7", "predominant"),
    "V7": ChordState("V7", 7, "7", "dominant"),
    "VIm7": ChordState("VIm7", 9, "m7", "tonic"),
    "VIIm7b5": ChordState("VIIm7b5", 11, "m7b5", "dominant"),
    # Empréstimos do modo menor paralelo:
    "ivm7": ChordState("ivm7", 5, "m7", "predominant", True),
    "bVImaj7": ChordState("bVImaj7", 8, "maj7", "predominant", True),
    "bVII7": ChordState("bVII7", 10, "7", "dominant", True),
}


def absolute_root(chord: ChordState, context: HarmonicContext) -> int:
    return (context.tonic + chord.root) % 12


TRANSITIONS = {
    "Imaj7": {
        "Imaj7": 1.0,
        "IIm7": 3.0,
        "IIIm7": 1.5,
        "IVmaj7": 3.0,
        "V7": 1.0,
        "VIm7": 2.5,
        "ivm7": 0.6,
        "bVImaj7": 0.5,
        "bVII7": 0.5,
    },
    "IIm7": {
        "IIm7": 0.6,
        "V7": 6.0,
        "VIIm7b5": 0.3,
        "IVmaj7": 0.5,
        "Imaj7": 0.5,
        "ivm7": 0.4,
    },
    "IIIm7": {
        "IIIm7": 0.5,
        "VIm7": 3.5,
        "IVmaj7": 3.0,
        "IIm7": 1.5,
        "V7": 0.6,
        "bVImaj7": 0.4,
    },
    "IVmaj7": {
        "IVmaj7": 0.8,
        "V7": 3.0,
        "Imaj7": 2.0,
        "IIIm7": 1.5,
        "IIm7": 1.2,
        "ivm7": 1.2,
        "VIm7": 1.0,
        "bVII7": 0.8,
        "VIIm7b5": 0.4,
    },
    "V7": {
        "V7": 0.5,
        "Imaj7": 6.0,
        "VIm7": 1.2,  # cadência de engano
        "IVmaj7": 0.4,
        "IIIm7": 0.4,
        "bVImaj7": 0.3,  # engano modal
    },
    "VIm7": {
        "VIm7": 0.8,
        "IIm7": 3.5,
        "IVmaj7": 2.5,
        "V7": 1.0,
        "IIIm7": 0.5,
        "Imaj7": 0.5,
        "bVImaj7": 0.5,
    },
    "VIIm7b5": {
        "IIIm7": 4.0,
        "Imaj7": 1.5,
        "V7": 1.0,
        "IIm7": 0.5,
    },
    "ivm7": {
        "ivm7": 0.5,
        "Imaj7": 3.0,
        "bVII7": 2.0,
        "V7": 1.5,
        "bVImaj7": 1.0,
    },
    "bVImaj7": {
        "bVImaj7": 0.5,
        "bVII7": 3.0,
        "V7": 2.0,
        "ivm7": 1.0,
        "Imaj7": 1.0,
    },
    "bVII7": {
        "bVII7": 0.5,
        "Imaj7": 4.0,
        "IVmaj7": 1.5,
        "V7": 0.8,
    },
}


def choose_next(current_name: str) -> str:
    weights = TRANSITIONS[current_name]
    candidates = list(weights.keys())
    probabilities = list(weights.values())

    return random.choices(
        candidates,
        weights=probabilities,
        k=1,
    )[0]


PREPARATION_WEIGHTS = {
    "Imaj7": {
        "V7": 4.0,
        "IIm7": 2.0,
        "ivm7": 2.0,
        "bVII7": 1.0,
        "VIIm7b5": 1.0,
    }
}

NAMES = list(CHORDS)
IDX = {name: i for i, name in enumerate(NAMES)}


def choose_preparation(current_name, target_name="Imaj7"):
    candidates = PREPARATION_WEIGHTS[target_name]
    current_weights = TRANSITIONS[current_name]

    names = list(candidates.keys())
    weights = [candidates[name] * current_weights.get(name, 0.15) for name in names]

    return random.choices(names, weights=weights, k=1)[0]


def build_matrix(temperature: float = 1.0) -> np.ndarray:
    P = np.zeros((len(NAMES), len(NAMES)))
    for a, row in TRANSITIONS.items():
        for b, w in row.items():
            P[IDX[a], IDX[b]] = w ** (1.0 / temperature)
    return P / P.sum(axis=1, keepdims=True)


def choose_toward(
    current_name: str,
    target_name: str,
    steps_left: int,
    P: np.ndarray,
    cadence_strength: float = 1.0,
) -> str:
    """Sorteia o próximo acorde sabendo que o alvo deve ser atingido em steps_left transições."""
    reach = np.linalg.matrix_power(P, steps_left - 1)[:, IDX[target_name]]
    reach = np.where(reach > 0, reach**cadence_strength, 0.0)

    weights = P[IDX[current_name]] * reach
    if weights.sum() == 0:
        raise ValueError(
            f"{target_name} inalcançável a partir de {current_name} em {steps_left} passos"
        )

    return random.choices(NAMES, weights=weights, k=1)[0]


def generate_progression(
    bars: int = 8,
    tonic: int = 0,
    cycle_bars: int = 4,
    temperature: float = 1.0,
    cadence_strength: float = 1.0,
) -> list[ChordState]:
    if bars < 1:
        raise ValueError("bars precisa ser pelo menos 1")
    if cycle_bars not in (4, 8):
        raise ValueError("cycle_bars deve ser 4 ou 8")

    P = build_matrix(temperature)
    total_steps = bars * 2
    cycle_steps = cycle_bars * 2

    progression = [CHORDS["Imaj7"]]

    for step in range(1, total_steps):
        # Próximo ponto em que a tônica deve soar. No fim da progressão usa-se
        # uma tônica "virtual" em total_steps, para o loop resolver bem.
        boundary = min(-(-step // cycle_steps) * cycle_steps, total_steps)
        steps_left = boundary - step + 1

        name = choose_toward(
            progression[-1].name, "Imaj7", steps_left, P, cadence_strength
        )
        progression.append(CHORDS[name])
    progression.append(CHORDS["Imaj7"])  # Garante a tônica no final
    return progression


ENDING_BEATS = 4.0  # duração do acorde final (uma barra em 4/4)


def with_ending(progression, authentic=False):
    """Acrescenta a tônica final depois da última preparação.

    Com authentic=True, a última preparação vira V7, garantindo V7 -> I.
    """
    body = list(progression)

    if authentic:
        body[-1] = CHORDS["V7"]

    return [*body, CHORDS["Imaj7"]]
