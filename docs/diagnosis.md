# Baseline diagnosis: fd and ripgrep

## Method and composition output

Analyzed the local cached checkouts at `out/.repo-cache/fd` and
`out/.repo-cache/ripgrep` with the unchanged analyzer, then composed anthem with
seed 42 and rendering disabled. The full emitted profiles are included below.

| Field | sharkdp/fd | BurntSushi/ripgrep | Comparison |
|---|---:|---:|---|
| Profile modules | 14 | 14 | Different module sets and names |
| Global LOC | 6,803 | 40,192 | ripgrep is 5.9× larger |
| Global avg complexity | 0.516084 | 0.625309 | Near-ish, same 0–1 rank scale |
| Proxy test coverage | 0.655172 | 0.975207 | Different, both reported as proxy |
| Unsafe ratio | 0.002674 | 0.001739 | Both very low |
| Key / mode | C / mixolydian | C / mixolydian | Identical |
| Tempo | 130 BPM | 133 BPM | Near (3 BPM) |
| Meter | 4/4 | 4/4 | Identical |
| Progression IDs | `mixolydian_p1,p3,p2,p2,p2,p1` | `mixolydian_p1,p3,p2,p2,p2,p1` | Identical in all six sections |
| Rhythm IDs | `offbeat_push,four_square,anthem_drive,anthem_drive,offbeat_push,stadium_stabs` | `offbeat_push,four_square,anthem_drive,anthem_drive,offbeat_push,stadium_stabs` | Identical in all six sections |
| Arrangement matrix | `a_hook` | `a_hook` | Identical, same roles in every section |
| VariationPlan fingerprint | identical (below) | identical (below) | Exact equality |
| Hook | module-name-derived violin motifs | module-name-derived violin motifs | No shared repo-level hook; no single signature |

### VariationPlan fingerprint (both runs)

`(p:intro:mixolydian_p1, p:theme:mixolydian_p3, p:development:mixolydian_p2, p:climax:mixolydian_p2, p:resolution:mixolydian_p2, p:outro:mixolydian_p1, r:intro:offbeat_push, r:theme:four_square, r:development:anthem_drive, r:climax:anthem_drive, r:resolution:offbeat_push, r:outro:stadium_stabs, v:open, b:gradual, t:0, m:a_hook, bp:root_hold, dg:anthem_four, mt:repeat, gp:29)`

### Arrangement matrix (both runs)

| Section | Piano | Bass | Drums | Violin | Guitar |
|---|---|---|---|---|---|
| intro | lead | out | out | out | out |
| theme | support | support | support | lead | out |
| development | support | support | support | lead | out |
| climax | support | support | support | support | lead |
| resolution | support | support | support | lead | out |
| outro | lead | out | out | out | out |

### Complete profiles

#### sharkdp/fd

```json
{
  "call_path": [
    "fd_find::bin_fd",
    "fd_find::walk",
    "fd_find::output",
    "fd_find::exec",
    "fd_find::exec::tests",
    "fd_find::exec",
    "fd_find::filesystem",
    "fd_find::dir_entry",
    "fd_find::other",
    "fd_find::fmt",
    "fd_find::cli",
    "fd_find::tests::testenv",
    "fd_find::tests::tests",
    "fd_find::filter::size::tests",
    "fd_find::filter::time::tests"
  ],
  "coverage_source": "proxy",
  "global": {
    "avg_complexity": 0.516084,
    "test_coverage": 0.655172,
    "total_loc": 6803,
    "unsafe_ratio": 0.002674
  },
  "modules": [
    {
      "complexity": 0.458132,
      "depended_by_count": 1,
      "depends_on": [
        "fd_find::other",
        "fd_find::filesystem"
      ],
      "loc": 648,
      "name": "fd_find::cli",
      "test_coverage": 0.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.397648,
      "depended_by_count": 3,
      "depends_on": [],
      "loc": 156,
      "name": "fd_find::dir_entry",
      "test_coverage": 0.4,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.785806,
      "depended_by_count": 3,
      "depends_on": [
        "fd_find::exec::tests"
      ],
      "loc": 355,
      "name": "fd_find::exec",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.341528,
      "depended_by_count": 4,
      "depends_on": [
        "fd_find::dir_entry"
      ],
      "loc": 124,
      "name": "fd_find::filesystem",
      "test_coverage": 0.125,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 1.0,
      "depended_by_count": 4,
      "depends_on": [
        "fd_find::fmt",
        "fd_find::dir_entry",
        "fd_find::filesystem"
      ],
      "loc": 865,
      "name": "fd_find::other",
      "test_coverage": 1.0,
      "todo_count": 1,
      "unsafe_count": 1
    },
    {
      "complexity": 0.717426,
      "depended_by_count": 2,
      "depends_on": [],
      "loc": 238,
      "name": "fd_find::fmt",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.852134,
      "depended_by_count": 0,
      "depends_on": [
        "fd_find::walk",
        "fd_find::filesystem",
        "fd_find::other",
        "fd_find::cli",
        "fd_find::dir_entry",
        "fd_find::exec",
        "fd_find::fmt",
        "fd_find::output"
      ],
      "loc": 436,
      "name": "fd_find::bin_fd",
      "test_coverage": 0.0,
      "todo_count": 1,
      "unsafe_count": 0
    },
    {
      "complexity": 0.57568,
      "depended_by_count": 2,
      "depends_on": [],
      "loc": 162,
      "name": "fd_find::output",
      "test_coverage": 0.0,
      "todo_count": 5,
      "unsafe_count": 0
    },
    {
      "complexity": 0.935928,
      "depended_by_count": 1,
      "depends_on": [
        "fd_find::output",
        "fd_find::exec",
        "fd_find::filesystem"
      ],
      "loc": 594,
      "name": "fd_find::walk",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.650449,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 265,
      "name": "fd_find::tests::testenv",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.510442,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 2524,
      "name": "fd_find::tests::tests",
      "test_coverage": 1.0,
      "todo_count": 6,
      "unsafe_count": 0
    },
    {
      "complexity": 0.0,
      "depended_by_count": 1,
      "depends_on": [
        "fd_find::exec"
      ],
      "loc": 182,
      "name": "fd_find::exec::tests",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.0,
      "depended_by_count": 0,
      "depends_on": [
        "fd_find::other"
      ],
      "loc": 130,
      "name": "fd_find::filter::size::tests",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.0,
      "depended_by_count": 0,
      "depends_on": [
        "fd_find::other"
      ],
      "loc": 124,
      "name": "fd_find::filter::time::tests",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    }
  ],
  "name": "diagnosis_fd"
}
```

#### BurntSushi/ripgrep

```json
{
  "call_path": [
    "ripgrep::other",
    "grep_cli::other",
    "ripgrep::flags::defs",
    "globset::other",
    "grep::other",
    "ignore::walk",
    "ignore::other",
    "ignore::walk",
    "grep_matcher::other",
    "grep_pcre2::other",
    "grep_printer::other",
    "grep_regex::other",
    "grep_searcher::other",
    "grep_searcher::searcher",
    "grep_searcher::other",
    "grep_printer::standard::tests"
  ],
  "coverage_source": "proxy",
  "global": {
    "avg_complexity": 0.625309,
    "test_coverage": 0.975207,
    "total_loc": 40192,
    "unsafe_ratio": 0.001739
  },
  "modules": [
    {
      "complexity": 0.520528,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 1119,
      "name": "grep_cli::other",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 2
    },
    {
      "complexity": 0.627264,
      "depended_by_count": 0,
      "depends_on": [
        "ripgrep::other"
      ],
      "loc": 6693,
      "name": "ripgrep::flags::defs",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.845758,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 2693,
      "name": "globset::other",
      "test_coverage": 1.0,
      "todo_count": 1,
      "unsafe_count": 0
    },
    {
      "complexity": 0.258252,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 79,
      "name": "grep::other",
      "test_coverage": 0.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.702504,
      "depended_by_count": 1,
      "depends_on": [
        "ignore::other"
      ],
      "loc": 1924,
      "name": "ignore::walk",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.459365,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 1325,
      "name": "grep_matcher::other",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.338737,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 318,
      "name": "grep_pcre2::other",
      "test_coverage": 0.363636,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.963132,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 4575,
      "name": "grep_printer::other",
      "test_coverage": 0.974359,
      "todo_count": 0,
      "unsafe_count": 0
    },
    {
      "complexity": 0.741458,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 1863,
      "name": "grep_regex::other",
      "test_coverage": 1.0,
      "todo_count": 3,
      "unsafe_count": 0
    },
    {
      "complexity": 0.586024,
      "depended_by_count": 1,
      "depends_on": [
        "grep_searcher::searcher"
      ],
      "loc": 3035,
      "name": "grep_searcher::other",
      "test_coverage": 1.0,
      "todo_count": 1,
      "unsafe_count": 0
    },
    {
      "complexity": 0.800626,
      "depended_by_count": 1,
      "depends_on": [
        "grep_searcher::other"
      ],
      "loc": 1597,
      "name": "grep_searcher::searcher",
      "test_coverage": 1.0,
      "todo_count": 1,
      "unsafe_count": 2
    },
    {
      "complexity": 1.0,
      "depended_by_count": 1,
      "depends_on": [],
      "loc": 7823,
      "name": "ripgrep::other",
      "test_coverage": 1.0,
      "todo_count": 2,
      "unsafe_count": 1
    },
    {
      "complexity": 0.910676,
      "depended_by_count": 1,
      "depends_on": [
        "ignore::walk"
      ],
      "loc": 5099,
      "name": "ignore::other",
      "test_coverage": 1.0,
      "todo_count": 2,
      "unsafe_count": 0
    },
    {
      "complexity": 0.0,
      "depended_by_count": 0,
      "depends_on": [],
      "loc": 2049,
      "name": "grep_printer::standard::tests",
      "test_coverage": 1.0,
      "todo_count": 0,
      "unsafe_count": 0
    }
  ],
  "name": "diagnosis_ripgrep"
}
```

## Suspected causes

| Cause | Finding |
|---|---|
| a) Global metrics rank-normalized | **Confirmed for complexity, partially.** Module complexity is ranked and rescaled within each repository; global `avg_complexity` averages those within-repo values. Thus the numbers lose an absolute complexity baseline. LOC, unsafe ratio, and coverage are not rank-normalized. |
| b) Root key always C | **Rejected literally; confirmed for this pair.** `COMMON_ROOTS` contains seven curated roots `(C,D,E,F,G,A,Bb)`, not all twelve. With seed 42 both plans select C. The code does not force C, but the root set is narrower than requested. |
| c) Plan sampled from `--seed` alone | **Confirmed for arrangement sampling.** Both profiles select the same `majorish` family for anthem, then `random.Random(42)` samples the same options. Profile metrics still influence mode family and form pacing/tempo, explaining 130 vs 133 BPM and different section sizes. |
| d) Coarse mode and tempo mapping | **Confirmed.** Health thresholds choose three families; anthem's bright-family setting forces `majorish`. Anthem tempo is confined to 120–140 BPM and maps the normalized complexity linearly into that band. Both repos therefore land near one another. |
| e) No repo-specific signature or Rust-specific features | **Confirmed.** There is no repo fingerprint, global hook, or Rust feature set. Existing violin motifs are stable hashes of individual module names, so they vary by module but do not establish an audible identity for each repository. |

The strongest immediate explanation is identical seeded arrangement sampling
combined with the same style/mode family and near tempos. Repo size changes form
pacing and module assignments, but does not change the sampled plan or provide a
recognizable signature. Steps 3–5 address those causes in that order.
