# mgen — Composição Musical Algorítmica

Trabalho Prático 1 de **DCC831 – IA Generativa para Música** (UFMG, 2026/2).
Autor: Natanael dos Santos Júnior (matrícula 2023087842)

O `mgen` gera peças curtas em domínio simbólico (arquivo `.mid`) com três pistas:
melodia, acompanhamento de piano e walking bass. Cada execução produz uma peça
diferente a partir da mesma configuração, e os hiperparâmetros permitem variar o
caráter das peças geradas.

## Método e restrição estilística

- **Harmonia:** cadeia de Markov de ordem 1 sobre um vocabulário de 10 acordes
  (7 diatônicos + 3 empréstimos do modo menor paralelo), com pesos de transição
  definidos manualmente. Cada ciclo harmônico é condicionado a voltar à tônica
  ("ponte de Markov"), o que faz as cadências surgirem sem regras separadas.
- **Melodia:** cadeia de Markov de ordem 1 sobre as alturas, condicionada
  ao acorde da vez, ao próximo acorde, ao tempo (forte ou fraco) e à duração
  da nota.
- **Ritmo:** gramática generativa probabilística, que produz os padrões rítmicos
  da melodia e do acompanhamento.
- **Restrição estilística: Estilo Jazz/Blues anos 40**

A descrição técnica completa (vocabulário, fórmulas, pesos, ordem do modelo e
limitações) está em [`METODO.md`](METODO.md).

```
cadeia de Markov (harmonia) ──► progressão de acordes ──┬──► acompanhamento (piano + baixo)
                                                         │
gramática probabilística (ritmo) ──► eventos rítmicos ───┤
                                                         └──► melodia (Markov com contexto harmônico)

pistas ──► MIDI (pretty_midi) ──► áudio (FluidSynth, só para audição)
```

## Instalação

Requer Python >= 3.12.

Com venv padrão:
```bash
git clone https://github.com/natanaelo-jr/mgen.git
cd mgen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ou usando [uv](https://github.com/astral-sh/uv):
```bash
uv sync
```

Dependências principais: `pretty_midi` e `numpy`. Para renderizar áudio é preciso
ter o [FluidSynth](https://www.fluidsynth.org/) instalado e um soundfont livre, ou alguma fonte/daw à escolha
(arquivo `.sf2`).

## Como gerar músicas

O script principal expõe uma interface de linha de comando com opções para tom, velocidade, tamanho em compassos, semente aleatória e caminho de saída.

### Execução rápida (padrão)

```bash
# Executando via módulo python
python -m mgen.main

# Ou usando uv
uv run python -m mgen.main
```

O arquivo gerado será salvo em `outputs/arrangement.mid`.

### Opções de linha de comando (`--help`)

Para visualizar todas as opções disponíveis:

```bash
uv run python -m mgen.main --help
```

```
usage: mgen [-h] [-t [0-12]] [-v BPM] [-b BARS] [-s SEED] [-o OUTPUT]

mgen — Composição Musical Algorítmica (Jazz/Blues anos 40)
Gera peças em formato MIDI combinando cadeias de Markov para harmonia e melodia
com gramática probabilística para ritmo.

options:
  -h, --help            Exibe esta mensagem de ajuda e encerra.
  -t [0-12], --tonic, --tom [0-12]
                        Tom da peça (classe de altura da tônica: 0=C, 1=C#, 2=D,
                        3=D#, 4=E, 5=F, 6=F#, 7=G, 8=G#, 9=A, 10=A#, 11=B, 12=C).
                        (padrão: 0)
  -v BPM, --bpm, --velocidade BPM
                        Velocidade/andamento da música em batidas por minuto (BPM).
                        (padrão: 140)
  -b BARS, --bars, --tamanho BARS
                        Tamanho da peça em número de compassos.
                        (padrão: 8)
  -T, --temp, --temperature <f>
                        Temperatura da cadeia de Markov harmônica (<1 previsível, >1 diversa).
                        (padrão: 1.0)
  -c, --cadence, --cadence-strength <f>
                        Força de condicionamento cadencial (ponte de Markov).
                        0 desliga o retorno forçado, 1.0 é o condicionamento exato, >=2 formulaico.
                        (padrão: 1.0)
  -s SEED, --seed SEED  Semente do gerador pseudoaleatório para reproduzir resultados
                        idênticos. (padrão: None)
  -o OUTPUT, --output OUTPUT
                        Caminho do arquivo MIDI de saída a ser gerado.
                        (padrão: outputs/arrangement.mid)
```

### Exemplos de uso

```bash
# Variação de temperatura:
./test.sh -t 0 -v 130 -b 8 -T 0.5 -s 11 -w outputs/exemplo_temp_baixa.wav
./test.sh -t 5 -v 140 -b 8 -T 1.0 -s 22 -w outputs/exemplo_temp_media.wav
./test.sh -t 10 -v 145 -b 8 -T 1.6 -s 33 -w outputs/exemplo_temp_alta.wav

# Variação de força cadencial (ponte de Markov):
./test.sh -t 0 -v 135 -b 8 -T 1.0 -c 0.0 -s 41 -w outputs/exemplo_cadencia_zero.wav
./test.sh -t 0 -v 135 -b 8 -T 1.0 -c 2.5 -s 41 -w outputs/exemplo_cadencia_forte.wav
```

## Hiperparâmetros

| Módulo   | Parâmetro          | Padrão / Padrão em `midi.py` | Efeito                                                                                                                            |
| -------- | ------------------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Harmonia | `bars`             | 8                            | Número de compassos (2 acordes por compasso).                                                                                     |
| Harmonia | `cycle_bars`       | 4 (8 no `main.py`)           | Tamanho do ciclo que volta à tônica (4 ou 8).                                                                                     |
| Harmonia | `temperature`      | 1.0                          | Abaixo de 1, concentra a probabilidade nas transições mais prováveis (progressões previsíveis). Acima de 1, aproxima do uniforme. |
| Harmonia | `cadence_strength` | 1.0                          | 0 desliga a preparação de cadências. 1 é o condicionamento exato. 2 ou mais gera cadências mais formulaicas.                      |
| Harmonia | `tonic`            | 0                            | Tônica da escala (0 = C, 1 = C#, ..., 11 = B).                                                                                    |
| Final    | `ending`           | `True`                       | Adiciona a tônica sustentada ao fim da progressão e prepara o encerramento da melodia e baixo.                                   |
| Final    | `settle_beats`     | 0.0                          | Acalma o ritmo da melodia nos últimos tempos antes do acorde final.                                                               |
| Melodia  | `melody_low`, `melody_high` | 60, 84             | Registro da melodia (números MIDI, C4 a C6).                                                                                      |
| Saída    | `bpm`              | 110 (140 no `main.py`)       | Andamento da peça (batidas por minuto).                                                                                           |
| Saída    | `piano_octave`     | 3                            | Oitava do piano de acompanhamento.                                                                                                |
| Saída    | `bass_octave`      | 2                            | Oitava do walking bass.                                                                                                           |

## Músicas de exemplo

Os arquivos gerados ficam salvos em `outputs/` (arquivos `.mid` e `.wav` sintetizados com o FluidSynth):

| Arquivo | Semente | Hiperparâmetros | Observação |
| ------- | ------- | --------------- | ---------- |
| `outputs/exemplo_temp_baixa.wav` | 11 | `tonic=0 (C), bpm=130, bars=8, temperature=0.5, cadence=1.0` | **Temperatura baixa:** progressão conservadora e cadencial $ii\text{--}V\text{--}I$, alta previsibilidade tonal. |
| `outputs/exemplo_temp_media.wav` | 22 | `tonic=5 (F), bpm=140, bars=8, temperature=1.0, cadence=1.0` | **Temperatura neutra:** equilíbrio entre transições funcionais padrão e variedade melódica com swing. |
| `outputs/exemplo_temp_alta.wav` | 33 | `tonic=10 (Bb), bpm=145, bars=8, temperature=1.6, cadence=1.0` | **Temperatura alta:** maior frequência de empréstimos modais ($\flat\text{VImaj7}$, $\text{ivm7}$), maior tensão harmônica. |
| `outputs/exemplo_cadencia_zero.wav` | 41 | `tonic=0 (C), bpm=135, bars=8, temperature=1.0, cadence=0.0` | **Sem atração cadencial ($\lambda=0$):** caminhos harmônicos livres sem preparar resoluções direcionais na tônica. |
| `outputs/exemplo_cadencia_forte.wav` | 41 | `tonic=0 (C), bpm=135, bars=8, temperature=1.0, cadence=2.5` | **Cadência estrita ($\lambda=2.5$):** atração forte no fechamento dos ciclos, forçando cadências resolutivas imediatas ($ii\text{--}V\text{--}I$). |

### Renderizar áudio a partir do MIDI

Você pode sintetizar e ouvir diretamente usando o script [`test.sh`](test.sh):

```bash
# Gerar MIDI e ouvir prévia em tempo real:
./test.sh --tom 0 --velocidade 140 --tamanho 8

# Gerar MIDI e salvar diretamente como WAV:
./test.sh --tom 7 --velocidade 120 --tamanho 16 --seed 42 -w outputs/musica.wav
```

Ou diretamente pelo FluidSynth na linha de comando:

```bash
fluidsynth -ni -g 2 -F outputs/arrangement.wav -r 44100 ~/Music/SoundFonts/GeneralUser-GS.sf2 outputs/arrangement.mid
```

## Estrutura do repositório

```
mgen/
├── pyproject.toml              # Metadados do projeto e dependências (uv/pip)
├── requirements.txt            # Dependências com hashes
├── README.md                   # Instruções de instalação e uso
├── METODO.md                   # Documentação teórica e técnica detalhada
├── test.sh                     # Script de teste e sintetização rápida
├── outputs/                    # Arquivos MIDI gerados
│   ├── arrangement.mid         # Arranjo com melodia, piano e walking bass
│   ├── accompaniment.mid       # Acompanhamento isolado (piano + baixo)
│   └── ritmo.mid               # Demonstração rítmica
└── src/
    └── mgen/
        ├── __init__.py         # Ponto de entrada do pacote
        ├── main.py             # Script de execução principal
        ├── harmony.py          # Cadeia de Markov para harmonia (vocabulário, transições, ciclos)
        ├── grammars.py         # Gramática probabilística (PCFG) e padrões rítmicos
        ├── melody.py           # Cadeia de Markov de alturas condicionada ao contexto harmônico
        ├── accompaniment.py    # Geração dos voicings de piano e walking bass
        └── midi.py             # Montagem e exportação para arquivos MIDI via pretty_midi
```

## Uso de IA

**Ferramenta:** Chat GPT, pela interface web.

Utilizado para auxílio na modelagem e escrita do código de forma geral.

**Conversas (links): https://chatgpt.com/share/6acc0f9d-e744-83e9-96a9-25e6985efd18 **
