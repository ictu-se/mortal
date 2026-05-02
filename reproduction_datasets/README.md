# External Dataset Placement

This directory is intentionally empty in the GitHub-ready artifact.

Place external datasets here before rerunning local LLM calls or mutation
analysis:

```text
reproduction_datasets/
├── UnLeakedTestBench/
│   └── datasets/
│       └── ULT_Lite.jsonl
└── SimiloLLM/
    ├── old.txt
    ├── new.txt
    └── oracles.txt
```

The artifact includes frozen raw model outputs under `pilot_outputs/`, so most
aggregate analyses can be reproduced without downloading these datasets.

