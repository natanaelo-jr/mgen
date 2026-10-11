import math
import random

import pretty_midi

from mgen.harmony import (
    ChordState,
    HarmonicContext,
    absolute_root,
)

ENDING_BEATS = 4.0  # duração do acorde final (uma barra em 4/4)


def add_melody_to_midi(
    midi: pretty_midi.PrettyMIDI,
    melody_events,
    bpm: int = 110,
    velocity: int = 90,
    instrument_name: str = "Lead 1 (square)",
):
    """Adiciona a melodia como uma nova pista MIDI."""
    if bpm <= 0:
        raise ValueError("bpm precisa ser positivo")

    melody_instrument = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program(instrument_name)
    )

    seconds_per_beat = 60.0 / bpm

    for event in melody_events:
        start_seconds = event["start"] * seconds_per_beat
        end_seconds = (event["start"] + event["duration"]) * seconds_per_beat

        if end_seconds <= start_seconds:
            continue

        melody_instrument.notes.append(
            pretty_midi.Note(
                velocity=velocity,
                pitch=event["pitch"],
                start=start_seconds,
                end=end_seconds,
            )
        )

    midi.instruments.append(melody_instrument)


CHORD_INTERVALS = {
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "7": (0, 4, 7, 10),
    "m7b5": (0, 3, 6, 10),
}

# Peso de cada grau do acorde (semitons a partir da fundamental).
# Terça e sétima definem a qualidade; fundamental e quinta são neutras.
CHORD_TONE_ROLE = {
    "maj7": {0: 1.0, 4: 2.0, 7: 0.7, 11: 1.8},
    "m7": {0: 1.0, 3: 2.0, 7: 0.7, 10: 1.8},
    "7": {0: 0.8, 4: 2.2, 7: 0.6, 10: 2.2},
    "m7b5": {0: 0.8, 3: 2.0, 6: 1.2, 10: 2.0},
}

PENTATONIC_INTERVALS = {
    "maj7": (0, 2, 4, 7, 9),
    "m7": (0, 3, 5, 7, 10),
    "7": (0, 2, 4, 7, 10),
    "m7b5": (0, 3, 5, 6, 10),
}

INTERVAL_WEIGHTS = {
    0: 0.6,  # Repetição
    1: 0.8,  # Semitom
    2: 5.0,  # Segunda maior
    3: 3.5,  # Terça menor
    4: 2.5,  # Terça maior
    5: 1.5,  # Quarta justa
    6: 0.5,  # Trítono
    7: 1.0,  # Quinta justa
    8: 0.35,
    9: 0.3,
    10: 0.15,
    11: 0.1,
    12: 0.08,
}

CHROMATIC_WEIGHT = 0.25

SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
}


def chord_pitch_classes(chord, context):
    """Classes de altura pertencentes ao acorde."""
    root = absolute_root(chord, context)

    return {(root + interval) % 12 for interval in CHORD_INTERVALS[chord.quality]}


def chord_pentatonic_pitch_classes(chord, context):
    """Retorna as cinco classes de altura da coleção do acorde."""
    root = absolute_root(chord, context)

    intervals = PENTATONIC_INTERVALS.get(chord.quality)

    if intervals is None:
        raise ValueError(f"Qualidade sem coleção pentatônica: {chord.quality}")

    return {(root + interval) % 12 for interval in intervals}


def scale_pitch_classes(context):
    """Classes de altura da escala da tonalidade."""
    intervals = SCALES[context.mode]

    return {(context.tonic + interval) % 12 for interval in intervals}


def pitch_candidates(
    chord,
    context,
    low=60,
    high=84,
):
    """Classifica alturas MIDI como notas do acorde, pentatônicas ou cromáticas."""
    pentatonic = chord_pentatonic_pitch_classes(chord, context)
    chord_tones = chord_pitch_classes(chord, context)

    candidates = []

    for pitch in range(low, high + 1):
        pc = pitch % 12

        if pc in chord_tones:
            category = "chord"
        elif pc in pentatonic:
            category = "pentatonic"
        else:
            # Só permite cromatismos vizinhos à coleção.
            distances = [min((pc - note) % 12, (note - pc) % 12) for note in pentatonic]

            if min(distances) == 1:
                category = "chromatic"
            else:
                continue

        candidates.append((pitch, category))

    return candidates


def melodic_weight(
    pitch,
    category,
    previous_pitch,
    strong_beat,
    chord,
    context,
    duration=0.5,
    previous_category=None,
    previous_chord=None,
    next_chord=None,
    approach_to=None,
    center=72,
    spread=7.0,
):
    """Peso de uma nota condicionado à harmonia, à nota anterior e ao contexto."""
    # 1. Base por categoria; entre as notas do acorde, terça e sétima valem mais.
    if category == "chord":
        weight = 4.0 if strong_beat else 2.0
        role = CHORD_TONE_ROLE[chord.quality].get(
            (pitch - absolute_root(chord, context)) % 12, 1.0
        )
        weight *= role if strong_beat else role**0.5
    elif category == "pentatonic":
        weight = 2.0 if strong_beat else 2.5
    else:
        weight = CHROMATIC_WEIGHT

    # 2. Notas longas pedem consonância (uma colcheia não é afetada).
    if category != "chord":
        weight /= max(1.0, duration * 2)

    # 3. Região confortável: evita o passeio aleatório pelo registro todo.
    weight *= math.exp(-0.5 * ((pitch - center) / spread) ** 2)

    if previous_pitch is not None:
        interval = abs(pitch - previous_pitch)
        weight *= INTERVAL_WEIGHTS.get(interval, 0.05)

        # 4. Nota estranha ao acorde resolve em nota do acorde, por grau conjunto.
        if previous_category in ("pentatonic", "chromatic"):
            if category == "chord" and 1 <= interval <= 2:
                weight *= 4.0
            elif category != "chord":
                weight *= 0.3

        # 5. Condução de vozes: sétima do acorde anterior desce para a terça do atual.
        if previous_chord is not None and previous_chord.name != chord.name:
            prev_seventh = (
                absolute_root(previous_chord, context)
                + CHORD_INTERVALS[previous_chord.quality][3]
            ) % 12
            third = (
                absolute_root(chord, context) + CHORD_INTERVALS[chord.quality][1]
            ) % 12

            if (
                previous_pitch % 12 == prev_seventh
                and pitch % 12 == third
                and 1 <= previous_pitch - pitch <= 2
            ):
                weight *= 3.0

    # 6. Último evento antes da troca: antecipa ou aproxima o próximo acorde.
    if next_chord is not None:
        upcoming = chord_pitch_classes(next_chord, context)

        if pitch % 12 in upcoming:
            weight *= 1.8
        elif (pitch + 1) % 12 in upcoming or (pitch - 1) % 12 in upcoming:
            weight *= 1.5

    # 7. Última nota antes do acorde final: 2º grau ou sensível, que resolvem
    #    na tônica por grau conjunto. approach_to é a classe de altura da tônica.
    if approach_to is not None:
        degree = (pitch - approach_to) % 12
        weight *= 8.0 if degree in (2, 11) else 0.25

    return weight


def choose_melody_pitch(
    chord,
    context,
    previous_pitch=None,
    strong_beat=True,
    low=60,
    high=84,
    rng=random,
    **kwargs,
):
    """Escolhe uma nota por probabilidades condicionadas à harmonia e à nota anterior.

    Retorna (pitch, category). Os kwargs extras (duration, previous_category,
    previous_chord, next_chord, approach_to) são repassados para melodic_weight.
    """
    candidates = pitch_candidates(
        chord=chord,
        context=context,
        low=low,
        high=high,
    )

    if not candidates:
        raise ValueError("Não há notas candidatas no registro escolhido")

    weights = [
        melodic_weight(
            pitch,
            category,
            previous_pitch,
            strong_beat,
            chord,
            context,
            center=(low + high) // 2,
            spread=(high - low) / 3.5,
            **kwargs,
        )
        for pitch, category in candidates
    ]

    return rng.choices(candidates, weights=weights, k=1)[0]


def settle_rhythm(ordered, final_start, settle_beats):
    """Acalma o ritmo antes do acorde final.

    Nos últimos settle_beats tempos, mantém só as notas que caem em início de
    acorde (tempos 1 e 3) e alonga cada uma até a próxima, ou até o acorde final.
    """
    window_start = final_start - settle_beats

    head = [event for event in ordered if event["start"] < window_start]
    window = [event for event in ordered if event["start"] >= window_start]

    kept = [event for event in window if event["start"] % 2 == 0] or window[:1]

    settled = []
    for k, event in enumerate(kept):
        end = kept[k + 1]["start"] if k + 1 < len(kept) else final_start
        settled.append({**event, "duration": end - event["start"]})

    return head + settled


def final_melody_event(
    events,
    progression,
    context,
    low=60,
    high=84,
    rng=random,
):
    """Nota de descanso: a tônica mais próxima da última nota tocada, longa."""
    chord = progression[-1]
    root = absolute_root(chord, context)
    previous_pitch = events[-1]["pitch"] if events else (low + high) // 2

    roots = [pitch for pitch in range(low, high + 1) if pitch % 12 == root]

    if not roots:
        raise ValueError("Não há tônica disponível no registro escolhido")

    # Em empate, prefere a mais grave.
    pitch = min(roots, key=lambda p: (abs(p - previous_pitch), p))

    return {
        "start": (len(progression) - 1) * 2.0,
        "duration": ENDING_BEATS,
        "pitch": pitch,
        "chord": chord.name,
    }


def generate_melody_events(
    rhythm_events,
    progression,
    context,
    low=60,
    high=84,
    rng=random,
    ending=True,
    settle_beats=0.0,
):
    """
    Associa alturas aos eventos rítmicos.
    Cada acorde da progressão ocupa dois tempos.

    Com ending=True, o último acorde da progressão é o acorde final: eventos
    que cairiam nele são descartados, a última nota antes dele é o 2º grau ou
    a sensível, e a melodia termina com a tônica, longa.

    settle_beats > 0 (opcional, só com ending=True) acalma o ritmo nesses
    últimos tempos antes do acorde final; veja settle_rhythm.
    """
    ordered = sorted(rhythm_events, key=lambda event: event["start"])

    final_start = (len(progression) - 1) * 2.0
    if ending:
        ordered = [event for event in ordered if event["start"] < final_start]

        if settle_beats > 0:
            ordered = settle_rhythm(ordered, final_start, settle_beats)

    events = []
    previous_pitch = None
    previous_category = None
    previous_chord = None

    for i, rhythm_event in enumerate(ordered):
        start = rhythm_event["start"]

        chord_index = int(start // 2)

        if chord_index >= len(progression):
            continue

        chord = progression[chord_index]

        # Nenhuma nota invade o acorde final.
        duration = rhythm_event["duration"]
        if ending:
            duration = min(duration, final_start - start)

        # Se o próximo evento cai em outro acorde (ou, no fim, o acorde final),
        # este é o momento de preparar a troca.
        if i + 1 < len(ordered):
            next_index = int(ordered[i + 1]["start"] // 2)
        elif ending:
            next_index = len(progression) - 1
        else:
            next_index = chord_index

        next_chord = None
        if next_index != chord_index and next_index < len(progression):
            next_chord = progression[next_index]

        # Última nota antes do acorde final: aproxima a tônica por grau conjunto.
        is_last = ending and i + 1 >= len(ordered)
        approach_to = absolute_root(progression[-1], context) if is_last else None

        # Em 4/4, os tempos 1 e 3 são considerados fortes.
        beat_in_bar = start % 4
        strong_beat = abs(beat_in_bar) < 1e-6 or abs(beat_in_bar - 2) < 1e-6

        pitch, category = choose_melody_pitch(
            chord=chord,
            context=context,
            previous_pitch=previous_pitch,
            strong_beat=strong_beat,
            low=low,
            high=high,
            rng=rng,
            duration=duration,
            previous_category=previous_category,
            previous_chord=previous_chord,
            next_chord=next_chord,
            approach_to=approach_to,
        )

        events.append(
            {
                "start": start,
                "duration": duration,
                "pitch": pitch,
                "chord": chord.name,
            }
        )

        previous_pitch = pitch
        previous_category = category
        previous_chord = chord

    if ending:
        events.append(
            final_melody_event(
                events,
                progression,
                context,
                low=low,
                high=high,
                rng=rng,
            )
        )

    return events
