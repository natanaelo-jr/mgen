import random
from pathlib import Path

import pretty_midi

from mgen.harmony import ChordState, HarmonicContext
from mgen.accompaniment import (
    generate_accompaniment,
    generate_walking_bass,
    chord_to_midi_notes,
)
from mgen.melody import generate_melody_events


def arrangement_to_midi(
    progression: list[ChordState],
    context: HarmonicContext,
    rhythm_events: list[dict],
    output_path="output/arrangement.mid",
    bpm: int = 110,
    piano_octave: int = 3,
    bass_octave: int = 2,
    melody_low: int = 60,
    melody_high: int = 84,
    piano_velocity: int = 75,
    bass_velocity: int = 85,
    melody_velocity: int = 90,
    rng=random,
    ending: bool = True,
):
    """Gera um MIDI com acompanhamento, walking bass e melodia."""
    if bpm <= 0:
        raise ValueError("bpm precisa ser positivo")

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    seconds_per_beat = 60.0 / bpm

    # 1. Acompanhamento harmônico
    piano = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
        name="Harmony",
    )

    accompaniment_events = generate_accompaniment(progression, rng=rng, ending=ending)

    for event in accompaniment_events:
        pitches = chord_to_midi_notes(
            event["chord"],
            context,
            octave=piano_octave,
        )

        start = event["start"] * seconds_per_beat
        end = (event["start"] + event["duration"]) * seconds_per_beat

        for pitch in pitches:
            piano.notes.append(
                pretty_midi.Note(
                    velocity=piano_velocity,
                    pitch=pitch,
                    start=start,
                    end=end,
                )
            )

    midi.instruments.append(piano)

    # 2. Walking bass
    bass = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Bass"),
        name="Walking Bass",
    )

    bass_events = generate_walking_bass(
        progression=progression,
        context=context,
        octave=bass_octave,
    )

    for event in bass_events:
        start = event["start"] * seconds_per_beat
        end = (event["start"] + event["duration"]) * seconds_per_beat

        bass.notes.append(
            pretty_midi.Note(
                velocity=bass_velocity,
                pitch=event["pitch"],
                start=start,
                end=end,
            )
        )

    midi.instruments.append(bass)

    # 3. Melodia
    melody_events = generate_melody_events(
        rhythm_events=rhythm_events,
        progression=progression,
        context=context,
        low=melody_low,
        high=melody_high,
        rng=rng,
    )

    melody_track = pretty_midi.Instrument(
        program=pretty_midi.instrument_name_to_program("Acoustic Grand Piano"),
        name="Melody",
    )

    for event in melody_events:
        start = event["start"] * seconds_per_beat
        end = (event["start"] + event["duration"]) * seconds_per_beat

        if end <= start:
            continue

        melody_track.notes.append(
            pretty_midi.Note(
                velocity=melody_velocity,
                pitch=event["pitch"],
                start=start,
                end=end,
            )
        )

    midi.instruments.append(melody_track)

    # 4. Salvar o arranjo completo
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(path))

    return {
        "accompaniment": accompaniment_events,
        "bass": bass_events,
        "melody": melody_events,
        "path": str(path),
    }
