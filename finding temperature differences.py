import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from fnmatch import fnmatch
from matplotlib.dates import DateFormatter
import statsmodels.api as sm
import scipy.stats as stats
from datetime import datetime

# ========== Configuration ==========
# Hard physical limits — readings outside these are impossible (sensor fault/typo)
LOWER_THRESHOLD = 30
UPPER_THRESHOLD = 85

# Channels
CHANNELS         = [3, 4, 5, 7, 9, 10, 11, 12]
PANEL_1_CHANNELS = [3, 4, 5, 7]    # unmodified panel — expected to be warmer
PANEL_2_CHANNELS = [9, 10, 11, 12] # cooled panel     — expected to be cooler

# Per-panel IQR outlier filter
# Each panel's channels are assessed independently against their own distribution.
IQR_MULTIPLIER = 2.5   # fence = Q1 - k*IQR ... Q3 + k*IQR

# Cross-panel difference window
# At each timestamp: expected range for (Panel_1_Avg - Panel_2_Avg)
# Panel 1 is warmer, so difference should be >= 0.
# Domain knowledge says the cooling effect produces at most ~6 °C separation.
DIFF_LOW  = -15   # below this: Panel 2 is warmer than Panel 1 — physically backwards
DIFF_HIGH = 15   # above this: gap is too large — something went wrong

# Newey-West lags for autocorrelation correction
NW_LAGS = 1


# ============================================================
# FILE PROCESSING
# ============================================================

def process_file(filepath):
    """Load one Excel file, apply hard-limit filter, return cleaned DataFrame."""
    df = pd.read_excel(filepath)
    try:
        df['DateTime'] = pd.to_datetime(
            df['Date:'].astype(str) + ' ' + df['Time:'].astype(str),
            dayfirst=True,
            errors='coerce'
        )
    except Exception as e:
        print(f"  Could not parse timestamps in {filepath}: {e}")
        return None

    bad_dt = df['DateTime'].isna().sum()
    if bad_dt:
        print(f"  Warning: {bad_dt} row(s) with unparseable timestamps dropped.")
        df = df.dropna(subset=['DateTime'])

    for ch in CHANNELS:
        col = f"Channel - {ch}"
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].where(
                (df[col] >= LOWER_THRESHOLD) & (df[col] <= UPPER_THRESHOLD)
            )
    return df


# ============================================================
# STEP 2 — PER-PANEL IQR FILTER
# ============================================================

def _iqr_mask(series, k):
    """
    Return (outlier_mask, lower_fence, upper_fence) for a Series.
    Only non-NaN values are considered; NaNs are never flagged.
    """
    valid = series.dropna()
    if len(valid) < 4:
        return pd.Series(False, index=series.index), np.nan, np.nan
    q1  = valid.quantile(0.25)
    q3  = valid.quantile(0.75)
    iqr = q3 - q1
    lo  = q1 - k * iqr
    hi  = q3 + k * iqr
    # Build mask over full index (NaN rows stay False)
    full_mask = pd.Series(False, index=series.index)
    full_mask[valid[(valid < lo) | (valid > hi)].index] = True
    return full_mask, lo, hi


def apply_per_panel_iqr(df, k=IQR_MULTIPLIER):
    """
    Apply IQR outlier removal separately to Panel 1 channels and Panel 2 channels.
    Panel 1 channels are assessed only against each other's distribution;
    Panel 2 channels are assessed only against each other's distribution.
    Returns cleaned df and a per-channel summary dict.
    """
    summary = {}

    for panel_label, channels in [("Panel 1", PANEL_1_CHANNELS),
                                   ("Panel 2", PANEL_2_CHANNELS)]:
        # Collect all valid readings from this panel's channels to get
        # a single shared distribution for the panel.
        # Rationale: channels on the same panel should track together;
        # pooling them gives a more stable Q1/Q3 than per-channel stats
        # when individual channels have few readings.
        panel_cols = [f"Channel - {ch}" for ch in channels
                      if f"Channel - {ch}" in df.columns]
        if not panel_cols:
            continue

        # Stack all readings from this panel into one series for fence calculation
        stacked = df[panel_cols].stack(future_stack=True).dropna()
        if len(stacked) < 4:
            for col in panel_cols:
                summary[col] = {"skipped": True, "reason": "too few readings in panel"}
            continue

        q1  = stacked.quantile(0.25)
        q3  = stacked.quantile(0.75)
        iqr = q3 - q1
        lo  = q1 - k * iqr
        hi  = q3 + k * iqr

        for col in panel_cols:
            series    = df[col]
            valid     = series.dropna()
            out_mask  = pd.Series(False, index=df.index)
            out_mask[valid[(valid < lo) | (valid > hi)].index] = True

            n_out          = int(out_mask.sum())
            outlier_vals   = df.loc[out_mask, col].tolist()
            df.loc[out_mask, col] = np.nan

            summary[col] = {
                "panel":          panel_label,
                "n_total":        len(valid),
                "n_outliers":     n_out,
                "outlier_values": [round(v, 3) for v in outlier_vals],
                "fence_lower":    round(lo, 3),
                "fence_upper":    round(hi, 3),
                "pct_removed":    round(100 * n_out / len(valid), 2) if len(valid) else 0,
            }

    return df, summary


# ============================================================
# STEP 3 — CROSS-PANEL DIFFERENCE CHECK
# ============================================================

def apply_cross_panel_check(df, diff_low=DIFF_LOW, diff_high=DIFF_HIGH):
    """
    After per-panel cleaning, compute Panel_1_Avg - Panel_2_Avg at each timestamp.
    Flag rows where the difference falls outside [diff_low, diff_high].

    Reasoning:
      - diff < diff_low  (including negative): Panel 2 is warmer than Panel 1.
        Since Panel 2 is the cooled panel, this is physically backwards.
      - diff > diff_high: the gap is larger than the known maximum cooling effect.
        This suggests at least one panel's average is corrupted even after
        per-channel cleaning (e.g. multiple channels on one panel reading low
        simultaneously — consistent within the panel but wrong in absolute terms).

    The averaged values for flagged rows are set to NaN so they are excluded
    from all subsequent statistics and plots.  The raw channel columns are
    left untouched so you can inspect them.
    """
    p1_cols = [f"Channel - {ch}" for ch in PANEL_1_CHANNELS if f"Channel - {ch}" in df.columns]
    p2_cols = [f"Channel - {ch}" for ch in PANEL_2_CHANNELS if f"Channel - {ch}" in df.columns]

    df['Panel_1_Avg'] = df[p1_cols].mean(axis=1)
    df['Panel_2_Avg'] = df[p2_cols].mean(axis=1)
    df['Diff']        = df['Panel_1_Avg'] - df['Panel_2_Avg']

    # Rows where both averages exist but difference is out of window
    both_valid   = df['Panel_1_Avg'].notna() & df['Panel_2_Avg'].notna()
    out_of_range = both_valid & (
        (df['Diff'] < diff_low) | (df['Diff'] > diff_high)
    )

    n_flagged      = int(out_of_range.sum())
    flagged_diffs  = df.loc[out_of_range, 'Diff'].tolist()
    flagged_times  = df.loc[out_of_range, 'DateTime'].tolist()

    # Null out averages and diff for flagged rows
    df.loc[out_of_range, ['Panel_1_Avg', 'Panel_2_Avg', 'Diff']] = np.nan

    cross_summary = {
        "diff_low":       diff_low,
        "diff_high":      diff_high,
        "n_both_valid":   int(both_valid.sum()),
        "n_flagged":      n_flagged,
        "flagged_diffs":  [round(v, 3) for v in flagged_diffs],
        "flagged_times":  [str(t) for t in flagged_times],
    }
    return df, cross_summary


# ============================================================
# REPORT FORMATTING
# ============================================================

def format_reports(date_input, iqr_summary, cross_summary):
    lines = [
        "",
        "=" * 56,
        "OUTLIER DETECTION REPORT",
        "=" * 56,
        f"Date: {date_input}",
        "",
        "─" * 56,
        "STEP 1 — Hard physical limits",
        "─" * 56,
        f"  Any reading outside [{LOWER_THRESHOLD} °C, {UPPER_THRESHOLD} °C] was deleted",
        "  immediately as physically impossible (sensor fault,",
        "  disconnection, or data-entry error).",
        "",
        "─" * 56,
        "STEP 2 — Per-panel IQR filter  (k = {})".format(IQR_MULTIPLIER),
        "─" * 56,
        "  Panel 1 channels (3,4,5,7) are assessed against the",
        "  distribution of Panel 1 readings only.",
        "  Panel 2 channels (9,10,11,12) are assessed against the",
        "  distribution of Panel 2 readings only.",
        "  This keeps the two panels' different temperature ranges",
        "  from interfering with each other's outlier fences.",
        "  Fence = Q1 - {}*IQR  to  Q3 + {}*IQR".format(IQR_MULTIPLIER, IQR_MULTIPLIER),
        "",
    ]

    for col, info in iqr_summary.items():
        if info.get("skipped"):
            lines.append(f"  {col}: skipped ({info['reason']})")
            continue
        n = info['n_outliers']
        if n > 0:
            lines += [
                f"  {col}  [{info['panel']}]:",
                f"    Readings after hard limits : {info['n_total']}",
                f"    Panel fences               : [{info['fence_lower']} °C,  {info['fence_upper']} °C]",
                f"    Outliers removed           : {n}  ({info['pct_removed']} %)",
                f"    Removed values             : {info['outlier_values']}",
            ]
        else:
            lines.append(
                f"  {col}  [{info['panel']}]: no outliers  "
                f"(fences [{info['fence_lower']}, {info['fence_upper']}] °C)"
            )

    lines += [
        "",
        "─" * 56,
        "STEP 3 — Cross-panel difference check",
        "─" * 56,
        f"  Expected window for (Panel 1 avg − Panel 2 avg):",
        f"    Low  = {cross_summary['diff_low']} °C  "
        f"(Panel 2 warmer than Panel 1 → physically backwards)",
        f"    High = {cross_summary['diff_high']} °C  "
        f"(gap exceeds maximum known cooling effect)",
        f"  Timestamps with both panel averages valid : {cross_summary['n_both_valid']}",
        f"  Timestamps flagged and excluded           : {cross_summary['n_flagged']}",
    ]

    if cross_summary['n_flagged'] > 0:
        lines.append("  Flagged timestamps and their differences:")
        for t, d in zip(cross_summary['flagged_times'], cross_summary['flagged_diffs']):
            reason = "Panel 2 warmer (negative diff)" if d < cross_summary['diff_low'] \
                     else "Gap too large"
            lines.append(f"    {t}  →  diff = {d} °C  ({reason})")
    else:
        lines.append("  No timestamps flagged by cross-panel check.")

    lines += ["", "=" * 56, ""]
    return "\n".join(lines)


# ============================================================
# STATISTICS
# ============================================================

def newey_west_t_test(series, maxlags=NW_LAGS):
    """t-test on mean using Newey-West (HAC) standard errors."""
    y = series.dropna()
    if len(y) < 2:
        return np.nan, np.nan, np.nan
    X     = np.ones((len(y), 1))
    model = sm.OLS(np.asarray(y), X).fit(cov_type='HAC', cov_kwds={'maxlags': maxlags})
    return float(model.tvalues[0]), float(model.pvalues[0]), float(model.df_resid)


# ============================================================
# PLOTTING HELPER
# ============================================================

def _time_axis(ax):
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    ax.figure.autofmt_xdate()
    ax.grid(True, alpha=0.3)


# ============================================================
# MAIN
# ============================================================

def main():
    # ----- User inputs -----
    while True:
        date_input = input("Enter date (dd-mm-yyyy): ").strip()
        try:
            datetime.strptime(date_input, '%d-%m-%Y')
            break
        except ValueError:
            print("  Invalid format. Use dd-mm-yyyy")

    FILE_PATTERN = f"{date_input} *.xlsx"

    while True:
        INPUT_DIR = input("Enter input folder path: ").strip()
        if os.path.isdir(INPUT_DIR):
            break
        print("  Invalid directory")

    while True:
        OUTPUT_DIR = input("Enter output folder path: ").strip()
        if OUTPUT_DIR:
            break
        print("  Cannot be empty")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ----- Find and process files -----
    file_paths = [
        os.path.join(INPUT_DIR, f)
        for f in os.listdir(INPUT_DIR)
        if fnmatch(f.lower(), FILE_PATTERN.lower())
    ]
    if not file_paths:
        print(f"No files matching '{FILE_PATTERN}' in {INPUT_DIR}")
        return
    print(f"\nFound {len(file_paths)} file(s). Processing...")

    df_list = []
    for fp in sorted(file_paths):
        print(f"  Processing: {os.path.basename(fp)}")
        df = process_file(fp)
        if df is not None:
            df_list.append(df)
    if not df_list:
        print("No valid data after processing.")
        return

    # Keep a raw copy (hard-limits only) for the before/after plot
    raw_combined = pd.concat(df_list).sort_values('DateTime').reset_index(drop=True)
    combined_df  = raw_combined.copy()

    print(f"\nCombined dataset: {len(combined_df)} rows.")

    # ----- Step 2: per-panel IQR -----
    print(f"Step 2: per-panel IQR filter (k={IQR_MULTIPLIER}) ...")
    combined_df, iqr_summary = apply_per_panel_iqr(combined_df)

    # ----- Step 3: cross-panel difference check -----
    print(f"Step 3: cross-panel difference check  "
          f"[{DIFF_LOW}, {DIFF_HIGH}] °C ...")
    combined_df, cross_summary = apply_cross_panel_check(combined_df)

    # ----- Reports -----
    report = format_reports(date_input, iqr_summary, cross_summary)
    print(report)

    # Sparse-channel warning
    p1_cols = [f"Channel - {ch}" for ch in PANEL_1_CHANNELS if f"Channel - {ch}" in combined_df.columns]
    p2_cols = [f"Channel - {ch}" for ch in PANEL_2_CHANNELS if f"Channel - {ch}" in combined_df.columns]
    sparse1 = (combined_df[p1_cols].notna().sum(axis=1) < len(p1_cols) / 2).sum()
    sparse2 = (combined_df[p2_cols].notna().sum(axis=1) < len(p2_cols) / 2).sum()
    if sparse1 or sparse2:
        print(f"  Note: {sparse1} Panel-1 rows and {sparse2} Panel-2 rows averaged "
              f"from fewer than half their channels.")

    # ============================================================
    # STATISTICAL ANALYSIS
    # ============================================================
    diff_clean = combined_df['Diff'].dropna()
    if len(diff_clean) < 2:
        print("Not enough valid data points for statistics.")
        return

    mean_diff = diff_clean.mean()
    std_diff  = diff_clean.std()
    n         = len(diff_clean)

    if mean_diff > 0:
        diff_statement = f"Panel 1 is WARMER than Panel 2 by {abs(mean_diff):.3f} °C on average."
    elif mean_diff < 0:
        diff_statement = f"Panel 2 is WARMER than Panel 1 by {abs(mean_diff):.3f} °C on average."
    else:
        diff_statement = "Both panels have the same average temperature."

    t_stat, p_val, df_adj = newey_west_t_test(diff_clean, maxlags=NW_LAGS)

    s1 = combined_df['Panel_1_Avg'].dropna().std()
    s2 = combined_df['Panel_2_Avg'].dropna().std()
    pooled_std  = np.sqrt((s1**2 + s2**2) / 2) if (s1 > 0 and s2 > 0) else np.nan
    effect_size = mean_diff / pooled_std if (pooled_std and not np.isnan(pooled_std)) else np.nan

    combined_df['Time_sec'] = (
        combined_df['DateTime'] - combined_df['DateTime'].iloc[0]
    ).dt.total_seconds()
    valid_reg = combined_df[['Panel_1_Avg', 'Panel_2_Avg', 'Time_sec']].dropna()
    if len(valid_reg) > 5:
        X_reg    = sm.add_constant(valid_reg[['Time_sec']])
        y_reg    = valid_reg['Panel_1_Avg'] - valid_reg['Panel_2_Avg']
        time_mdl = sm.OLS(y_reg, X_reg).fit()
        time_coef = time_mdl.params['Time_sec']
        time_p    = time_mdl.pvalues['Time_sec']
    else:
        time_coef, time_p = np.nan, np.nan

    def _effect_label(d):
        if np.isnan(d): return "N/A"
        d = abs(d)
        if d < 0.2: return "negligible"
        if d < 0.5: return "small"
        if d < 0.8: return "medium"
        return "large"

    results_text = f"""
==================================================
TEMPERATURE COMPARISON: PANEL 1 vs PANEL 2
==================================================
Date            : {date_input}
Hard limits     : [{LOWER_THRESHOLD}, {UPPER_THRESHOLD}] °C
IQR multiplier  : {IQR_MULTIPLIER}  (per-panel, separate distributions)
Diff window     : [{DIFF_LOW}, {DIFF_HIGH}] °C  (Panel 1 − Panel 2)
Data points (n) : {n}

DESCRIPTIVE STATISTICS:
  Mean difference (P1 - P2) : {mean_diff:.3f} °C
  Std deviation of diff     : {std_diff:.3f} °C
  {diff_statement}

INFERENTIAL STATISTICS (Newey-West HAC, lags={NW_LAGS}):
  H0: mean difference = 0
    t-statistic                   = {t_stat:.4f}
    degrees of freedom (residual) = {df_adj:.2f}
    p-value                       = {p_val:.6f}
  {'Reject H0' if p_val < 0.05 else 'Fail to reject H0'} at alpha = 0.05.
  -> There {"IS" if p_val < 0.05 else "is NOT"} a statistically significant mean difference.

EFFECT SIZE:
  Cohen's d (approx.) = {effect_size:.3f}  [{_effect_label(effect_size)}]

REGRESSION WITH TIME TREND:
  Change in difference per second : {time_coef:.6f} °C/s
  p-value for time trend          : {time_p:.4f}
  {'Significant time trend detected.' if time_p < 0.05 else 'No significant time trend.'}

CONCLUSION:
  {'Statistically and practically meaningful temperature difference.' if (p_val<0.05 and abs(effect_size)>0.2) else 'Statistically significant but negligible effect size.' if p_val<0.05 else 'No strong evidence of a meaningful temperature difference.'}
==================================================
"""
    print(results_text)

    stats_path = os.path.join(OUTPUT_DIR, "statistical_comparison.txt")
    with open(stats_path, 'w', encoding='utf-8') as f:
        f.write(report)
        f.write(results_text)
    print(f"Report saved to: {stats_path}")

    # ============================================================
    # PLOTS
    # ============================================================

    # Plot 0 — per-channel before/after (per-panel IQR only, before cross check)
    # We need an intermediate state: after IQR, before cross-panel nulling
    # We can derive it: raw_combined with IQR applied is 'combined_df' channel cols
    # (cross check only nulled Panel_1_Avg/Panel_2_Avg/Diff, not raw channel cols)
    n_ch = len(CHANNELS)
    fig, axes = plt.subplots(n_ch, 1, figsize=(14, 2.8 * n_ch), sharex=True)
    fig.suptitle(
        'Per-channel: hard-limit only (red)  vs  after per-panel IQR removal (blue)',
        fontsize=12, fontweight='bold', y=1.005
    )
    for ax, ch in zip(axes, CHANNELS):
        col = f"Channel - {ch}"
        if col not in raw_combined.columns:
            ax.set_visible(False)
            continue
        panel_label = "Panel 1" if ch in PANEL_1_CHANNELS else "Panel 2"
        ax.plot(raw_combined['DateTime'], raw_combined[col],
                color='#d62728', alpha=0.5, linewidth=1, label='Hard-limit only')
        ax.plot(combined_df['DateTime'], combined_df[col],
                color='#1f77b4', alpha=0.9, linewidth=1, label='After per-panel IQR')
        info  = iqr_summary.get(col, {})
        n_out = info.get('n_outliers', 0)
        ax.set_ylabel('°C', fontsize=9)
        ax.set_title(f'{col}  [{panel_label}]  |  {n_out} IQR outlier(s) removed',
                     fontsize=10)
        ax.legend(fontsize=8, loc='upper right')
        _time_axis(ax)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "outlier_per_channel.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Per-channel plot saved to: {p}")

    # Plot 1 — difference over time with cross-panel window shaded
    fig, ax = plt.subplots(figsize=(12, 4))
    # Plot raw diff (before cross-panel exclusion) in grey for reference
    raw_combined['Panel_1_Avg_raw'] = raw_combined[
        [f"Channel - {ch}" for ch in PANEL_1_CHANNELS if f"Channel - {ch}" in raw_combined.columns]
    ].mean(axis=1)
    raw_combined['Panel_2_Avg_raw'] = raw_combined[
        [f"Channel - {ch}" for ch in PANEL_2_CHANNELS if f"Channel - {ch}" in raw_combined.columns]
    ].mean(axis=1)
    raw_combined['Diff_raw'] = raw_combined['Panel_1_Avg_raw'] - raw_combined['Panel_2_Avg_raw']

    ax.plot(raw_combined['DateTime'], raw_combined['Diff_raw'],
            color='#aaaaaa', linewidth=1, alpha=0.6, label='Before cross-panel check')
    ax.plot(combined_df['DateTime'], combined_df['Diff'],
            color='#1f77b4', linewidth=1.5, alpha=0.9, label='After all filters')

    # Shade the valid window
    ax.axhspan(DIFF_LOW, DIFF_HIGH, alpha=0.08, color='green',
               label=f'Expected window [{DIFF_LOW}, {DIFF_HIGH}] °C')
    ax.axhline(DIFF_LOW,  color='green', linestyle='--', linewidth=1)
    ax.axhline(DIFF_HIGH, color='green', linestyle='--', linewidth=1)
    ax.axhline(mean_diff, color='navy',  linestyle=':',  linewidth=1.5,
               label=f'Mean diff = {mean_diff:.2f} °C')

    ax.set_xlabel('Time')
    ax.set_ylabel('Panel 1 − Panel 2  (°C)')
    ax.set_title('Cross-panel temperature difference  —  green band = expected window')
    ax.legend(fontsize=9)
    _time_axis(ax)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "temperature_difference.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Difference plot saved to: {p}")

    # Plot 2 — panel averages
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(combined_df['DateTime'], combined_df['Panel_1_Avg'],
            label='Panel 1 (unmodified)', linewidth=2, marker='o', markersize=3, alpha=0.7)
    ax.plot(combined_df['DateTime'], combined_df['Panel_2_Avg'],
            label='Panel 2 (cooled)',     linewidth=2, marker='s', markersize=3, alpha=0.7)
    ax.set_title('Average Temperature — Panel 1 vs Panel 2', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time (HH:MM:SS)', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontsize=12)
    ax.set_ylim(LOWER_THRESHOLD - 5, UPPER_THRESHOLD + 5)
    ax.legend(fontsize=11)
    _time_axis(ax)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "temperature_average_comparison.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Comparison plot saved to: {p}")

    # Plot 3 — distribution of differences
    fig, ax = plt.subplots(figsize=(8, 4))
    diff_clean.hist(bins=30, ax=ax, color='steelblue', edgecolor='white',
                    alpha=0.8, density=True)
    diff_clean.plot(kind='kde', ax=ax, color='navy', linewidth=2)
    ax.axvline(mean_diff, color='r',    linestyle='--', linewidth=1.5,
               label=f'Mean = {mean_diff:.2f} °C')
    ax.axvline(DIFF_LOW,  color='green', linestyle=':', linewidth=1.2,
               label=f'Window low  = {DIFF_LOW} °C')
    ax.axvline(DIFF_HIGH, color='green', linestyle=':', linewidth=1.2,
               label=f'Window high = {DIFF_HIGH} °C')
    ax.set_xlabel('Panel 1 − Panel 2  (°C)')
    ax.set_ylabel('Density')
    ax.set_title('Distribution of temperature differences (post-filter)')
    ax.legend()
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "difference_distribution.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Distribution plot saved to: {p}")

    # CSV
    csv_path = os.path.join(OUTPUT_DIR, "temperature_averages.csv")
    combined_df[['DateTime', 'Panel_1_Avg', 'Panel_2_Avg', 'Diff']].to_csv(
        csv_path, index=False)
    print(f"Averaged data saved to: {csv_path}")
    print("\nAll outputs written successfully.")


if __name__ == "__main__":
    main()
