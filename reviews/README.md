# Reviews Analysis

This directory contains scripts to analyze reviews for ASPLOS '27.

## Scripts

### `analyze_reviews.py`

Analyzes reviewer statistics by combining review data with TPMS scores and combined scores.

**Usage:**
Run from the `reviews/` directory:
```bash
python3 analyze_reviews.py
```

**Inputs:**
- `data/from-hotcrp/asplos27-apr-reviews.csv`
- `../assignments/data/from-tpms/asplos27_scores.csv`
- `../assignments/data/paper-reviewer-combined-scores.csv`

**Outputs:**
- `data/analysis/reviewer-stats.csv`

### `analyze_papers.py`

Analyzes paper statistics, computing averages and weighted averages for various scores.

**Usage:**
Run from the `reviews/` directory:
```bash
python3 analyze_papers.py
```

**Inputs:**
- `data/from-hotcrp/asplos27-apr-reviews.csv`
- `../assignments/data/paper-reviewer-combined-scores.csv`

**Outputs:**
- `data/analysis/paper-stats.csv`

### `analyze_topics.py`

Analyzes review statistics by topic.

**Usage:**
Run from the `reviews/` directory:
```bash
python3 analyze_topics.py
```

**Inputs:**
- `../assignments/data/from-hotcrp/asplos27-apr-topics.csv`
- `../assignments/data/to-hotcrp/asplos27-apr-pc-assignments.csv`
- `../assignments/data/from-tpms/asplos27_scores.csv`
- `data/from-hotcrp/asplos27-apr-reviews.csv`
- `data/analysis/paper-stats.csv`

**Outputs:**
- `data/analysis/topic-review-stats.csv`


## Score Calculation

The `pct` column in `paper-stats.csv` is a combined metric used to rank papers. It is calculated as a weighted average of two percentile ranks:

$$pct = \frac{2}{3} \times \text{rank}_{\text{overall}} + \frac{1}{3} \times \text{rank}_{\text{asplos}}$$

Where:
- **`rank_overall`**: The paper's percentile rank (on a scale of 1 to 100) based on its weighted average score for "Overall Strong ASPLOS paper" (`wavg_overall`).
- **`rank_asplos`**: The paper's percentile rank (on a scale of 1 to 100) based on its weighted `wavg_asplos` score.
- **`avg_asplos`**: For each review, we take the average of the best two scores among the four advancement categories ("Advances computer architecture research", "Advances programming languages research", "Advances operating systems research", and "Introduces new area"). We then average these reviewer scores for the paper.

Percentiles are computed based on the proportion of papers falling below or at a given score. To handle ties gracefully and ensure that bins are centered, we use the midpoint of the range of positions for tied scores: `midpoint = count_lt + (count_eq + 1) / 2`. This ensures that large bins or empty bins in the distribution are strictly caused by actual score ties.

The final tag uploaded to HotCRP is `pctl`, which holds the integer percentile rank computed from the `pct` score.
