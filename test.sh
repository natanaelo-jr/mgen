#!/usr/bin/env bash
set -e

# Padrões
TONIC=0
BPM=140
BARS=8
TEMP=1.0
CADENCE=1.0
SEED=""
OUTPUT_MID="outputs/arrangement.mid"
WAV_FILE=""
SF2_PATH="$HOME/Music/SoundFonts/GeneralUser-GS.sf2"

usage() {
  cat <<EOF
Uso: $0 [opções]

Gera a música em MIDI com os parâmetros informados e, opcionalmente, exporta para WAV via FluidSynth.

Opções:
  -t, --tom, --tonic <0-12>     Tom da peça (0=C, 1=C#, ..., 12=C). Padrão: $TONIC
  -v, --velocidade, --bpm <num> Andamento em BPM. Padrão: $BPM
  -b, --tamanho, --bars <num>   Tamanho em número de compassos. Padrão: $BARS
  -T, --temp, --temperature <f> Temperatura harmônica (<1 previsível, >1 diversa). Padrão: $TEMP
  -c, --cadence <f>             Força cadencial/ponte de Markov (0=desligado, 1=exato, >=2=rígido). Padrão: $CADENCE
  -s, --seed <num>              Semente pseudoaleatória para reprodutibilidade.
  -o, --output <caminho.mid>    Arquivo MIDI de saída. Padrão: $OUTPUT_MID
  -w, --wav <caminho.wav>       Exporta também em áudio WAV com o nome/caminho especificado.
  --sf2 <caminho.sf2>           SoundFont para o FluidSynth. Padrão: $SF2_PATH
  -h, --help                    Exibe esta mensagem de ajuda.

Exemplos:
  $0
  $0 --tom 7 --velocidade 120 --tamanho 16 --seed 42 --temp 1.4 --cadence 2.0
  $0 --tom 2 --tamanho 8 --temp 0.6 -w outputs/musica.wav
EOF
  exit 0
}

# Parsing de argumentos
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tom|--tonic)
      TONIC="$2"
      shift 2
      ;;
    -v|--velocidade|--bpm)
      BPM="$2"
      shift 2
      ;;
    -b|--tamanho|--bars)
      BARS="$2"
      shift 2
      ;;
    -T|--temp|--temperature)
      TEMP="$2"
      shift 2
      ;;
    -c|--cadence|--cadence-strength)
      CADENCE="$2"
      shift 2
      ;;
    -s|--seed)
      SEED="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_MID="$2"
      shift 2
      ;;
    -w|--wav)
      WAV_FILE="$2"
      shift 2
      ;;
    --sf2)
      SF2_PATH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Opção desconhecida: $1" >&2
      echo "Use $0 --help para ver as opções disponíveis." >&2
      exit 1
      ;;
  esac
done

# Monta o comando Python
CMD=("uv" "run" "python" "-m" "mgen.main" "--tom" "$TONIC" "--velocidade" "$BPM" "--tamanho" "$BARS" "--temp" "$TEMP" "--cadence-strength" "$CADENCE" "--output" "$OUTPUT_MID")

if [[ -n "$SEED" ]]; then
  CMD+=("--seed" "$SEED")
fi

echo "==> Executando geração MIDI..."
"${CMD[@]}"

# Renderização WAV opcional ou reprodução direta
if [[ -n "$WAV_FILE" ]]; then
  mkdir -p "$(dirname "$WAV_FILE")"
  echo "==> Renderizando áudio WAV em $WAV_FILE usando FluidSynth..."
  fluidsynth -ni -g 2 -F "$WAV_FILE" -r 44100 "$SF2_PATH" "$OUTPUT_MID"
  echo "==> WAV gerado com sucesso: $WAV_FILE"
else
  echo "==> Tocando prévia via FluidSynth..."
  fluidsynth -ni -g 2 "$SF2_PATH" "$OUTPUT_MID"
fi
