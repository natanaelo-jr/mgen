from mgen.grammars import expand, generate_rhythm_events
from mgen.midi import arrangement_to_midi
from mgen.harmony import generate_progression, absolute_root, HarmonicContext
from mgen.accompaniment import accompaniment_to_midi
from mgen.melody import generate_melody_events


def main():
    bpm = 140
    tonic = 0

    context = HarmonicContext(tonic=tonic)
    progression = generate_progression(bars=8, tonic=tonic, cycle_bars=8)

    rhythm_tree = expand("S")
    rhythm_events = generate_rhythm_events(rhythm_tree)

    melody = generate_melody_events(
        rhythm_events=rhythm_events,
        progression=progression,
        context=context,
        ending=True,
    )

    result = arrangement_to_midi(
        progression=progression,
        context=context,
        rhythm_events=rhythm_events,
        output_path="outputs/arrangement.mid",
        bpm=bpm,
        ending=True,
    )


if __name__ == "__main__":
    main()
