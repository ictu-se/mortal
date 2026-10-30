# MORTAL replication package

Code and retained evidence for **MORTAL: Multi-Oracle Robustness Testing as a
Quality Gate for LLM-Generated Software Artifacts**.

The analysis joins artifact validity, reference correctness, repeat stability,
fixed instruction probes, synthetic-mutant detection, and generation cost by
case/model/variant/repetition. The strict historical gate requires all nine
observations for a case to pass the applicable checks and an optional mean
per-call generation budget. These predicates compose established oracles.

## Retained study evidence

| Cohort | Domain | Cases | Models | Variants | Repeats | Calls |
|---|---|---:|---:|---:|---:|---:|
| Historical | ULT Lite | 200 | 3 Qwen sizes | 3 | 3 | 5,400 |
| Historical | SimiloLLM | 804 | 3 Qwen sizes | 3 | 3 | 21,708 |
| Second family | ULT Lite | 100 | DeepSeek-Coder 6.7B | Original | 3 | 300 |
| Second family | SimiloLLM | 100 | DeepSeek-Coder 6.7B | Original | 3 | 300 |

The historical mutation evidence contains 600 wrapper mutants and 14,874
artifact–mutant evaluations. The second-family comparison uses the same sampled
cases and original-prompt conditions from the historical Qwen observations.
All 47 Similo applications are represented in the selected 100 cases.

The extension initially scheduled 1,800 calls. Before analyzing its outcomes,
measured acquisition cost prompted an amendment to 600 original-prompt calls;
case selection and three repetitions remained unchanged. The 49 completed
non-original responses remain in the raw evidence as exploratory records and
are excluded from the primary comparison solely by prompt condition. The
initial design, amended design, and amendment are retained. The extension does
not estimate the nine-condition gate across prompt variants.

## Install and reproduce tables and figures

The recorded analysis environment used Python 3.9.6, NumPy 1.26.4,
pandas 2.3.3, and Matplotlib 3.9.4. Reference execution uses Python subprocesses;
mutation execution uses POSIX interval timers (macOS or Linux).

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make check
make analyze
make displays
```

`make analyze` uses the retained, response-hash-checked oracle evaluations. It
reproduces the historical and matched summary tables, cluster bootstrap
intervals, paired probe differences, case-level gate decisions, held-out repetition selection, and budget
retention without downloading models or benchmarks. The bootstrap uses 4,000
resamples with seed 20261029, clustering ULT observations by task and Similo
observations by application. Matched outputs contain original-only summaries
and repeat stability, with no inferred nine-condition gate.

`make displays` creates the empirical figures and table fragments under
`results/displays/`. Their source measurements are the CSV analysis outputs
under `results/quality_gates/`. The table fragments are generated locally;
manuscript sources, manuscript PDFs, and correspondence are not repository
contents.

`make historical` reproduces only the 27,108-call historical analysis.

The post hoc held-out replay selects cases using the first two repetitions of
each variant (six observations), then evaluates all three artifacts from the
reserved third repetition. It compares schema-only and joint selection on the
same held-out outcomes and reports successful/selected cases. This is
conditional reliability on recorded tasks, not transfer to unseen tasks.

## Obtain the benchmark inputs

Download the upstream benchmarks from
[UnLeakedTestBench](https://github.com/huangd1999/UnLeakedTestBench) and
[SimiloLLM](https://github.com/michelnass/SimiloLLM). The published benchmark
articles are [Huang et al.](https://doi.org/10.1145/3805043) and
[Nass et al.](https://doi.org/10.1002/stvr.1893).

Use this layout, or set `DATASETS` to another directory:

```text
reproduction_datasets/
  UnLeakedTestBench/datasets/ULT_Lite.jsonl
  SimiloLLM/old.txt
  SimiloLLM/new.txt
  SimiloLLM/oracles.txt
```

Despite its suffix, the retained upstream ULT input is one JSON array. Dataset
SHA-256 fingerprints are recorded in the extension design. The study uses the
first 200 ULT entries in that input order and the deterministic top-50 Similo
candidate builder. Third-party benchmark material and derived function bodies
remain subject to their upstream terms; this repository's code license does
not replace those terms.

To recompute the extension's oracle evaluations from its saved responses,
move `results/family_extension/evaluated.jsonl` and
`results/family_extension/reference_evaluations.jsonl` to a backup location,
then run:

```bash
make analyze DATASETS=/path/to/reproduction_datasets
```

The reference evaluator uses the historical process-isolated 1.5-second limit.
Mutation assessment filters reference-passing assertions at 0.5 seconds and
uses the same limit on mutants. `mutants.py` reproduces all 600 historical
wrapper implementations. The three operators corrupt the return value,
return `None`, or perturb the first positional argument. They are syntax
checked but not equivalence filtered; yield is not real-defect recall.

## Rerun local inference

Install [Ollama](https://ollama.com/) and start its local service. Pull the
models required for the chosen cohort. The recorded extension used Ollama
0.34.4 and DeepSeek-Coder 6.7B Q4_0, with digest
`ce298d984115b93bb1b191b47fee6b39e4e9fbd5f18e651c02f9fa74e0edcd13`.
Model tags can change; retain the resolved digest for a new run.

```bash
ollama pull deepseek-coder:6.7b
python3 run_family_extension.py \
  --datasets /path/to/reproduction_datasets \
  --output results/reruns/deepseek \
  --variants original --workers 1
```

The output directory is explicit so a fresh acquisition preserves the published
evidence. Repeating the command resumes only that design. A changed design
requires a different directory. Primary sampling is fixed by seed 20261029;
decoding seeds are 20261029–20261031. The historical prompt builders are reused.

To rerun the historical Qwen conditions:

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
python3 run_ollama_ult_lite_experiment.py \
  --datasets /path/to/reproduction_datasets \
  --output results/reruns/ult \
  --models qwen2.5-coder:1.5b,qwen2.5-coder:7b,qwen2.5-coder:14b \
  --limit 200 --repeats 3 --resume
python3 run_similo_ollama_experiment.py \
  --datasets /path/to/reproduction_datasets \
  --output results/reruns/similo \
  --models qwen2.5-coder:1.5b,qwen2.5-coder:7b,qwen2.5-coder:14b \
  --variants original,paraphrase,noise --repeats 3 --top-k 50
```

The historical runners did not fix sampling seeds or retain complete runtime
provenance. Fresh inference need not reproduce the saved responses bitwise.
Both cohorts use temperature 0.1 and top-p 1; ULT context is 4,096 tokens and
Similo context is 8,192 with at most 96 output tokens. The extension's initial
four-worker acquisition was resumed with one worker and grouped jobs. Its
timings are retained but excluded from cross-family efficiency claims.

Generated response text, request options, prompt hashes, token counts, and backend timings are retained. Unused runtime continuation-token arrays are omitted from the distributed responses.

## Interpretation boundaries

- Schema acceptance means the parser's operational checks. The ULT parser keeps
  up to five nonempty test strings and does not enforce the requested minimum
  of three tests or an assert-only grammar. Target-function matching is lexical.
  The Similo parser accepts its documented integer-recovery paths and does not
  validate every confidence/rationale field requested by the prompt.
- The historical condition names `paraphrase` and `noise` are retained as data
  keys. ULT uses fixed instruction suffixes; Similo replaces the instruction
  with a migration-intent reformulation or distractor warning. It does not add
  DOM distractors or produce independent task paraphrases.
- Reference correctness is separate from partial assertion success and
  mutation yield. Conditional mutation yield excludes unevaluable responses;
  unconditional yield uses every scheduled artifact–mutant pair.
- Cost is client-observed generation time, including queuing/loading, divided
  by the relevant outcomes. It excludes oracle execution and mutation cost.
  The gate is replayed after all calls; no early-stopping speedup is measured.
- The repository contains reproducibility code, configuration, retained model
  outputs, oracle evaluations, analysis results, and empirical display code.
  Manuscripts, correspondence, local notes, runtime caches, and build products are
  excluded.
