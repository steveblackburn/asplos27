# Reviews Analysis

This directory contains scripts to analyze reviews for ASPLOS '27.

## Scripts

### `analyze\_reviews.py`

Analyzes reviewer statistics by combining review data with TPMS scores and combined scores.

**Usage:**
Run from the `reviews/` directory:
```bash
python3 analyze\_reviews.py
```

**Inputs:**
- `data/from-hotcrp/asplos27-apr-reviews.csv`
- `../assignments/data/from-tpms/asplos27\_scores.csv`
- `../assignments/data/paper-reviewer-combined-scores.csv`

**Outputs:**
- `data/analysis/reviewer-stats.csv`

### `analyze\_papers.py`

Analyzes paper statistics, computing averages and weighted averages for various scores.

**Usage:**
Run from the `reviews/` directory:
```bash
python3 analyze\_papers.py
```

**Inputs:**
- `data/from-hotcrp/asplos27-apr-reviews.csv`
- `../assignments/data/paper-reviewer-combined-scores.csv`

**Outputs:**
- `data/analysis/paper-stats.csv`

## Score Calculation

The `score` column in `paper-stats.csv` is a combined metric used to rank papers. It is calculated as a weighted average of two ranks:

$$Score = \text{round}\left(\frac{2}{3} \times \text{rank\_overall} + \frac{1}{3} \times \text{rank\_asplos}\right)$$

Where:
- **`rank\_overall`**: The paper's rank (on a scale of 1 to 100) based on its weighted average score for "Overall Strong ASPLOS paper" (`wavg\_overall`).
- **`rank\_asplos`**: The paper's rank (on a scale of 1 to 100) based on its weighted `wavg\_asplos` score.
- **`avg\_asplos`**: For each review, we take the average of the best two scores among the four advancement categories ("Advances computer architecture research", "Advances programming languages research", "Advances operating systems research", and "Introduces new area"). We then average these reviewer scores for the paper.

Ranks are dense ranks scaled to a 1-100 range, where the highest score gets 100 and the lowest gets 1.
