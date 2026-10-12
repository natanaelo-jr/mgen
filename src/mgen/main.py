import argparse
import random
from mgen.grammars import expand, generate_rhythm_events
from mgen.midi import arrangement_to_midi
from mgen.harmony import generate_progression, HarmonicContext


def parse_args():
    parser = argparse.ArgumentParser(
        prog="mgen",
        description=(
            "mgen — Composição Musical Algorítmica (Jazz/Blues anos 40)\n"
            "Gera peças em formato MIDI combinando cadeias de Markov para harmonia e melodia "
            "com gramática probabilística para ritmo."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-t",
        "--tonic",
        "--tom",
        dest="tonic",
        type=int,
        default=0,
        choices=range(0, 13),
        metavar="[0-12]",
        help=(
            "Tom da peça (classe de altura da tônica: 0=C, 1=C#, 2=D, 3=D#, 4=E, 5=F, "
            "6=F#, 7=G, 8=G#, 9=A, 10=A#, 11=B, 12=C/oitava)."
        ),
    )

    parser.add_argument(
        "-v",
        "--bpm",
        "--velocidade",
        dest="bpm",
        type=int,
        default=140,
        help="Velocidade/andamento da música em batidas por minuto (BPM).",
    )

    parser.add_argument(
        "-b",
        "--bars",
        "--tamanho",
        dest="bars",
        type=int,
        default=8,
        help="Tamanho da peça em número de compassos (bars).",
    )

    parser.add_argument(
        "-s",
        "--seed",
        dest="seed",
        type=int,
        default=None,
        help="Semente do gerador pseudoaleatório para reproduzir resultados idênticos.",
    )

    parser.add_argument(
        "-T",
        "--temp",
        "--temperature",
        dest="temperature",
        type=float,
        default=1.0,
        help=(
            "Temperatura da cadeia de Markov harmônica. Valores < 1.0 geram progressões "
            "mais previsíveis/conservadoras; valores > 1.0 aumentam a variedade e empréstimos modais."
        ),
    )

    parser.add_argument(
        "-c",
        "--cadence",
        "--cadence-strength",
        dest="cadence_strength",
        type=float,
        default=1.0,
        help=(
            "Força de condicionamento cadencial (ponte de Markov). "
            "0 desliga o condicionamento por destino, 1.0 é o condicionamento exato, "
            "e valores >= 2.0 tornam as chegadas cadenciais estritamente formulaicas (ii-V-I)."
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        type=str,
        default="outputs/arrangement.mid",
        help="Caminho do arquivo MIDI de saída a ser gerado.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random

    tonic = args.tonic % 12
    context = HarmonicContext(tonic=tonic)

    cycle_bars = 8 if args.bars % 8 == 0 else (4 if args.bars % 4 == 0 else 4)

    progression = generate_progression(
        bars=args.bars,
        tonic=tonic,
        cycle_bars=cycle_bars,
        temperature=args.temperature,
        cadence_strength=args.cadence_strength,
        rng=rng,
    )

    rhythm_tree = expand("S", bars=args.bars, rng=rng)
    rhythm_events = generate_rhythm_events(rhythm_tree, rng=rng)

    result = arrangement_to_midi(
        progression=progression,
        context=context,
        rhythm_events=rhythm_events,
        output_path=args.output,
        bpm=args.bpm,
        rng=rng,
        ending=True,
    )

    print(f"Música gerada com sucesso em: {result['path']}")
    print(
        f"Parâmetros: Tom={tonic} (C+{tonic}), Velocidade={args.bpm} BPM, "
        f"Tamanho={args.bars} compassos, Temp={args.temperature}, Cadence={args.cadence_strength}, Seed={args.seed}"
    )


if __name__ == "__main__":
    main()
