# Documentação técnica do método

Este documento descreve como o `mgen` representa e gera música. O README traz
instalação e reprodução dos resultados.

## 1. Representação simbólica

- Fôrmula de compasso 4/4. A unidade de tempo é a semínima (_beat_).
- Cada acorde ocupa **2 tempos** (2 acordes por compasso).
- Alturas são números MIDI. A tonalidade vem de um contexto harmônico
  (`HarmonicContext`: tônica e modo), e a fundamental absoluta de um acorde é
  `(tônica + grau) mod 12`.
- A saída é um arquivo `.mid` escrito com `pretty_midi`, com três pistas:

| Pista   | Instrumento                            | Registro                                 |
| ------- | -------------------------------------- | ---------------------------------------- |
| Melodia | Acoustic Grand Piano (ou Lead 1)       | MIDI 60 a 84                             |
| Piano   | Acoustic Grand Piano                   | acordes em posição fundamental, oitava 3 |
| Baixo   | Acoustic Bass                          | oitava 2                                 |

## 2. Harmonia: cadeia de Markov de ordem 1

### 2.1 Vocabulário

Dez estados, definidos em relação à tônica. Os três últimos são empréstimos do
modo menor paralelo.

| Acorde  | Grau (semitons) | Qualidade | Função       | Empréstimo |
| ------- | --------------- | --------- | ------------ | ---------- |
| Imaj7   | 0               | maj7      | tônica       | não        |
| IIm7    | 2               | m7        | predominante | não        |
| IIIm7   | 4               | m7        | tônica       | não        |
| IVmaj7  | 5               | maj7      | predominante | não        |
| V7      | 7               | 7         | dominante    | não        |
| VIm7    | 9               | m7        | tônica       | não        |
| VIIm7b5 | 11              | m7b5      | dominante    | não        |
| ivm7    | 5               | m7        | predominante | sim        |
| bVImaj7 | 8               | maj7      | predominante | sim        |
| bVII7   | 10              | 7         | dominante    | sim        |

### 2.2 Probabilidades de transição

As probabilidades **não são aprendidas de um corpus**: os pesos `w(a, b)` foram
definidos manualmente (`TRANSITIONS` em `harmony.py`) e normalizados por linha:

```
P(a → b) = w(a, b) / Σ_c w(a, c)
```

Critérios usados para definir os pesos:

- o ciclo de quintas (VIIm7b5 → IIIm7 → VIm7 → IIm7 → V7 → Imaj7) como "motor"
  da harmonia diatônica;
- ênfase em IIm7 → V7 e V7 → Imaj7, com V7 → VIm7 como cadência de engano;
- empréstimos modais com pesos baixos, para aparecerem como cor e não como regra;
- autotransições (acorde repetido) com pesos baixos e consistentes entre estados.

### 2.3 Temperatura

Antes da normalização, cada peso é elevado a `1/T`:

```
w'(a, b) = w(a, b)^(1/T)
```

`T < 1` concentra a probabilidade nas transições mais prováveis (progressões mais
previsíveis). `T > 1` aproxima a distribuição do uniforme.

### 2.4 Ciclos e condicionamento por destino ("ponte de Markov")

A progressão é dividida em ciclos de `cycle_bars` compassos (4 ou 8), e cada
ciclo recomeça na tônica `Imaj7`. Em vez de sortear livremente e forçar a tônica
no fim, cada acorde é sorteado já sabendo quantas transições faltam para a
próxima chegada à tônica.

Sejam `P` a matriz de transição, `i` o acorde atual, `n` o número de transições
até a tônica e `λ` o parâmetro `cadence_strength`:

```
P(j | i, n)  ∝  P[i, j] · ( (P^(n−1))[j, Imaj7] )^λ
```

O segundo fator é a probabilidade de, saindo de `j`, chegar à tônica
exatamente no passo certo. Longe da fronteira do ciclo, ele quase não influencia
o sorteio. Perto dela, favorece naturalmente V7 e IIm7, e padrões como ii–V–I
surgem sem uma tabela de cadências separada. Estados que não alcançam a tônica
a tempo recebem probabilidade zero.

- `λ = 0`: sem preparação de cadência (só caminhos viáveis).
- `λ = 1`: condicionamento exato.
- `λ ≥ 2`: cadências mais formulaicas.

No fim da progressão usa-se uma tônica "virtual" depois do último acorde. Assim,
a progressão termina preparando a tônica e funciona em _loop_.

### 2.5 Final da música

`with_ending(progression, authentic=False)` acrescenta um `Imaj7` final, sustentado
por `ENDING_BEATS = 4.0` tempos (uma barra) nas três pistas. Com
`authentic=True`, a última preparação é trocada por `V7`, garantindo V7 → I.

## 3. Ritmo: gramática generativa probabilística

A geração rítmica é estruturada em dois níveis: uma gramática livre de contexto probabilística (PCFG) que divide a peça em unidades de tempo abstratas (`U1` = 1 tempo de semínima, `U2` = 2 tempos de semínima), seguida por uma substituição probabilística de cada unidade por padrões rítmicos concretos (com notas, pausas, quiálteras ou síncopas).

### 3.1 Gramática formal

**G = (N, T, P, S)**

- **N** (não-terminais): `{S, B, D2}`
  - `S`: símbolo inicial (axioma da peça)
  - `B`: bloco/compasso de 4 tempos (bar)
  - `D2`: subdivisão de 2 tempos
- **T** (terminais): `{U1, U2}`
  - `U1`: unidade de duração 1 tempo (semínima)
  - `U2`: unidade de duração 2 tempos (mínima)
- **S** (axioma): `S`
- **P** (regras de produção):

| Regra | Probabilidade | Descrição |
| ----- | ------------- | --------- |
| `S → B B B B B B B B` (`B * 8`) | 0.75 | Peça de 8 compassos |
| `S → B B B B B B B B B B B B B B B B` (`B * 16`) | 0.25 | Peça de 16 compassos |
| `B → D2 D2` | 0.75 | Divisão binária do compasso (2 + 2) |
| `B → U1 U2 U1` | 0.25 | Síncopa/divisão ternária de compasso (1 + 2 + 1) |
| `D2 → U1 U1` | 0.75 | Duas semínimas (1 + 1) |
| `D2 → U2` | 0.25 | Uma mínima (2) |

### 3.2 Mapeamento terminal → evento rítmico

Após a derivação na gramática, a árvore é linearizada acumulando os tempos de início (`start`). Cada terminal `U1` e `U2` é então mapeado estocasticamente (escolha aleatória com distribuição uniforme) em um dos padrões de `RHYTHMIC_PATTERNS`:

- **Padrões para `U1` (duração 1 tempo):**
  - `staccato`: colcheia tocada (offset 0, dur 0.5) + pausa de colcheia (0.5 a 1.0)
  - `inverted_staccato`: pausa de colcheia (0 a 0.5) + colcheia tocada (offset 0.5, dur 0.5)
  - `rest`: pausa completa de 1 tempo
  - `triplet`: três terceiros de tempo (quiáltera de 3 notas com dur 1/3)
  - `dotted_eighth_sixteenth`: colcheia pontuada (dur 0.75) + semicolcheia (dur 0.25)

- **Padrões para `U2` (duração 2 tempos):**
  - `default`: nota sustentada por 2 tempos
  - `staccato`: colcheia tocada (offset 0, dur 0.5) + pausa de 1.5 tempos
  - `inverted_staccato`: pausa de 1.5 tempos + colcheia tocada (offset 1.5, dur 0.5)

Cada padrão gera eventos `{start, duration}` (em tempos de semínima), descartando as pausas. Em seguida, a melodia atribui alturas a esses eventos. O acompanhamento de piano também possui padrões próprios de 2 tempos (`CHORD_DURATION = 2.0`), garantindo variedade rítmica nas harmonias.

## 4. Melodia: cadeia de Markov de ordem 1 com contexto harmônico

### 4.1 Estados candidatos

Para cada evento rítmico, as alturas candidatas estão no registro
`[low, high] = [60, 84]` e são classificadas segundo o acorde vigente:

- **nota do acorde**: classes de altura do acorde (fundamental, terça, quinta, sétima);
- **pentatônica**: classes da coleção pentatônica do acorde que não são notas do acorde;
- **cromática**: vizinhas (a 1 semitom) da coleção pentatônica;
- as demais alturas são excluídas.

### 4.2 Distribuição

A probabilidade de uma altura é proporcional ao produto de fatores. Os valores
abaixo foram escolhidos manualmente.

| Fator             | Quando                            | Efeito                                                                                     |
| ----------------- | --------------------------------- | ------------------------------------------------------------------------------------------ | --- | ---------------------------------------------- |
| Categoria         | sempre                            | nota do acorde: 4.0 (tempo forte) ou 2.0 (fraco); pentatônica: 2.0 ou 2.5; cromática: 0.25 |
| Papel do grau     | nota do acorde                    | terça e sétima valem mais (tabela abaixo); em tempo fraco, usa-se a raiz quadrada do peso  |
| Duração           | nota fora do acorde               | peso dividido por `max(1, 2 · duração)`: notas longas pedem consonância                    |
| Registro          | sempre                            | gaussiana centrada em `(low + high) // 2`, com desvio `(high − low) / 3.5`                 |
| Intervalo         | há nota anterior                  | peso `INTERVAL_WEIGHTS[                                                                    | Δ   | ]` (tabela abaixo); acima de 12 semitons, 0.05 |
| Resolução         | nota anterior fora do acorde      | nota do acorde a 1–2 semitons: ×4.0; outra nota fora do acorde: ×0.3                       |
| Condução de vozes | troca de acorde                   | sétima do acorde anterior descendo 1–2 semitons para a terça do atual: ×3.0                |
| Antecipação       | último evento antes da troca      | nota do próximo acorde: ×1.8; vizinha a 1 semitom de uma nota do próximo acorde: ×1.5      |
| Cadência final    | última nota antes do acorde final | segundo grau ou sensível: ×8.0; demais notas: ×0.25                                        |

Papel do grau (`CHORD_TONE_ROLE`, por qualidade e semitons a partir da fundamental):

| Qualidade | Pesos                           |
| --------- | ------------------------------- |
| maj7      | 0: 1.0, 4: 2.0, 7: 0.7, 11: 1.8 |
| m7        | 0: 1.0, 3: 2.0, 7: 0.7, 10: 1.8 |
| 7         | 0: 0.8, 4: 2.2, 7: 0.6, 10: 2.2 |
| m7b5      | 0: 0.8, 3: 2.0, 6: 1.2, 10: 2.0 |

Pesos de intervalo (`INTERVAL_WEIGHTS`, em semitons):

| 0   | 1   | 2   | 3   | 4   | 5   | 6   | 7   | 8    | 9   | 10   | 11  | 12   |
| --- | --- | --- | --- | --- | --- | --- | --- | ---- | --- | ---- | --- | ---- |
| 0.6 | 0.8 | 5.0 | 3.5 | 2.5 | 1.5 | 0.5 | 1.0 | 0.35 | 0.3 | 0.15 | 0.1 | 0.08 |

### 4.3 Contexto condicionante

A escolha depende da altura anterior e de um contexto determinístico, conhecido
de antemão a partir da partitura: acorde atual, próximo acorde, posição no
compasso (tempos 1 e 3 são fortes), duração do evento, categoria e acorde da nota
anterior e a indicação de "última nota antes do final". Em termos formais, é uma
cadeia de Markov de ordem 1 sobre as alturas com informação lateral
determinística, e não uma cadeia de Markov pura sobre alturas.

### 4.4 Nota final

A melodia termina com a tônica mais próxima da última nota tocada, sustentada por
`ENDING_BEATS` tempos. Como a última nota antes do final tende a ser o segundo
grau ou a sensível, a chegada é por grau conjunto.

O parâmetro opcional `settle_beats` acalma o ritmo antes do fim: nos últimos
`settle_beats` tempos, ficam só as notas que caem em tempo forte, e cada uma é
alongada até a próxima ou até o acorde final.

## 5. Acompanhamento

- **Piano:** acorde em posição fundamental (oitava 3), com o ritmo vindo da gramática. No acorde final, um bloco sustentado.
- **Baixo (determinístico):** no primeiro tempo de cada acorde, a fundamental
  (oitava 2). No segundo tempo, uma nota de aproximação cromática da próxima
  fundamental: um semitom abaixo se a próxima fundamental for mais aguda, um
  semitom acima se for mais grave e, quando coincidem, a quinta justa acima. No
  acorde final, só a fundamental, sustentada.

## 6. Ordem do modelo e trade-off

Escolheu-se **ordem 1** pelos motivos abaixo.

- Com 10 estados harmônicos, a ordem 2 tem 100 contextos. Como os pesos são
  definidos manualmente, isso exigiria centenas de valores para ajustar.
- Como não há corpus, não há risco de memorização de trechos. O trade-off
  clássico (ordem alta = mais fiel ao corpus, com risco de decorar) se traduz aqui em
  **fidelidade ao estilo que o autor codificou** contra **flexibilidade**.
- A estrutura de longo alcance (retorno à tônica, cadências) é obtida por
  **condicionamento por destino**, e não por aumento da ordem.
- Na melodia, a ordem 1 mantém a condução por graus conjuntos e a relação com o
  acorde, mas não "lembra" motivos: a coerência de frase fica limitada.

## 7. Limitações conhecidas

- Os pesos foram ajustados de ouvido e por critérios de teoria funcional, sem
  avaliação quantitativa contra um corpus.
- A melodia não tem memória de motivos: o ritmo é repetido pela gramática, mas o
  contorno melódico não.
- O ritmo é gerado independentemente da função harmônica.
- O baixo é determinístico.
- O final é sempre sobre `Imaj7`.
