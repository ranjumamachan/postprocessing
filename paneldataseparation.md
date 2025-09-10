# IV Curve Data Processor (`paneldataseparation.py`)

This script processes IV (current-voltage) curve data files containing measurements from multiple solar cell samples. It allows users to separate the data into "Modified" and "Unmodified" sample groups, export the results to Excel-compatible CSV files, and perform graphical analysis of key solar cell parameters.

---

## Features

- **Flexible IV Curve Parsing:** Supports files with metadata, multiple samples, and variable formatting.
- **Key Parameter Extraction:** Automatically extracts open-circuit voltage (VOC), short-circuit current (ISC), maximum power (PMAX), and fill factor (FF) for each sample.
- **Sample Grouping:** Lets users interactively select which samples are "Modified" and which are "Unmodified".
- **Excel-Compatible Output:** Saves separated samples into UTF-8 BOM CSV files for easy opening in Excel.
- **Graphical Analysis:** Plots VOC, ISC, PMAX, and FF versus time for both groups.
- **User-Friendly CLI:** Guides the user through file selection, sample grouping, and error handling.

---

## How It Works

### 1. **Input**

- **IV Curve Data File:**  
  - Plain text file containing measurements from one or more samples.
  - Each sample should start with a "Sample No." or similar identifier.
  - Each sample section contains metadata (e.g., "Sample No.", "Date & Time") and a table of IV data (columns like "V (V)", "I (A)", "P (W)").
- **User Input (CLI Prompts):**
  - Path to the IV curve data file.
  - Selection of "Modified" sample numbers (e.g., `1,2,5-7`).
  - Selection of "Unmodified" sample numbers (e.g., `3,4,8-10`).
  - Option to continue if overlapping samples are selected for both groups.

### 2. **Processing**

- **Parsing:**  
  The script splits the file into samples, extracts metadata and IV data, and converts the data table into a pandas DataFrame.
- **Parameter Extraction:**  
  For each sample, the script computes VOC, ISC, PMAX, and FF, either from metadata or directly from the IV data.
- **Sample Grouping:**  
  User selects which samples are "Modified" and which are "Unmodified". The script warns about overlaps.
- **File Output:**  
  Each group is saved in a separate CSV file with metadata and IV data formatted for Excel.
- **Plotting:**  
  The script generates time-series plots for VOC, ISC, PMAX, and FF for each group.

### 3. **Output**

- **CSV Files:**  
  - `<input>_Modified.csv` — Contains all selected "Modified" samples.
  - `<input>_Unmodified.csv` — Contains all selected "Unmodified" samples.
  - If files already exist, appends `_1`, `_2`, etc. to avoid overwriting.
- **Plots:**  
  - Four plots per group, showing VOC, ISC, PMAX, and FF vs. time.
- **Console Output:**  
  - Summary table of extracted parameters per sample.
  - Guidance and error messages as needed.

---

## Example Usage

```sh
$ python paneldataseparation.py
IV Curve Data Processor with Graphical Analysis
---------------------------------------------
Enter path to your IV curve data file: mydata.txt

Extracted Parameters:
  timestamp     Sample No  VOC   ISC  PMAX    FF
2022-09-01 12:00       1   0.6  0.03  0.014  0.78
...

Found 6 samples:
1. Sample 1 - 01-09-2022 12:00
2. Sample 2 - 01-09-2022 12:15
...

Enter sample numbers for MODIFIED samples (comma/range format, e.g., 1,3,5-10): 1,2,3
Enter sample numbers for UNMODIFIED samples (comma/range format, e.g., 2,4,6-8): 4-6

Processing successful!
Modified samples saved to: mydata_Modified.csv
Unmodified samples saved to: mydata_Unmodified.csv

Plotting Modified Samples...
Plotting Unmodified Samples...
```

---

## Input Details

- **Data File:** Text file with sections per sample, each containing metadata lines and a table of IV data.
- **Sample Selection:** User enters sample numbers as comma-separated list or ranges (e.g., `1,3,5-8`).

## Output Details

- **CSV Files:** Each file contains metadata as key-value pairs and IV data as tables for each sample, separated by blank lines.
- **Plots:** Four time-series plots per group, displayed using matplotlib.

---

## Requirements

- Python 3
- pandas
- numpy
- matplotlib

Install requirements with:
```sh
pip install pandas numpy matplotlib
```

---

## Notes

- The script is CLI-driven and interactive.
- Designed for files containing multiple samples in a single text file with consistent formatting.
- Handles some variations in sample section headers (e.g., "Sample No.", "Sample: 1", etc.).
- Outputs are Excel-friendly.

---

**Author:** [ranjumamachan](https://github.com/ranjumamachan)
