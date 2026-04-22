# ASPLOS'27 Reviewer Scripts

Scripts for processing reviewer data for the ASPLOS 2027 conference.

## Setup

1. Clone the repository
2. Export required csv's from HotCRP intothe `from-hotcrp` directory:
   - `<conference_name>-authors.csv` _(select all papers then Download Authors)_
   - `<conference_name>-pcconflicts.csv` _(select all papers then Download PC Conflicts)_
   - `<conference_name>-pcinfo.csv` _(users, Program Committee, View options, check    - `<conference_name>-topics.csv` _(select all papers then Download PC Topics)_
'Tags' and 'Topics' the Download, PC Info)_
5. Add the tpms scores into the `from-tpms` directory as csv:
  - asplos27_scores.csv
6. Add PC demographics (exported from PC Chair's spreadsheets) into the `from-sheets` directory as csv:
  - demographics.csv, with columns: first,last,email,gender,country,field,seniority

## Run scripts

1. Run the `run_pipeline.sh` script (this will run all the scripts in the correct order, generating two sorts of output:
  - files for upload to hotcrp in `data/to-hotcrp`
  - various analyses which may be uploaded to a spreadsheet, in `data/*.csv`

## Upload to HotCRP

1. Upload pc assignments from `data/to-hotcrp/asplos27-apr-pc-assignments.csv` (Assignments/Bulk update)
2. Upload vc assignments from `data/to-hotcrp/asplos27-apr-vc-assignments.csv` (Assignments/Bulk update)
3. Upload reviewer scores from `data/to-hotcrp/asplos27-apr-preferences.csv`(Assignments/Bulk update)
4. Upload paper tags from `data/to-hotcrp/asplos27-apr-papertags.csv` (Assignments/Bulk update)


## Administrator Assignments

The current script for administrator assignments (`assign_admins.py`) is very ad hoc, so should be modified by hand or re-written as necessary.

