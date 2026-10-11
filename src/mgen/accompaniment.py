import random
from pathlib import Path

import pretty_midi

from mgen.harmony import ChordState, HarmonicContext, absolute_root

# Cada acorde ocupa dois tempos.
CHORD_DURATION = 2.0
ENDING_BEATS = 4.0  # duração do acorde final (uma barra em 4/4)

# (início relativo, fim relativo, tipo)
RHYTHMIC_PATTERNS = {
    "U2": {
        "default": [
            (0, 2 / 3, "rest"),
            (2 / 3, 3 / 2, "note"),
        ],
        "default_staccato": [
            (0, 2 / 3, "rest"),
            (2 / 3, 1, "note"),
        ],
        "two": [
            (0, 3 / 4, "note"),
            (3 / 4, 1, "rest"),
            (1, 7 / 4, "note"),
            (7 / 4, 2, "rest"),
        ],
        "two_staccato": [
            (0, 1 / 4, "note"),
            (1 / 4, 1, "rest"),
            (1, 5 / 4, "note"),
            (5 / 4, 2, "rest"),
        ],
    },
}


# Pesos opcionais por acorde.
# Chaves são nomes como "Imaj7", "V7", "ivm7".
# A ausência de uma chave significa distribuição uniforme.
PATTERN_WEIGHTS_BY_CHORD = {
    # Exemplo para personalizar futuramente:
    # "V7": {
    #     "default": 1,
    #     "staccato": 2,
    #     "inverted_staccato": 3,
    #     "syncopated": 3,
    #     "two_attacks": 2,
    #     "rest": 0.2,
    # },
}


def choose_rhythm_pattern(chord: ChordState, rng=random) -> str:
    """Escolhe um padrão segundo os pesos associados ao acorde."""
    patterns = RHYTHMIC_PATTERNS["U2"]
    weights_by_name = PATTERN_WEIGHTS_BY_CHORD.get(chord.name, {})

    names = list(patterns.keys())
    weights = [weights_by_name.get(name, 1.0) for name in names]

    if any(weight < 0 for weight in weights) or sum(weights) <= 0:
        raise ValueError(f"Pesos inválidos para o acorde {chord.name}")

    return rng.choices(names, weights=weights, k=1)[0]


def generate_chord_events(
    chord: ChordState,
    start: float,
    rng=random,
) -> list[dict]:
    """Aplica um padrão rítmico ao acorde e retorna seus ataques."""
    pattern_name = choose_rhythm_pattern(chord, rng)
    pattern = RHYTHMIC_PATTERNS["U2"][pattern_name]

    events = []

    for relative_start, relative_end, kind in pattern:
        if not (0 <= relative_start < relative_end <= CHORD_DURATION):
            raise ValueError(
                f"Padrão {pattern_name} tem intervalo inválido: "
                f"{relative_start}, {relative_end}"
            )

        if kind == "rest":
            continue
        if kind != "note":
            raise ValueError(f"Tipo rítmico desconhecido: {kind}")

        events.append(
            {
                "chord": chord,
                "pattern": pattern_name,
                "start": start + relative_start,
                "duration": relative_end - relative_start,
            }
        )

    return events


def generate_accompaniment(progression, rng=random, ending=True) -> list[dict]:
    """Gera eventos rítmicos; cada acorde ocupa dois tempos."""
    events = []
    last = len(progression) - 1

    for index, chord in enumerate(progression):
        start = index * CHORD_DURATION

        if ending and index == last:
            events.append(
                {
                    "chord": chord,
                    "start": start,
                    "duration": ENDING_BEATS,
                }
            )
            continue
        events.extend(
            generate_chord_events(
                chord=chord,
                start=start,
                rng=rng,
            )
        )

    return events


CHORD_INTERVALS = {
    "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10),
    "7": (0, 4, 7, 10),
    "m7b5": (0, 3, 6, 10),
}


def chord_to_midi_notes(
    chord: ChordState,
    context: HarmonicContext,
    octave: int = 3,
) -> list[int]:
    """Converte o acorde em notas MIDI."""
    if chord.quality not in CHORD_INTERVALS:
        raise ValueError(f"Qualidade desconhecida: {chord.quality}")

    root_pitch_class = absolute_root(chord, context)
    root_midi = 12 * (octave + 1) + root_pitch_class

    return [root_midi + interval for interval in CHORD_INTERVALS[chord.quality]]


def accompaniment_to_midi(
    progression,
    context: HarmonicContext,
    output_path="output/accompaniment.mid",
    bpm: int = 110,
    octave: int = 3,
    velocity: int = 75,
    rng=random,
    ending: bool = True,
):
    """Gera o acompanhamento e salva o arquivo MIDI."""
    if bpm <= 0:
        raise ValueError("bpm precisa ser positivo")

    events = generate_accompaniment(progression, rng=rng, ending=ending)

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    piano = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano")
    )

    seconds_per_beat = 60.0 / bpm

    for event in events:
        pitches = chord_to_midi_notes(
            event["chord"],
            context,
            octave=octave,
        )

        start_seconds = event["start"] * seconds_per_beat
        end_seconds = (event["start"] + event["duration"]) * seconds_per_beat

        for pitch in pitches:
            piano.notes.append(
                pretty_midi.Note(
                    velocity=velocity,
                    pitch=pitch,
                    start=start_seconds,
                    end=end_seconds,
                )
            )

    midi.instruments.append(piano)

    add_walking_bass_to_midi(
        midi=midi,
        progression=progression,
        context=context,
        bpm=bpm,
        octave=2,
        ending=ending,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(path))

    return events


def generate_walking_bass(
    progression, context: HarmonicContext, octave: int = 2, ending=True
):
    """Gera duas semínimas de baixo por acorde."""
    events = []
    last = len(progression) - 1

    for index, chord in enumerate(progression):
        root = absolute_root(chord, context)
        root_midi = 12 * (octave + 1) + root

        # Acorde final: só a fundamental, sustentada.
        if ending and index == last:
            events.append(
                {
                    "start": index * 2.0,
                    "duration": ENDING_BEATS,
                    "pitch": root_midi,
                }
            )
            break

        next_chord = (
            progression[index + 1] if index + 1 < len(progression) else progression[0]
        )
        next_root = absolute_root(next_chord, context)
        next_midi = 12 * (octave + 1) + next_root

        if next_midi > root_midi:
            next_midi -= 1
        elif next_midi < root_midi:
            next_midi += 1
        else:
            next_midi += 7

        # Primeiro tempo: fundamental do acorde.
        events.append(
            {
                "start": index * 2.0,
                "duration": 1.0,
                "pitch": root_midi,
            }
        )

        # Segundo tempo: quinta do acorde, como ponto de partida.
        events.append(
            {
                "start": index * 2.0 + 1.0,
                "duration": 1.0,
                "pitch": next_midi,
            }
        )

    # events.append({})
    return events


def add_walking_bass_to_midi(
    midi: pretty_midi.PrettyMIDI,
    progression,
    context: HarmonicContext,
    bpm: int = 110,
    octave: int = 2,
    velocity: int = 85,
    ending: bool = False,
):
    """Adiciona uma pista de walking bass ao MIDI existente."""
    bass = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Bass")
    )

    seconds_per_beat = 60.0 / bpm
    events = generate_walking_bass(
        progression=progression, context=context, octave=octave, ending=ending
    )

    for event in events:
        bass.notes.append(
            pretty_midi.Note(
                velocity=velocity,
                pitch=event["pitch"],
                start=event["start"] * seconds_per_beat,
                end=(event["start"] + event["duration"]) * seconds_per_beat,
            )
        )

    midi.instruments.append(bass)
    return events
