# 📊 Panel Temperature Comparison Tool – Version 2 (Advanced)

**Dumb‑person‑friendly guide** – no coding skills needed.  
This script automatically finds and cleans temperature data from multiple Excel files, compares two panels of sensors, and tells you **if** and **how** they differ.

---

## 🔧 What does this script do?

1. **Reads all Excel files** in a folder that match a date pattern (e.g., `19-06-2026 *.xlsx`).  
2. **Cleans the data** in three steps:  
   - Removes readings outside the physical range **30–85 °C** (sensor faults).  
   - Removes **outliers** per panel using an IQR (Inter‑Quartile Range) filter – each panel’s channels are judged against their own distribution.  
   - Checks that the difference between the two panel averages is physically plausible (you can set a window, e.g., `[-15, 15]` °C).  
3. **Averages** the channels for Panel 1 (channels 3,4,5,7) and Panel 2 (channels 9,10,11,12).  
4. **Runs statistics**:  
   - Newey‑West t‑test (handles time‑series correlation).  
   - Effect size (Cohen’s d) – tells you *how large* the difference is.  
   - Time trend regression – checks if the gap changes over time.  
5. **Saves**:
   - Several **plots** (averages, difference, per‑channel before/after, histogram).  
   - A **CSV** with the cleaned averages.  
   - A **detailed text report** with all cleaning steps and statistical results.

---

## 📂 Inputs – what you need

### Folder structure
- Place all your Excel files for one date in a **single folder**.  
- Each Excel file must have columns named:  
  - `Date:` (format `dd-mm-yyyy`)  
  - `Time:` (format `HH:MM:SS`)  
  - `Channel - 3`, `Channel - 4`, … `Channel - 12` (temperature readings in °C).  

### File naming
The script looks for files named like:  
`19-06-2026 anything.xlsx` (the date you enter, then a space, then anything).  
Case‑insensitive, so `19-06-2026 data.xlsx` works.

### Channels
- **Panel 1 (unmodified)**: channels `3,4,5,7`  
- **Panel 2 (cooled/experimental)**: channels `9,10,11,12`  
You can change these at the top of the script if needed.

---

## 🖥️ How to run it

### 1. Install Python packages
Open a command prompt/terminal and run:

```bash
pip install pandas matplotlib openpyxl statsmodels scipy numpy
```

### 2. Save the script
Copy the entire script (the long one) into a file named `panel_compare_v2.py` on your computer.

### 3. Run the script
```bash
python panel_compare_v2.py
```

### 4. Answer the prompts
- **Enter date (dd-mm-yyyy):** Type the date, e.g., `19-06-2026`.  
- **Enter input folder path:** Drag and drop the folder containing your Excel files, or type the full path.  
- **Enter output folder path:** Where you want all results saved (will be created if it doesn’t exist).

The script will then process all matching files and generate outputs.

---

## 📤 Outputs – what you get

All outputs are saved in the **output folder** you specified.

### 📄 Text report: `statistical_comparison.txt`
This is your **master report**. It contains:
- How many outliers were removed **per channel** and their values.  
- Which timestamps were flagged by the cross‑panel difference check.  
- **Final statistical results** (mean difference, t‑test, p‑value, effect size, time trend).  
- A plain‑English conclusion.

**You can share this file with anyone – it explains everything.**

### 📈 Plots (PNG images)
| File name | What it shows |
|-----------|---------------|
| `outlier_per_channel.png` | Each channel’s raw data (red) and cleaned data (blue) – you can see exactly which points were removed. |
| `temperature_difference.png` | Panel 1 minus Panel 2 over time. Grey = before cross‑panel check, blue = after all filters. The green band shows your expected window. |
| `temperature_average_comparison.png` | The average temperatures of both panels over time – the main comparison plot. |
| `difference_distribution.png` | Histogram of all differences – shows the spread and whether it’s centred around zero. |

### 📊 CSV data: `temperature_averages.csv`
Columns: `DateTime`, `Panel_1_Avg`, `Panel_2_Avg`, `Diff` (cleaned data, after all filters).  
You can open this in Excel for your own analyses.

---

## ⚙️ Configuration – you can change these numbers

At the very top of the script there are **constants** you can tweak:

```python
LOWER_THRESHOLD = 30      # minimum physically possible temperature (°C)
UPPER_THRESHOLD = 85      # maximum physically possible temperature (°C)
IQR_MULTIPLIER = 2.5      # outlier strictness (higher = less aggressive)
DIFF_LOW  = -15.0         # minimum allowed (Panel1 - Panel2) difference
DIFF_HIGH =  15.0         # maximum allowed (Panel1 - Panel2) difference
NW_LAGS = 1               # Newey-West lag (leave as 1)
```

**What to change:**
- If your experiment operates at different temperatures, adjust `LOWER_THRESHOLD` / `UPPER_THRESHOLD`.  
- If you want to remove more or fewer outliers, change `IQR_MULTIPLIER` (typical range 1.5–3.0).  
- **Most important:** Set `DIFF_LOW` and `DIFF_HIGH` to a **wide enough range** that your true difference can fit. Since we don’t know which panel is warmer, setting `-15` to `+15` is safe for most experiments. Never set `DIFF_LOW = 0` unless you are **certain** Panel 1 is always warmer.

---

## 📖 Understanding the statistical output

After the script finishes, the text report will show:

- **Mean difference (P1 - P2):** Positive = Panel 1 hotter; negative = Panel 2 hotter.  
- **Newey‑West t‑test:** Tests if the mean difference is **significantly different from zero**.  
  - p‑value < 0.05 → **statistically significant** (almost certainly a real difference).  
- **Cohen’s d (effect size):** Tells you **how large** the difference is in practical terms:  
  - `|d| < 0.2` → negligible  
  - `0.2–0.5` → small  
  - `0.5–0.8` → medium  
  - `> 0.8` → large  
- **Time trend:** If the p‑value for time is < 0.05, the difference is changing over time. The coefficient tells you the rate of change (positive = gap growing).

---

## ❓ FAQ (Dumb questions welcome)

**Q: I have more than two panels – can I use this?**  
A: Not directly – you’d need to modify the `CHANNELS` lists to add more panels. But if you only have two, this works.

**Q: My Excel files have different column names – what do I do?**  
A: The script expects exactly `Date:`, `Time:`, and `Channel - X`. If yours are different, you’ll need to rename them or edit the script.

**Q: The script says “No files found” – what now?**  
A: Check that your folder path is correct and that your file names match the pattern, e.g., `19-06-2026 anything.xlsx`. The date you enter must match the start of the filenames.

**Q: Can I run this on a Mac or Linux?**  
A: Yes – Python works the same. Just make sure you have the packages installed.

**Q: I don’t want the IQR cleaning – can I turn it off?**  
A: Set `IQR_MULTIPLIER = 999` – it will then remove almost nothing.

**Q: What if my true difference is bigger than 15 °C?**  
A: Change `DIFF_HIGH` to, say, `30` or `50`. The window should cover your expected maximum gap.

---

## 📁 GitHub-friendly copy

You can copy‑paste the code from the previous message into a file named `panel_compare_v2.py`.  
For a GitHub repository, include this README.md file alongside it.  

**Repository structure suggestion:**
```
panel-temperature-comparison/
├── panel_compare_v2.py
├── README.md          (this file)
└── example_outputs/   (optional – show sample plots)
```

---

## 🧠 Final words

This script is designed to be **run and forget** – it gives you a complete audit trail of what it did to your data and a clear statistical verdict.  
If you ever forget how it works, just read this guide. And if something breaks, check the configuration constants first – 9 times out of 10, it’s a threshold that’s too tight.

**Happy temperature‑comparing!** 🌡️
