# IV Curve Panel Splitter – Batch Processor with Irradiance Averaging

A robust, interactive Python tool for parsing photovoltaic (PV) IV‑curve CSV files, splitting samples into two user‑defined panels, and collecting triple‑averaged irradiance readings. It is designed for research and quality‑control workflows where multiple measurement files must be aggregated into clean, analysis‑ready spreadsheets.

---

## ✨ Key Features

- **Rock‑solid CSV parsing** – handles both quoted (old instruments) and unquoted (new instruments) formats; gracefully tolerates `-------` placeholders and trailing commas.
- **Batch processing** – load multiple CSV files in a single session; all data is accumulated and written to **two final output files** at the end.
- **Panel separation** – interactively select sample numbers (e.g. `1,3,5-10` or `all`) for **Panel 1** and **Panel 2**; warns if a sample is assigned to both.
- **Triple‑irradiance averaging** – for each selected sample, enter **three** W/m² readings; the tool computes and stores only the **average**, reducing measurement noise.
- **Never drops samples** – even if you skip the irradiance entry (press Enter), the sample is still included in the output with a blank `irradiance` cell.
- **One‑click output** – after processing all files, saves `Combined_Panel1.xlsx` and `Combined_Panel2.xlsx` (falls back to `.csv` if `openpyxl` is unavailable).

---

## 🧠 How It Works (Step‑by‑Step)

1. **Launch** the script.
2. **Provide the path** to your first `.csv` IV‑curve file (drag‑and‑drop works on Windows).
3. The parser reads the file, extracts **metadata only** (Sample No., Date/Time, Voc, Vmpp, Impp, Pmax) and displays a clean table.
4. **Select sample numbers** for Panel 1.
5. **Select sample numbers** for Panel 2.
6. For **each** selected sample, enter **three** irradiance values (W/m²) separated by commas, e.g. `850, 860, 855`. The script calculates and saves the average.
   - *Tip:* Press `Enter` without typing to keep the sample but leave the irradiance blank.
7. When the file is done, you are asked: *“Load another CSV file?”*
   - Reply `y` to process another file (all data accumulates).
   - Reply `n` to finish.
8. At the end, **two combined Excel files** are saved in the same folder as your first input file.

---

## 📥 Input Format (CSV)

The parser expects a standard IV‑tracer export with blocks starting with:

```csv
Sample No.,1,
Date & Time ,10-05-2025 12:33,
Vopen (V) ,22.08,
Vmaxp (V),14.94,
Imaxp (A),1.757,
Pmax (W),26.27,
V (V),I (A),P (W)
...

##


📤 Output Format
The final output files (Combined_Panel1.xlsx and Combined_Panel2.xlsx) contain the following columns:

Column	Description
sample_no	Sample number as read from the CSV
date_time	Date and time of the measurement
source_file	Original CSV filename (useful for traceability)
Voc (V)	Open‑circuit voltage
Vmpp (V)	Voltage at maximum power point
Impp (A)	Current at maximum power point
Pmax (W)	Maximum power (calculated if missing)
irradiance	Averaged W/m² (blank if skipped)
The raw voltage/current data points are discarded – only the summary parameters are kept, keeping the output lean and ready for statistical post‑processing.
