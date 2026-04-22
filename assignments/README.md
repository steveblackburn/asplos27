# ASPLOS'27 Reviewer Scripts

Scripts for processing reviewer data for the ASPLOS 2027 conference.

## Setup

1. Clone the repository
2. Create a `data` directory
3. Create a `data/from-hotcrp` subdirectory
4. Export required csv's from HotCRP intothe `from-hotcrp` directory:
   - `<conference_name>-pcconflicts.csv` _(select all papers then Download PC Conflicts)_
   - `<conference_name>-topics.csv` _(select all papers then Download PC Topics)_
   - `<conference_name>-authors.csv` _(select all papers then Download Authors)_
   - `<conference_name>-pcinfo.csv` _(users, Program Committee, View options, check 'Tags' and 'Topics' the Download, PC Info)_
5. Add the tpms scores into the `from-tpms` directory as csv.

## Preliminaries

1. Generate topic scores with the `generate_topic_scores.py` script (this will produce scores per-reviewer-per-paper based on paper topics and reviewer topic scores)
2. Generate combined scores with the `combine_scores.py` script (this will combine topic scores and tpms scores into a single per-reviewer-per-paper expertise score)
3. Summarize scores using the `analyze_scores.py` script (this will produce per-paper score statistics in `data/paper_stats.csv` prior to review assignments, permitting an analysis of how well the reviewer pool supports each paper).

## Generate Assignments

1. Run the `assign_reviewers.py` script (this will produce a reviewer assignment)

## Upload to HotCRP

1. Upload pc assignments from `data/to-hotcrp/asplos27-apr-pc-assignments.csv` (Assignments/Bulk update)
2. Upload vc assignments from `data/to-hotcrp/asplos27-apr-vc-assignments.csv` (Assignments/Bulk update)
3. Upload reviewer scores from `data/to-hotcrp/asplos27-apr-preferences.csv`(Assignments/Bulk update)
4. Upload paper tags from `data/to-hotcrp/asplos27-apr-papertags.csv` (Assignments/Bulk update)

