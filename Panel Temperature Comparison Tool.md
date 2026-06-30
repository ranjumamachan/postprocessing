

A comprehensive Python script for analysing temperature data from two panels of sensors. This tool performs multi-stage cleaning, statistical analysis, uncertainty quantification, and sensitivity analysis to determine whether two panels have a meaningful temperature difference.

---

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Input Requirements](#input-requirements)
- [Output Files](#output-files)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Interpreting the Outputs](#interpreting-the-outputs)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## 🔍 Overview

This script reads temperature data from multiple Excel files, applies **five layers of cleaning**, calculates **panel averages**, and performs **rigorous statistical analysis** to determine:

1. **Is there a temperature difference between the two panels?**
2. **How large is the difference?** (with confidence intervals)
3. **Is the difference consistent over time?**
4. **How reliable is the data?** (uncertainty quantification)
5. **How sensitive is the result to the cleaning thresholds?** (sensitivity analysis)

The script is designed for **experimental data** where sensors may have:
- Intermittent connections (sensor dropouts and reconnections)
- Sensor disagreement (one sensor reading differently from others)
- Physical outliers (impossible temperature values)
- Time-dependent behaviour (morning vs afternoon differences)

---

## ✨ Features

### Data Cleaning (5 Layers)
1. **Hard Limits** – Remove readings outside physical range (30–85 °C).
2. **Lag Correction** – Detect reconnecting sensors and exclude their recovery period.
3. **Cluster Filter** – Drop sensors that disagree with their peers at a single timestamp.
4. **Per‑Panel IQR Filter** (optional) – Remove global outliers per panel.
5. **Cross‑Panel Difference Check** – Flag physically impossible panel differences.

### Statistical Analysis
- **Newey‑West t‑test** – Handles autocorrelation in time‑series data.
- **Effect Size (Cohen's d)** – Distinguishes statistical from practical significance.
- **Time Trend Regression** – Checks if the difference changes over time.
- **Uncertainty Quantification** – Calculates instantaneous uncertainty (SEM) and overall uncertainty (HAC standard error).
- **95% Confidence Intervals** – For the mean temperature difference.

### Sensitivity Analysis
- **Sensitivity Curve** – Shows how the result changes with the SD threshold.
- **Temporal Coverage Heatmap** – Reveals if cleaning biases specific times of day.
- **Active Hours Coverage** – Quantifies data retention across the experimental period.
- **Hour‑by‑Hour Retention** – Identifies which hours survive the filter.

### Visualisations
- **Panel Average** – Colour‑coded by data quality status.
- **Temperature Difference** – Over time with mean line.
- **Difference Distribution** – Histogram and KDE.
- **Channel Detail** – Individual sensor readings vs panel average.
- **Smooth Time Series** – Rolling average for trend visualisation.
- **Scatter Diagnostic** – Difference vs sensor spread.
- **Sensitivity Curve** – Mean diff and data retention vs threshold.
- **Temporal Coverage Heatmap** – Time of day vs threshold.
- **Active Hours Coverage** – Hour count vs threshold.
- **Hour‑by‑Hour Retention** – Percentage retained per hour.

---

## 📂 Input Requirements

### Folder Structure
- Place all Excel files for **one date** in a **single folder**.
- The script will process **all matching files** in that folder.

### File Naming Convention
Files **must** match the pattern:
```
DD-MM-YYYY *.xlsx
```
Example:
```
25-06-2026 data1.xlsx
25-06-2026 data2.xlsx
25-06-2026 experiment.xlsx
```

### Excel File Format
Each Excel file must have the following columns:
- **`Date:`** – Date in `dd-mm-yyyy` format (e.g., `25-06-2026`)
- **`Time:`** – Time in `HH:MM:SS` format (e.g., `14:30:05`)
- **`Channel - 3`** – Temperature reading for sensor 3 (°C)
- **`Channel - 4`** – Temperature reading for sensor 4 (°C)
- **`Channel - 5`** – Temperature reading for sensor 5 (°C)
- **`Channel - 7`** – Temperature reading for sensor 7 (°C)
- **`Channel - 9`** – Temperature reading for sensor 9 (°C)
- **`Channel - 10`** – Temperature reading for sensor 10 (°C)
- **`Channel - 11`** – Temperature reading for sensor 11 (°C)
- **`Channel - 12`** – Temperature reading for sensor 12 (°C)

> **Note:** Channel numbers 3, 4, 5, 7 form **Panel 1**; channels 9, 10, 11, 12 form **Panel 2**.

---

## 📤 Output Files

All outputs are saved to the **output folder** you specify.

### Text Reports
| File | Description |
| :--- | :--- |
| `statistical_comparison.txt` | **Complete report** – cleaning summary, statistical results, confidence intervals, and conclusion. |
| `continuous_runs_p2_colder.txt` | List of continuous periods where Panel 2 was colder (with run lengths). |
| `continuous_runs_p1_colder.txt` | List of continuous periods where Panel 1 was colder. |
| `continuous_runs_p2_colder.csv` | **Detailed run data** – timestamps, lengths, and quality flags for Panel 2 colder periods. |
| `continuous_runs_p1_colder.csv` | **Detailed run data** – timestamps, lengths, and quality flags for Panel 1 colder periods. |

### CSV Data
| File | Description |
| :--- | :--- |
| `temperature_averages.csv` | **Cleaned data** – every timestamp with panel averages, standard deviations, active sensor counts, SEM, and statuses. |

### Visualisations (PNG)
| File | Description |
| :--- | :--- |
| `panel_averages_colour_coded.png` | Panel averages colour‑coded by data quality (blue = all OK, orange = one dropped, green = 2 sensors, red = dropped). |
| `temperature_difference.png` | Difference (P1 − P2) over time with mean line. |
| `difference_distribution.png` | Histogram and KDE of all differences. |
| `channels_vs_panel_average.png` | Individual sensor readings vs panel average. |
| `temperature_diff_vs_spread_smooth.png` | Smoothed difference vs sensor spread (with 60‑point rolling average). |
| `diff_vs_spread_scatter.png` | Scatter plot of difference vs maximum sensor spread. |
| `sensitivity_curve.png` | **KEY PLOT** – How mean diff and data retention change with the SD threshold. |
| `temporal_coverage_heatmap.png` | Heatmap showing which times of day survive at each threshold. |
| `active_hours_coverage.png` | Number of active half‑hour bins as threshold changes. |
| `hour_by_hour_retention.png` | Percentage of timestamps retained per hour at current threshold. |

---

## ⚙️ How It Works

### The Data Pipeline

```
Excel Files
    ↓
1. Hard Limits (30–85 °C)
    ↓
2. Lag Correction (Reconnecting sensors excluded)
    ↓
3. Cluster Filter (Sensors that disagree are dropped)
    ↓
4. Panel Averages & Uncertainty (Std, N, SEM)
    ↓
5. Statistical Analysis (t‑test, CI, effect size)
    ↓
6. Run Analysis (Continuous periods where one panel is colder)
    ↓
7. Sensitivity Analysis (How threshold affects result)
    ↓
8. Visualisations & Reports
```

### Cleaning Logic Explained

#### 1. Hard Limits
Readings outside `[30, 85] °C` are set to `NaN` (deleted) because they are physically impossible.

#### 2. Lag Correction
When a sensor reconnects after being missing, it often reads incorrectly for a few seconds. The script:
- Detects `NaN → valid` transitions.
- Checks if the sensor is far from the panel median.
- If it converges towards the median over 5 steps, those recovery readings are excluded.

#### 3. Cluster Filter
At each timestamp:
- **4 sensors active** – keep all if spread ≤ 6.0 °C; else drop one if exactly 3 agree.
- **3 sensors active** – keep all if spread ≤ 6.0 °C; else drop timestamp.
- **2 sensors active** – keep both if difference ≤ 4.0 °C; else drop timestamp.
- **< 2 sensors active** – drop timestamp.

#### 4. Uncertainty
For each timestamp, the script calculates:
- **Standard Deviation** – how much the sensors disagree.
- **N** – number of active sensors (2, 3, or 4).
- **SEM** – standard error of the mean = `Std / sqrt(N)`.

#### 5. Statistical Tests
- **Newey‑West t‑test** – accounts for autocorrelation (time‑series correlation).
- **Effect Size (Cohen's d)** – large (>0.8), medium (0.5–0.8), small (0.2–0.5), negligible (<0.2).
- **Time Trend** – linear regression of difference against time.

#### 6. Sensitivity Analysis
- **SD Threshold** – controls how conservative you want to be.
- **Sensitivity Curve** – shows how mean diff changes with threshold.
- **Temporal Coverage** – ensures the threshold doesn't bias specific times of day.

---

## 🔧 Configuration

All configurable parameters are at the top of the script:

```python
LOWER_THRESHOLD  = 30     # °C — hard physical lower limit
UPPER_THRESHOLD  = 85     # °C — hard physical upper limit
MAX_SPREAD_4     = 6.0    # °C — max spread for 3-4 sensors
MAX_SPREAD_2     = 4.0    # °C — max spread for exactly 2 sensors
LAG_WINDOW       = 5      # steps to look ahead for sensor recovery
LAG_THRESHOLD    = 1.5    # °C — reconnection detection threshold
NW_LAGS          = 1      # Newey‑West autocorrelation lags
```

### What to Change

| Parameter | Effect of increasing | Effect of decreasing |
| :--- | :--- | :--- |
| `MAX_SPREAD_4` | Keeps more data (liberal) | Drops more data (conservative) |
| `MAX_SPREAD_2` | Keeps more 2‑sensor timestamps | Drops more 2‑sensor timestamps |
| `LAG_THRESHOLD` | Catches fewer lags | Catches more lags (aggressive) |
| `LAG_WINDOW` | Looks further ahead for convergence | Looks shorter ahead |

### The "Dial" – SD Threshold

The `flag_noisy_runs()` function uses **1.5 °C** as the default threshold for flagging runs. This is **not** a hard filter – it's a diagnostic flag. However, you can use the **Sensitivity Curve** to choose a threshold that balances data retention and signal stability.

---

## 📊 Interpreting the Outputs

### The Statistical Report (`statistical_comparison.txt`)

```
DESCRIPTIVE STATISTICS:
  Mean difference (P1 - P2): -2.135 °C
  Panel 2 is WARMER than Panel 1 by 2.135 °C on average.

UNCERTAINTY:
  Instantaneous uncertainty (average SEM):
    Panel 1: ±0.669 °C
    Panel 2: ±0.641 °C
  Overall uncertainty (Newey-West HAC standard error): ±0.0147 °C
  95% Confidence Interval: [-0.5660, -0.5083] °C

INFERENTIAL STATISTICS:
  t-statistic = -36.4734
  p-value = 0.000000
  Reject H0 at alpha = 0.05.

CONCLUSION:
  Statistically and practically meaningful temperature difference.
```

### Key Takeaways

| Metric | What it means |
| :--- | :--- |
| **Mean Difference** | The average temperature difference (P1 − P2). Positive = P1 warmer; negative = P2 warmer. |
| **95% CI** | You are 95% confident the true difference lies in this range. **If zero is not in the CI, the difference is statistically significant.** |
| **p‑value** | Probability of seeing this difference by chance. **p < 0.05 = statistically significant.** |
| **Cohen's d** | Standardised effect size. **> 0.8 = large, > 0.5 = medium, > 0.2 = small.** |
| **SEM** | Standard error of the mean at each timestamp. How precise the *average* is. |

### The Sensitivity Curve

- **Flat line** = result is robust to the threshold.
- **Sloping line** = result depends on the threshold – be cautious.

### The Temporal Coverage Heatmap

- **Dark colours across the day** = threshold keeps data evenly.
- **Light/white patches** = threshold kills that time of day.

---

## 🐛 Troubleshooting

### Common Errors

| Error | Solution |
| :--- | :--- |
| `No files matching 'DD-MM-YYYY *.xlsx'` | Check file naming. Files must start with `DD-MM-YYYY ` (space after date). |
| `KeyError: 'Max_Spread'` | Ensure you're using the latest script version (Plot 9 fix included). |
| `KeyError: 'Date:'` | Excel columns must be exactly `Date:` and `Time:` (with colon). |
| `UnicodeEncodeError` | The script uses UTF‑8 encoding – should be fine on modern systems. |
| `No valid data after processing` | Check that readings are within 30–85 °C and columns exist. |

### Debugging

The script prints debug information to the console, including:
- Number of files found.
- Rows processed per file.
- Hour range and unique hours count (for active hours plot).

### Performance Notes

- The script is designed for **< 1 million rows**. For larger datasets, consider downsampling.
- Plots are saved at **300 DPI** – fine for publications.

---

## 📝 License

This script is provided **as‑is** for research purposes. You are free to use, modify, and distribute it with appropriate attribution.

**Author:** [Your Name / Lab]

---

## 🙏 Acknowledgements

- `statsmodels` for the Newey‑West HAC estimator.
- `pandas` and `numpy` for data handling.
- `matplotlib` for visualisations.

---

## 💡 Tips for Best Results

1. **Always check the Sensitivity Curve** before reporting a single number.
2. **Use the Temporal Coverage Heatmap** to ensure your threshold doesn't bias time of day.
3. **If the result is threshold‑dependent**, report the **range** (e.g., "The difference ranges from -2.25 °C to -1.20 °C depending on the filter").
4. **Present the Hour‑by‑Hour Retention plot** to show data quality across the experiment.
5. **If retention is < 60% across all hours**, consider repeating the experiment with improved sensor placement.

---

## 📧 Contact

For questions, issues, or feature requests, please open an issue on the GitHub repository or contact the author directly.

**Happy temperature‑comparing!** 🌡️📊
