import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from fnmatch import fnmatch
from matplotlib.dates import DateFormatter
import statsmodels.api as sm
from datetime import datetime
from itertools import combinations

# ========== Configuration ==========
LOWER_THRESHOLD  = 30     # °C — hard physical lower limit
UPPER_THRESHOLD  = 85     # °C — hard physical upper limit
CHANNELS         = [3, 4, 5, 7, 9, 10, 11, 12]
PANEL_1_CHANNELS = [3, 4, 5, 7]
PANEL_2_CHANNELS = [9, 10, 11, 12]
MAX_SPREAD_4     = 6.0    # °C — max allowed spread within a cluster of 3 or 4 sensors
MIN_OUTSIDER_GAP = 3.0    # outsider must be at least this far from the nearest cluster member
MAX_SPREAD_2     = 4.0    # °C — max allowed difference when exactly 2 sensors active
NW_LAGS          = 1      # lags for Newey-West autocorrelation correction
LAG_WINDOW       = 5      # number of timestamps to look ahead for stabilisation
LAG_THRESHOLD    = 1.5    # °C — if reconnected sensor is this far from median, check for lag

# Colour codes for the plot (what happened at each timestamp)
COLORS = {
    'all_ok':      '#1f77b4',   # blue   — all sensors agreed
    'one_dropped': '#ff7f0e',   # orange — one sensor dropped, averaged from 3
    'two_sensors': '#2ca02c',   # green  — only 2 sensors active, both agreed
    'dropped':     '#d62728',   # red    — timestamp dropped (shown as scatter markers)
}


# ============================================================
# LAG CORRECTION — detects reconnecting/stabilising sensors
# ============================================================

def apply_lag_correction(df, panel_channels, lag_window=LAG_WINDOW, lag_threshold=LAG_THRESHOLD):
    """
    Detect sensors that have just reconnected (NaN -> valid) and are
    "lagging" (slowly converging to the other sensors).
    For these timestamps, set the channel to NaN so the average uses the other 3 sensors.
    Applied per panel, per file.
    """
    df_copy = df.copy()
    for ch in panel_channels:
        col = f"Channel - {ch}"
        if col not in df_copy.columns:
            continue

        # Process each file (batch) independently to avoid cross‑file continuity
        for file_name, group in df_copy.groupby('File'):
            idx = group.index
            series = group[col]

            # Find reconnection points: valid now, but was NaN in previous 1 or 2 steps
            reconn_mask = series.notna() & (series.shift(1).isna() | series.shift(2).isna())
            reconn_indices = idx[reconn_mask]

            for i in reconn_indices:
                loc = df_copy.index.get_loc(i)

                # Get the other channels on this same panel
                other_cols = [
                    f"Channel - {c}"
                    for c in panel_channels
                    if c != ch and f"Channel - {c}" in df_copy.columns
                ]
                if not other_cols:
                    continue

                # Check initial difference at reconnection point
                start_idx = df_copy.index[loc]
                start_median = df_copy.loc[start_idx, other_cols].median()
                if pd.isna(start_median):
                    continue
                initial_diff = abs(df_copy.loc[start_idx, col] - start_median)
                if initial_diff < lag_threshold:
                    continue  # not far enough to be a noticeable lag

                # Look ahead to see if it's converging
                max_lookahead = min(lag_window, len(df_copy) - loc - 1)
                if max_lookahead < 1:
                    continue

                diffs = []
                for k in range(1, max_lookahead + 1):
                    check_idx = df_copy.index[loc + k]
                    if pd.isna(df_copy.loc[check_idx, col]):
                        break
                    check_median = df_copy.loc[check_idx, other_cols].median()
                    if pd.isna(check_median):
                        break
                    diff = abs(df_copy.loc[check_idx, col] - check_median)
                    diffs.append(diff)

                if not diffs:
                    continue

                # If diffs are decreasing (converging) or end below threshold / 2
                if diffs[-1] < diffs[0] - 0.3 or diffs[-1] < lag_threshold / 2:
                    # It's lagging! Nullify the channel for the first few timestamps
                    for k in range(max_lookahead):
                        null_idx = df_copy.index[loc + k]
                        # Always nullify the first 3 timestamps
                        if k < 3:
                            df_copy.loc[null_idx, col] = np.nan
                        else:
                            # For later timestamps, only nullify if still > threshold
                            median_val = df_copy.loc[null_idx, other_cols].median()
                            if not pd.isna(median_val):
                                if abs(df_copy.loc[null_idx, col] - median_val) > lag_threshold:
                                    df_copy.loc[null_idx, col] = np.nan
    return df_copy


# ============================================================
# WITHIN-PANEL TIMESTAMP FILTER (with uncertainty metrics)
# ============================================================

def assess_timestamp(readings):
    """
    Given up to 4 valid (non-NaN) readings from one panel at one timestamp,
    decide which readings to keep.

    Returns (kept_values, status) where status is one of:
      'all_ok'      — all sensors agreed, keep all
      'one_dropped' — one rogue sensor dropped, keep 3
      'two_sensors' — exactly 2 sensors active and they agreed
      'dropped'     — timestamp unusable, discard

    Rules:
      n < 2   → dropped
      n == 2  → keep both if diff <= MAX_SPREAD_2, else dropped
      n == 3  → keep all 3 if spread <= MAX_SPREAD_4, else dropped
      n == 4  → all_ok if spread <= MAX_SPREAD_4
                one_dropped if exactly one valid trio exists and
                  the outsider is > MAX_SPREAD_4 from all trio members
                else dropped
    """
    vals = sorted([v for v in readings if not np.isnan(v)])
    n    = len(vals)

    if n < 2:
        return None, 'dropped'

    if n == 2:
        if vals[1] - vals[0] <= MAX_SPREAD_2:
            return vals, 'two_sensors'
        return None, 'dropped'

    if n == 3:
        if vals[-1] - vals[0] <= MAX_SPREAD_4:
            return vals, 'all_ok'
        return None, 'dropped'

    # n == 4
    if vals[-1] - vals[0] <= MAX_SPREAD_4:
        return vals, 'all_ok'

    valid_groups = []
    for trio in combinations(range(4), 3):
        group    = [vals[i] for i in trio]
        outsider = vals[[i for i in range(4) if i not in trio][0]]
        if max(group) - min(group) <= MAX_SPREAD_4:
            if all(abs(outsider - g) > MIN_OUTSIDER_GAP for g in group):
                valid_groups.append(group)

    if len(valid_groups) == 1:
        return valid_groups[0], 'one_dropped'
    return None, 'dropped'


def apply_within_panel_filter(df, channels, panel_label):
    """
    Apply the timestamp-level cluster filter to one panel's channels.
    Returns:
      averages  — Series of per-timestamp averages (NaN where dropped)
      stdevs    — Series of per-timestamp standard deviations (NaN if dropped)
      n_active  — Series of number of sensors used (2,3,4 or NaN if dropped)
      statuses  — Series of per-timestamp status strings
      summary   — dict with counts and dropped details
    """
    cols     = [f"Channel - {ch}" for ch in channels if f"Channel - {ch}" in df.columns]
    averages = pd.Series(np.nan,  index=df.index)
    stdevs   = pd.Series(np.nan,  index=df.index)
    n_active = pd.Series(np.nan,  index=df.index)
    statuses = pd.Series('dropped', index=df.index)

    counts = {
        'all_ok': 0, 'one_dropped': 0,
        'two_sensors': 0, 'dropped': 0
    }
    dropped_details = []

    for idx, row in df[cols + ['DateTime']].iterrows():
        # Coerce each value to float first — Excel cells can come in as strings
        raw_vals = []
        for c in cols:
            try:
                raw_vals.append(float(row[c]))
            except (TypeError, ValueError):
                raw_vals.append(np.nan)
        valid_vals = [v for v in raw_vals if not np.isnan(v)]
        n_valid    = len(valid_vals)

        result, status = assess_timestamp(valid_vals)
        statuses[idx]  = status
        counts[status] += 1

        if result is not None:
            averages[idx] = np.mean(result)
            n_active[idx] = len(result)
            # Sample standard deviation (ddof=1). If only 1 sensor, set to 0.
            if len(result) > 1:
                stdevs[idx] = np.std(result, ddof=1)
            else:
                stdevs[idx] = 0.0
        else:
            if n_valid == 0:
                reason = "no valid readings after hard limits"
            elif n_valid == 1:
                reason = "only 1 sensor active — cannot assess agreement"
            elif n_valid == 2:
                reason = (f"2 sensors active, disagreement > {MAX_SPREAD_2} °C "
                          f"(values: {[round(v,2) for v in valid_vals]})")
            else:
                reason = "no clear majority cluster (ambiguous or 2-2 split)"
            dropped_details.append((row['DateTime'], reason, valid_vals))

    summary = {
        "panel":            panel_label,
        "n_rows":           len(df),
        "counts":           counts,
        "dropped_details":  dropped_details,
    }
    return averages, stdevs, n_active, statuses, summary


# ============================================================
# FILE PROCESSING
# ============================================================

def process_file(filepath):
    """Load one Excel file, apply hard physical limits, return cleaned DataFrame."""
    df = pd.read_excel(filepath)
    try:
        df['DateTime'] = pd.to_datetime(
            df['Date:'].astype(str) + ' ' + df['Time:'].astype(str),
            dayfirst=True, errors='coerce'
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

    # Keep track of which file each row came from (batch)
    df['File'] = os.path.basename(filepath)
    return df


# ============================================================
# REPORT FORMATTING (updated to include new steps)
# ============================================================

def format_report(date_input, p1_summary, p2_summary):
    def panel_section(s):
        c = s['counts']
        total_kept = c['all_ok'] + c['one_dropped'] + c['two_sensors']
        lines = [
            f"  {s['panel']}:",
            f"    Total timestamps                              : {s['n_rows']}",
            f"    All sensors agreed (3 or 4 active)           : {c['all_ok']}",
            f"    One sensor dropped, averaged from 3           : {c['one_dropped']}",
            f"    2 sensors active, agreed (diff <= {MAX_SPREAD_2} °C)   : {c['two_sensors']}",
            f"    Timestamp dropped entirely                    : {c['dropped']}",
            f"    Total timestamps contributing to average      : {total_kept}",
        ]
        n_show = min(10, len(s['dropped_details']))
        if n_show > 0:
            lines.append(f"    First {n_show} dropped timestamp(s):")
            for dt, reason, vals in s['dropped_details'][:n_show]:
                cleaned = [round(v, 2) if not np.isnan(v) else 'NaN' for v in vals]
                lines.append(f"      {dt}  readings={cleaned}")
                lines.append(f"        reason: {reason}")
        return "\n".join(lines)

    return "\n".join([
        "",
        "=" * 62,
        "OUTLIER DETECTION REPORT",
        "=" * 62,
        f"Date: {date_input}",
        "",
        "─" * 62,
        "STEP 1 — Hard physical limits",
        "─" * 62,
        f"  Readings outside [{LOWER_THRESHOLD} °C, {UPPER_THRESHOLD} °C] deleted unconditionally.",
        "",
        "─" * 62,
        f"STEP 2 — Lag correction (reconnecting sensors)",
        "─" * 62,
        f"  If a sensor reconnects after being missing, and is {LAG_THRESHOLD} °C",
        f"  away from the panel median, but converges within {LAG_WINDOW} steps,",
        f"  its readings during the stabilisation are excluded from the average.",
        "",
        "─" * 62,
        f"STEP 3 — Within-panel cluster filter",
        "─" * 62,
        "  Decision rules at each timestamp:",
        f"  • 4 or 3 sensors active, all within {MAX_SPREAD_4} °C",
        "      → keep all, average normally.                      [all_ok]",
        f"  • 4 sensors active, exactly 3 agree within {MAX_SPREAD_4} °C",
        f"    AND the 4th is > {MAX_SPREAD_4} °C from all 3",
        "      → drop the 4th, average the 3.                  [one_dropped]",
        f"  • Exactly 2 sensors active, difference <= {MAX_SPREAD_2} °C",
        "      → keep both, average the 2.                     [two_sensors]",
        f"  • Exactly 2 sensors active, difference > {MAX_SPREAD_2} °C",
        "      → drop timestamp.                                  [dropped]",
        "  • Any other case (2-2 split, 1 or 0 sensors active)",
        "      → drop timestamp.                                  [dropped]",
        "",
        panel_section(p1_summary),
        "",
        panel_section(p2_summary),
        "",
        "=" * 62,
        "",
    ])


# ============================================================
# STATISTICS (now returns standard error)
# ============================================================

def newey_west_t_test(series, maxlags=NW_LAGS):
    y = series.dropna()
    if len(y) < 2:
        return np.nan, np.nan, np.nan, np.nan
    X = np.ones((len(y), 1))
    model = sm.OLS(np.asarray(y), X).fit(cov_type='HAC', cov_kwds={'maxlags': maxlags})
    t_stat = float(model.tvalues[0])
    p_val  = float(model.pvalues[0])
    df_adj = float(model.df_resid)
    se     = float(model.bse[0])  # standard error of the mean
    return t_stat, p_val, df_adj, se


# ============================================================
# RUN INTERVAL ANALYSIS (BOTH DIRECTIONS) + UPGRADED QUALITY FLAGS
# ============================================================

def get_run_intervals(df, group_col='File', diff_col='Diff', datetime_col='DateTime'):
    """
    For each file, find consecutive runs where:
        - Diff > 0  (Panel 2 colder)
        - Diff < 0  (Panel 1 colder)
    Returns two DataFrames: (df_positive, df_negative)
    Each has columns: File, run_number, start_time, end_time, length, direction
    """
    records_pos = []
    records_neg = []
    for file_name, group in df.groupby(group_col):
        group = group.sort_values(datetime_col)
        mask_pos = group[diff_col] > 0
        mask_neg = group[diff_col] < 0

        def extract_runs(mask, direction):
            runs = []
            i = 0
            n = len(group)
            run_num = 0
            while i < n:
                if mask.iloc[i]:
                    start_idx = i
                    while i < n and mask.iloc[i]:
                        i += 1
                    end_idx = i - 1
                    run_num += 1
                    start_time = group.iloc[start_idx][datetime_col]
                    end_time   = group.iloc[end_idx][datetime_col]
                    length = end_idx - start_idx + 1
                    runs.append({
                        'File': file_name,
                        'run_number': run_num,
                        'start_time': start_time,
                        'end_time': end_time,
                        'length': length,
                        'direction': direction
                    })
                else:
                    i += 1
            return runs

        records_pos.extend(extract_runs(mask_pos, 'P2 colder'))
        records_neg.extend(extract_runs(mask_neg, 'P1 colder'))

    df_pos = pd.DataFrame(records_pos) if records_pos else pd.DataFrame(columns=['File','run_number','start_time','end_time','length','direction'])
    df_neg = pd.DataFrame(records_neg) if records_neg else pd.DataFrame(columns=['File','run_number','start_time','end_time','length','direction'])
    return df_pos, df_neg


def flag_noisy_runs(run_df, combined_df, panel1_cols, panel2_cols, threshold=1.5):
    """
    Upgraded: Flags runs based on BOTH average spread AND stability (volatility) of spread.
    
    Returns a copy of run_df with added columns:
        std_p1, std_p2           : mean standard deviation of sensors during the run
        std_p1_volatility, std_p2_volatility : standard deviation of the std dev (how much it wobbled)
        flag                     : reason for flagging (or empty string)
    """
    if run_df.empty:
        return run_df
    flagged = run_df.copy()
    flagged['std_p1'] = np.nan
    flagged['std_p2'] = np.nan
    flagged['std_p1_volatility'] = np.nan
    flagged['std_p2_volatility'] = np.nan
    flagged['flag'] = ''

    for idx, row in flagged.iterrows():
        # Get rows belonging to this run
        mask = (combined_df['File'] == row['File']) & (combined_df['DateTime'] >= row['start_time']) & (combined_df['DateTime'] <= row['end_time'])
        run_data = combined_df[mask]
        if run_data.empty:
            continue

        # Calculate the Standard Deviation for EVERY second in this run
        p1_std_series = run_data[panel1_cols].std(axis=1)
        p2_std_series = run_data[panel2_cols].std(axis=1)

        # 1. Average spread (the old metric)
        p1_mean_std = p1_std_series.mean()
        p2_mean_std = p2_std_series.mean()

        # 2. Volatility of the spread (the new metric!)
        # If this is high, the sensors are "wobbling" (intermittent glitch).
        # If this is low, the spread is "constant" (steady gradient or calibration).
        p1_volatility = p1_std_series.std()
        p2_volatility = p2_std_series.std()

        flagged.loc[idx, 'std_p1'] = p1_mean_std
        flagged.loc[idx, 'std_p2'] = p2_mean_std
        flagged.loc[idx, 'std_p1_volatility'] = p1_volatility
        flagged.loc[idx, 'std_p2_volatility'] = p2_volatility

        # --- The new intelligent flagging logic ---
        # Check if ANY panel exceeds the threshold
        if p1_mean_std > threshold or p2_mean_std > threshold:
            # Case A: High average spread, BUT it's stable (volatility < 0.3)
            if p1_volatility < 0.3 and p2_volatility < 0.3:
                flagged.loc[idx, 'flag'] = 'stable_offset (likely real gradient)'
            # Case B: High average spread AND it wobbles (volatility > 0.5)
            elif p1_volatility > 0.5 or p2_volatility > 0.5:
                flagged.loc[idx, 'flag'] = 'erratic_wobble (intermittent glitch)'
            else:
                flagged.loc[idx, 'flag'] = 'high_variance'

        # BONUS: Catch the "intermittent spike" scenario (low average, but high volatility)
        # This catches cases where the average spread is < threshold, but the spread jumps wildly.
        elif p1_volatility > 0.5 or p2_volatility > 0.5:
            flagged.loc[idx, 'flag'] = 'hidden_spikes (low avg but unstable)'

    return flagged


# ============================================================
# PLOTTING HELPER
# ============================================================

def _time_axis(ax):
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    ax.figure.autofmt_xdate()
    ax.grid(True, alpha=0.3)


def plot_panel_avg_with_status(ax, df, avg_col, status_col, panel_label):
    for status, color in COLORS.items():
        mask = df[status_col] == status
        sub  = df[mask]
        if sub.empty:
            continue
        if status == 'dropped':
            # Dropped timestamps as red crosses at the bottom of axis
            ax.scatter(sub['DateTime'],
                       [ax.get_ylim()[0] + 1] * len(sub),
                       color=color, marker='x', s=30, zorder=3,
                       label=f'Dropped timestamp ({len(sub)})')
        else:
            label_map = {
                'all_ok':      f'All sensors agreed ({mask.sum()})',
                'one_dropped': f'One sensor dropped ({mask.sum()})',
                'two_sensors': f'2 sensors, agreed ({mask.sum()})',
            }
            ax.scatter(sub['DateTime'], sub[avg_col],
                       color=color, s=12, zorder=3, label=label_map[status])
            ax.plot(sub['DateTime'], sub[avg_col],
                    color=color, linewidth=0.8, alpha=0.5)
    ax.set_title(panel_label, fontsize=11)
    ax.set_ylabel('Temperature (°C)')
    ax.legend(fontsize=8, loc='upper right')
    _time_axis(ax)


# ============================================================
# MAIN
# ============================================================

def main():
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

    # ----- Load files -----
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

    combined_df = pd.concat(df_list).sort_values('DateTime').reset_index(drop=True)
    print(f"\nCombined dataset: {len(combined_df)} rows after hard-limit filtering.")

    # ----- Step 2: Lag correction -----
    print("Step 2: Applying lag correction (detecting reconnecting/stabilising sensors)...")
    combined_df = apply_lag_correction(combined_df, PANEL_1_CHANNELS)
    combined_df = apply_lag_correction(combined_df, PANEL_2_CHANNELS)

    # ----- Step 3: within-panel cluster filter (now with uncertainty) -----
    print("Step 3: within-panel cluster filter ...")
    p1_avg, p1_std, p1_n, p1_status, p1_summary = apply_within_panel_filter(
        combined_df, PANEL_1_CHANNELS, "Panel 1")
    p2_avg, p2_std, p2_n, p2_status, p2_summary = apply_within_panel_filter(
        combined_df, PANEL_2_CHANNELS, "Panel 2")

    combined_df['Panel_1_Avg'] = p1_avg
    combined_df['Panel_1_Std'] = p1_std
    combined_df['Panel_1_N']   = p1_n
    combined_df['Panel_1_Status'] = p1_status

    combined_df['Panel_2_Avg'] = p2_avg
    combined_df['Panel_2_Std'] = p2_std
    combined_df['Panel_2_N']   = p2_n
    combined_df['Panel_2_Status'] = p2_status

    combined_df['Diff'] = combined_df['Panel_1_Avg'] - combined_df['Panel_2_Avg']

    # Standard Error of the Mean (instantaneous)
    combined_df['Panel_1_SEM'] = combined_df['Panel_1_Std'] / np.sqrt(combined_df['Panel_1_N'])
    combined_df['Panel_2_SEM'] = combined_df['Panel_2_Std'] / np.sqrt(combined_df['Panel_2_N'])

    # ----- Report (outlier details) -----
    report = format_report(date_input, p1_summary, p2_summary)
    print(report)

    # ============================================================
    # RUN INTERVAL ANALYSIS FOR BOTH DIRECTIONS + UPGRADED QUALITY FLAGS
    # ============================================================
    df_pos, df_neg = get_run_intervals(combined_df)

    def process_run_df(run_df, label, direction_name):
        if run_df.empty:
            print(f"\nNo runs where {direction_name}.\n")
            return None, None

        panel1_cols = [f"Channel - {ch}" for ch in PANEL_1_CHANNELS if f"Channel - {ch}" in combined_df.columns]
        panel2_cols = [f"Channel - {ch}" for ch in PANEL_2_CHANNELS if f"Channel - {ch}" in combined_df.columns]
        flagged_df = flag_noisy_runs(run_df, combined_df, panel1_cols, panel2_cols, threshold=1.5)

        total_rows = flagged_df['length'].sum()
        print(f"\n{'='*62}")
        print(f"CONTINUOUS RUNS: {direction_name}")
        print(f"{'='*62}")
        print(f"Total timestamps in runs: {total_rows}")
        for file in flagged_df['File'].unique():
            sub = flagged_df[flagged_df['File'] == file]
            total_here = sub['length'].sum()
            print(f"\n  {file}: {len(sub)} runs, total {total_here} rows")
            for idx, row in sub.head(5).iterrows():
                flag_str = f"  [{row['flag']}]" if row['flag'] else ""
                print(f"    Run {row['run_number']}: {row['start_time']}  →  {row['end_time']}  (length {row['length']}){flag_str}")
            if len(sub) > 5:
                print(f"    ... and {len(sub)-5} more runs (see detailed CSV).")
        print("")

        csv_path = os.path.join(OUTPUT_DIR, f"continuous_runs_{label}.csv")
        flagged_df.to_csv(csv_path, index=False)
        print(f"Detailed run intervals (with upgraded flags) saved to: {csv_path}")

        # Also save a text summary (with flag symbols)
        summary_lines = []
        for file in flagged_df['File'].unique():
            sub = flagged_df[flagged_df['File'] == file]
            run_str_list = []
            for _, row in sub.iterrows():
                if row['flag']:
                    run_str_list.append(f"{row['length']}*")
                else:
                    run_str_list.append(str(row['length']))
            run_str = ', '.join(run_str_list)
            summary_lines.append(f"  {file}: runs = [{run_str}]  (total {sub['length'].sum()} rows)")
        summary_text = "\n".join([
            "",
            f"CONTINUOUS RUNS: {direction_name}",
            "="*62,
            f"Total timestamps: {total_rows}",
            "(* = flagged run - check the CSV for specific reason)",
            "Per file:",
        ] + summary_lines + [""])
        txt_path = os.path.join(OUTPUT_DIR, f"continuous_runs_{label}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print(f"Text summary saved to: {txt_path}")

        return summary_text, flagged_df

    summary_pos, flagged_pos = process_run_df(df_pos, "p2_colder", "Panel 2 colder than Panel 1")
    summary_neg, flagged_neg = process_run_df(df_neg, "p1_colder", "Panel 1 colder than Panel 2")
    run_summary_text = (summary_pos or "") + "\n" + (summary_neg or "")

    # ============================================================
    # STATISTICAL ANALYSIS (including overall uncertainty)
    # ============================================================
    diff_clean = combined_df['Diff'].dropna()
    if len(diff_clean) < 2:
        print("Not enough valid data points for statistics.")
        return

    mean_diff = diff_clean.mean()
    std_diff  = diff_clean.std()
    n         = len(diff_clean)

    if mean_diff > 0:
        diff_statement = f"Panel 1 averaged {abs(mean_diff):.3f} °C warmer than Panel 2."
    elif mean_diff < 0:
        diff_statement = f"Panel 2 averaged {abs(mean_diff):.3f} °C warmer than Panel 1."
    else:
        diff_statement = "Both panels averaged the same temperature."

    t_stat, p_val, df_adj, hac_se = newey_west_t_test(diff_clean)

    s1 = combined_df['Panel_1_Avg'].dropna().std()
    s2 = combined_df['Panel_2_Avg'].dropna().std()
    pooled_std = np.sqrt((s1**2 + s2**2) / 2) if (s1 > 0 and s2 > 0) else np.nan
    effect_size = mean_diff / pooled_std if (pooled_std and not np.isnan(pooled_std)) else np.nan

    combined_df['Time_sec'] = (
        combined_df['DateTime'] - combined_df['DateTime'].iloc[0]
    ).dt.total_seconds()
    valid_reg = combined_df[['Panel_1_Avg', 'Panel_2_Avg', 'Time_sec']].dropna()
    if len(valid_reg) > 5:
        X_reg = sm.add_constant(valid_reg[['Time_sec']])
        y_reg = valid_reg['Panel_1_Avg'] - valid_reg['Panel_2_Avg']
        time_mdl = sm.OLS(y_reg, X_reg).fit()
        time_coef = time_mdl.params['Time_sec']
        time_p = time_mdl.pvalues['Time_sec']
    else:
        time_coef, time_p = np.nan, np.nan

    def _effect_label(d):
        if np.isnan(d): return "N/A"
        d = abs(d)
        if d < 0.2: return "negligible"
        if d < 0.5: return "small"
        if d < 0.8: return "medium"
        return "large"

    # Compute 95% CI for the mean difference
    ci_lower = mean_diff - 1.96 * hac_se if not np.isnan(hac_se) else np.nan
    ci_upper = mean_diff + 1.96 * hac_se if not np.isnan(hac_se) else np.nan

    results_text = f"""
==================================================
TEMPERATURE COMPARISON: PANEL 1 vs PANEL 2
==================================================
Date                    : {date_input}
Hard limits             : [{LOWER_THRESHOLD}, {UPPER_THRESHOLD}] °C
Max spread (3-4 sensors): {MAX_SPREAD_4} °C
Max spread (2 sensors)  : {MAX_SPREAD_2} °C
Data points (n)         : {n}

DESCRIPTIVE STATISTICS:
  Mean Panel 1 avg          : {combined_df['Panel_1_Avg'].mean():.3f} °C
  Mean Panel 2 avg          : {combined_df['Panel_2_Avg'].mean():.3f} °C
  Mean difference (P1 - P2) : {mean_diff:.3f} °C
  Std deviation of diff     : {std_diff:.3f} °C
  {diff_statement}

UNCERTAINTY:
  Instantaneous uncertainty (average SEM):
    Panel 1: ±{combined_df['Panel_1_SEM'].mean():.3f} °C
    Panel 2: ±{combined_df['Panel_2_SEM'].mean():.3f} °C
  Overall uncertainty (Newey-West HAC standard error of mean diff):
    ±{hac_se:.4f} °C
  95% Confidence Interval for mean diff:
    [{ci_lower:.4f}, {ci_upper:.4f}] °C

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

    # Save full report
    full_report = report + run_summary_text + results_text
    stats_path = os.path.join(OUTPUT_DIR, "statistical_comparison.txt")
    with open(stats_path, 'w', encoding='utf-8') as f:
        f.write(full_report)
    print(f"Full report saved to: {stats_path}")

    # ============================================================
    # PLOTS
    # ============================================================

    # Plot 1 — panel averages with colour-coded status
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    for ax, avg_col, status_col, panel_label in [
        (axes[0], 'Panel_1_Avg', 'Panel_1_Status', 'Panel 1  (channels 3, 4, 5, 7)'),
        (axes[1], 'Panel_2_Avg', 'Panel_2_Status', 'Panel 2  (channels 9, 10, 11, 12)'),
    ]:
        ax.set_ylim(LOWER_THRESHOLD - 3, UPPER_THRESHOLD + 3)
        plot_panel_avg_with_status(ax, combined_df, avg_col, status_col, panel_label)

    legend_text = (
        f"■ Blue   = all sensors agreed\n"
        f"■ Orange = one sensor dropped, averaged from 3\n"
        f"■ Green  = 2 sensors active, agreed (diff ≤ {MAX_SPREAD_2} °C)\n"
        f"✕ Red    = timestamp dropped entirely"
    )
    fig.text(0.01, 0.01, legend_text, fontsize=8,
             verticalalignment='bottom',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    fig.suptitle('Panel average temperatures — colour coded by data quality',
                 fontsize=13, fontweight='bold')
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    p = os.path.join(OUTPUT_DIR, "panel_averages_colour_coded.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Colour-coded panel plot saved to: {p}")

    # Plot 2 — difference over time
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(combined_df['DateTime'], combined_df['Diff'],
            color='#1f77b4', linewidth=1.5, alpha=0.9, label='P1 − P2')
    ax.axhline(0, color='grey', linestyle=':', linewidth=1)
    ax.axhline(mean_diff, color='red', linestyle='--', linewidth=1.5,
               label=f'Mean = {mean_diff:.2f} °C')
    ax.set_xlabel('Time')
    ax.set_ylabel('Panel 1 − Panel 2  (°C)')
    ax.set_title('Temperature difference between panels over time')
    ax.legend(fontsize=9)
    _time_axis(ax)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "temperature_difference.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Difference plot saved to: {p}")

    # Plot 3 — distribution of differences
    fig, ax = plt.subplots(figsize=(8, 4))
    diff_clean.hist(bins=30, ax=ax, color='steelblue', edgecolor='white',
                    alpha=0.8, density=True)
    diff_clean.plot(kind='kde', ax=ax, color='navy', linewidth=2)
    ax.axvline(mean_diff, color='red', linestyle='--', linewidth=1.5,
               label=f'Mean = {mean_diff:.2f} °C')
    ax.axvline(0, color='grey', linestyle=':', linewidth=1, label='Zero')
    ax.set_xlabel('Panel 1 − Panel 2  (°C)')
    ax.set_ylabel('Density')
    ax.set_title('Distribution of temperature differences (post-filter)')
    ax.legend()
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "difference_distribution.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Distribution plot saved to: {p}")

    # Plot 4 — individual channels vs panel average
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    ch_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    for ax, (panel_label, channels, avg_col) in zip(axes, [
        ("Panel 1  (channels 3, 4, 5, 7)",    PANEL_1_CHANNELS, 'Panel_1_Avg'),
        ("Panel 2  (channels 9, 10, 11, 12)",  PANEL_2_CHANNELS, 'Panel_2_Avg'),
    ]):
        for ch, col in zip(channels, ch_colors):
            cname = f"Channel - {ch}"
            if cname in combined_df.columns:
                ax.plot(combined_df['DateTime'], combined_df[cname],
                        color=col, alpha=0.45, linewidth=1, label=f'Ch {ch}')
        ax.plot(combined_df['DateTime'], combined_df[avg_col],
                color='black', linewidth=2, label='Panel average (filtered)')
        ax.set_title(panel_label, fontsize=11)
        ax.set_ylabel('°C')
        ax.legend(fontsize=9, loc='upper right')
        _time_axis(ax)
    plt.suptitle('Individual channel readings vs filtered panel average',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "channels_vs_panel_average.png")
    plt.savefig(p, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Channel detail plot saved to: {p}")

    # ============================================================
    # ==== NEW PLOT 5: Difference vs Standard Deviation (Sensor Spread) ====
    # ============================================================
        # ============================================================
    # PLOT 5 — Time series with rolling average (smooth)
    # ============================================================
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Drop rows where Diff or Std is NaN
    plot_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std'])
    
    # --- Calculate rolling averages (smoothing) ---
    # Adjust window size: 60 data points = ~1 minute (if 1 reading/sec), 
    # but you can change it based on your sampling rate.
    WINDOW = 60  
    plot_data = plot_data.copy()
    plot_data['Diff_smooth'] = plot_data['Diff'].rolling(window=WINDOW, center=True, min_periods=10).mean()
    plot_data['P1_std_smooth'] = plot_data['Panel_1_Std'].rolling(window=WINDOW, center=True, min_periods=10).mean()
    plot_data['P2_std_smooth'] = plot_data['Panel_2_Std'].rolling(window=WINDOW, center=True, min_periods=10).mean()
    
    # --- Left Y-axis: Temperature Difference ---
    color1 = 'tab:blue'
    ax1.set_xlabel('Time', fontsize=11)
    ax1.set_ylabel('Temperature Difference P1 - P2 (°C)', color=color1, fontsize=11)
    
    # Plot RAW diff as a thin, transparent line (for context)
    ax1.plot(plot_data['DateTime'], plot_data['Diff'], 
             color=color1, linewidth=0.5, alpha=0.3, label='Diff (raw)')
    # Plot SMOOTH diff as a thick, opaque line (the trend)
    ax1.plot(plot_data['DateTime'], plot_data['Diff_smooth'], 
             color='darkblue', linewidth=2.5, alpha=1, label='Diff (smooth, 60pt avg)')
    ax1.axhline(0, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    ax1.tick_params(axis='y', labelcolor=color1)
    
    # --- Right Y-axis: Standard Deviation (sensor spread) ---
    ax2 = ax1.twinx()
    ax2.set_ylabel('Sensor Standard Deviation (°C)', color='tab:orange', fontsize=11)
    
    # RAW spreads (thin, transparent)
    ax2.plot(plot_data['DateTime'], plot_data['Panel_1_Std'], 
             color='tab:orange', linewidth=0.5, alpha=0.2, label='P1 Std (raw)')
    ax2.plot(plot_data['DateTime'], plot_data['Panel_2_Std'], 
             color='tab:green', linewidth=0.5, alpha=0.2, label='P2 Std (raw)')
    
    # SMOOTH spreads (thick, solid)
    ax2.plot(plot_data['DateTime'], plot_data['P1_std_smooth'], 
             color='darkorange', linewidth=2, alpha=0.9, label='P1 Std (smooth)')
    ax2.plot(plot_data['DateTime'], plot_data['P2_std_smooth'], 
             color='darkgreen', linewidth=2, alpha=0.9, label='P2 Std (smooth)')
    
    # Flagging threshold (1.5 °C)
    ax2.axhline(1.5, color='red', linestyle='--', linewidth=1.5, alpha=0.7, 
                label='Variance flag threshold (1.5 °C)')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    # --- Legend & Title ---
    ax1.set_title('Temperature Difference & Sensor Spread (with 60‑point rolling average)', 
                  fontsize=14, fontweight='bold')
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
    
    _time_axis(ax1)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "temperature_diff_vs_spread_smooth.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Smoothed Diff vs Spread plot saved to: {p}")

    # ============================================================
    # PLOT 6 — Scatter: Difference vs Maximum Sensor Spread
    # ============================================================
    # This plot eliminates time entirely and shows the *quality* of the data.
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Calculate the maximum spread between the two panels at each timestamp
    scatter_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std']).copy()
    scatter_data['Max_Spread'] = scatter_data[['Panel_1_Std', 'Panel_2_Std']].max(axis=1)
    
    # Create a density scatter plot (alpha for transparency)
    # Color points by whether the spread is above or below the threshold
    mask_low = scatter_data['Max_Spread'] <= 1.5
    mask_high = scatter_data['Max_Spread'] > 1.5
    
    # Plot low-spread points (clean data) in blue
    ax.scatter(scatter_data.loc[mask_low, 'Diff'], 
               scatter_data.loc[mask_low, 'Max_Spread'],
               c='#1f77b4', s=8, alpha=0.4, label='Spread ≤ 1.5 °C (clean)')
    
    # Plot high-spread points (flagged data) in red
    ax.scatter(scatter_data.loc[mask_high, 'Diff'], 
               scatter_data.loc[mask_high, 'Max_Spread'],
               c='#d62728', s=8, alpha=0.6, label='Spread > 1.5 °C (flagged)')
    
    # Add vertical line at zero difference
    ax.axvline(0, color='grey', linestyle=':', linewidth=1, alpha=0.7)
    # Add horizontal line at the threshold
    ax.axhline(1.5, color='red', linestyle='--', linewidth=1.5, alpha=0.7, 
               label='Flag threshold')
    
    ax.set_xlabel('Temperature Difference P1 − P2 (°C)', fontsize=12)
    ax.set_ylabel('Maximum Sensor Spread (Std Dev, °C)', fontsize=12)
    ax.set_title('Data Quality Diagnostic: Difference vs Sensor Agreement', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "diff_vs_spread_scatter.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Scatter diagnostic plot saved to: {p}")

        # ============================================================
    # PLOT 7 — Sensitivity Curve (Conservative vs Liberal Dial)
    # ============================================================
    # How does the mean difference and data retention change with SD threshold?
    scatter_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std']).copy()
    scatter_data['Max_Spread'] = scatter_data[['Panel_1_Std', 'Panel_2_Std']].max(axis=1)
    
    thresholds = np.linspace(0.1, 5.0, 50)
    mean_diffs = []
    counts = []
    
    for thresh in thresholds:
        filtered = scatter_data[scatter_data['Max_Spread'] <= thresh]
        mean_diffs.append(filtered['Diff'].mean())
        counts.append(len(filtered))
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Left Y-axis: Mean Difference
    color1 = 'tab:blue'
    ax1.set_xlabel('Sensor Spread Threshold (Max Std Dev, °C)', fontsize=12)
    ax1.set_ylabel('Mean Temperature Difference P1 − P2 (°C)', color=color1, fontsize=12)
    ax1.plot(thresholds, mean_diffs, color=color1, linewidth=2.5, marker='o', markersize=4, label='Mean Diff')
    ax1.axhline(scatter_data['Diff'].mean(), color='grey', linestyle='--', alpha=0.5, label='Overall Mean (no filter)')
    ax1.tick_params(axis='y', labelcolor=color1)
    
    # Right Y-axis: Number of timestamps kept
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Number of Timestamps Kept', color=color2, fontsize=12)
    ax2.plot(thresholds, counts, color=color2, linewidth=2, linestyle='--', marker='s', markersize=4, label='Data retained')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Add a vertical line at the current threshold (1.5 °C)
    ax1.axvline(1.5, color='green', linestyle=':', linewidth=2, alpha=0.8, label='Current threshold (1.5 °C)')
    
    # Title and legend
    ax1.set_title('Sensitivity Analysis: How the SD Threshold (Dial) Affects Your Result', 
                  fontsize=14, fontweight='bold')
    
    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)
    
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "sensitivity_curve.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Sensitivity curve saved to: {p}")


        # ============================================================
    # PLOT 8 — Temporal Coverage Heatmap
    # ============================================================
    # This shows if your threshold kills specific times of the day.
    scatter_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std']).copy()
    scatter_data['Max_Spread'] = scatter_data[['Panel_1_Std', 'Panel_2_Std']].max(axis=1)
    
    # Extract fractional hour (e.g., 10.5 for 10:30)
    scatter_data['Hour'] = scatter_data['DateTime'].dt.hour + scatter_data['DateTime'].dt.minute / 60.0
    
    # Define bins for the 2D histogram
    hour_bins = np.arange(0, 24.5, 0.5)          # 30-minute bins across the day
    thresh_bins = np.arange(0.1, 5.1, 0.25)     # Threshold from 0.1 to 5.0 °C
    
    # Create 2D histogram: Time (x) vs Threshold (y)
    H, x_edges, y_edges = np.histogram2d(
        scatter_data['Hour'], 
        scatter_data['Max_Spread'], 
        bins=[hour_bins, thresh_bins]
    )
    
    fig, ax = plt.subplots(figsize=(14, 6))
    # Plot the heatmap (transpose H so Y-axis is threshold)
    im = ax.pcolormesh(x_edges, y_edges, H.T, cmap='viridis', shading='auto')
    
    # Highlight the current threshold (1.5 °C)
    ax.axhline(1.5, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Current threshold (1.5 °C)')
    
    ax.set_xlabel('Time of Day (Hours)', fontsize=12)
    ax.set_ylabel('SD Threshold (Max Std Dev, °C)', fontsize=12)
    ax.set_title('Temporal Coverage Heatmap: Does your threshold bias the time of day?', 
                 fontsize=14, fontweight='bold')
    
    # Set x-ticks to show every 2 hours for readability
    ax.set_xticks(np.arange(0, 25, 2))
    ax.set_xticklabels([f'{int(h):02d}:00' for h in np.arange(0, 25, 2)])
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Number of Datapoints Retained', fontsize=11)
    ax.legend(loc='upper right')
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "temporal_coverage_heatmap.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Temporal coverage heatmap saved to: {p}")

    # ============================================================
    # PLOT 9 — Active Hours Coverage Curve
    # ============================================================
    # This shows how many unique hours of the day have data as you turn the dial.
        # ============================================================
    # PLOT 9 — Active Hours Coverage Curve (FIXED)
    # ============================================================
    # This shows how many unique hours of the day have data as you turn the dial.
    
    # Ensure DateTime is actually a datetime object
        # ============================================================
    # PLOT 9 — Active Hours Coverage Curve (FIXED)
    # ============================================================
    # This shows how many unique hours of the day have data as you turn the dial.
    
    # Ensure we have a clean copy with all needed columns
    scatter_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std']).copy()
    
    # --- CRITICAL FIX: Add the Max_Spread column ---
    scatter_data['Max_Spread'] = scatter_data[['Panel_1_Std', 'Panel_2_Std']].max(axis=1)
    
    # Ensure DateTime is actually a datetime object
    if not pd.api.types.is_datetime64_any_dtype(scatter_data['DateTime']):
        scatter_data['DateTime'] = pd.to_datetime(scatter_data['DateTime'])
    
    # Extract fractional hour (e.g., 10.5 for 10:30)
    scatter_data['Hour'] = scatter_data['DateTime'].dt.hour + scatter_data['DateTime'].dt.minute / 60.0
    
    # Debug prints (these will show up in the console)
    print(f"  Debug: Hour range in data: {scatter_data['Hour'].min():.1f} to {scatter_data['Hour'].max():.1f}")
    print(f"  Debug: Unique hours count: {scatter_data['Hour'].nunique()}")
    print(f"  Debug: Max_Spread range: {scatter_data['Max_Spread'].min():.2f} to {scatter_data['Max_Spread'].max():.2f} °C")
    
    thresholds = np.linspace(0.1, 5.0, 50)
    active_hours = []
    data_counts = []
    
    for thresh in thresholds:
        temp_df = scatter_data[scatter_data['Max_Spread'] <= thresh]
        if not temp_df.empty:
            # Round to nearest half-hour to count unique bins
            unique_hours = temp_df['Hour'].apply(lambda x: round(x * 2) / 2).nunique()
        else:
            unique_hours = 0
        active_hours.append(unique_hours)
        data_counts.append(len(temp_df))
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Primary Y-axis: Active Hours
    ax.plot(thresholds, active_hours, color='darkgreen', linewidth=2.5, marker='s', markersize=4, label='Active Hours')
    
    # Calculate the maximum possible half-hour bins from the actual data range
    if not scatter_data.empty:
        min_hour = scatter_data['Hour'].min()
        max_hour = scatter_data['Hour'].max()
        # Count how many unique half-hour bins exist in the full dataset
        full_hours = scatter_data['Hour'].apply(lambda x: round(x * 2) / 2).nunique()
        ax.axhline(full_hours, color='grey', linestyle='--', alpha=0.5, 
                   label=f'Max possible (from data: {full_hours} bins)')
    else:
        full_hours = 24
        ax.axhline(24, color='grey', linestyle='--', alpha=0.5, label='Max possible (24 hours)')
    
    ax.axvline(1.5, color='red', linestyle=':', linewidth=2, alpha=0.8, label='Current threshold (1.5 °C)')
    
    ax.set_xlabel('SD Threshold (Max Std Dev, °C)', fontsize=12)
    ax.set_ylabel('Number of Unique Half-Hour Bins with Data', fontsize=12)
    ax.set_title('Active Hours Coverage: How much of the day survives the filter?', 
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, full_hours * 1.1 if 'full_hours' in locals() else 25)
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "active_hours_coverage.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Active hours coverage saved to: {p}")
        # ============================================================
    # PLOT 10 — Hour-by-Hour Coverage Bar Chart
    # ============================================================
    # This shows which specific hours of the day survive the filter,
    # so you can see if the threshold biases certain times.
    
    # Use the same scatter_data (with Max_Spread already computed)
    scatter_data = combined_df.dropna(subset=['Diff', 'Panel_1_Std', 'Panel_2_Std']).copy()
    scatter_data['Max_Spread'] = scatter_data[['Panel_1_Std', 'Panel_2_Std']].max(axis=1)
    
    # Ensure DateTime is a datetime object
    if not pd.api.types.is_datetime64_any_dtype(scatter_data['DateTime']):
        scatter_data['DateTime'] = pd.to_datetime(scatter_data['DateTime'])
    
    # Extract hour (integer, e.g., 10, 11, 12, 13, 14, 15)
    scatter_data['Hour'] = scatter_data['DateTime'].dt.hour
    
    # Group by hour and count timestamps BEFORE any filter
    total_by_hour = scatter_data.groupby('Hour').size()
    
    # Now apply the current threshold (1.5 °C) and count again
    filtered_data = scatter_data[scatter_data['Max_Spread'] <= 1.5]
    kept_by_hour = filtered_data.groupby('Hour').size()
    
    # Calculate percentage retained per hour
    all_hours = sorted(total_by_hour.index.unique())
    kept_pct = []
    raw_counts = []
    
    for h in all_hours:
        total = total_by_hour.get(h, 0)
        kept = kept_by_hour.get(h, 0)
        pct = (kept / total * 100) if total > 0 else 0
        kept_pct.append(pct)
        raw_counts.append((kept, total))
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    bars = ax.bar(all_hours, kept_pct, color='steelblue', edgecolor='white', linewidth=1)
    
    # Add value labels on top of bars
    for i, (bar, (kept, total)) in enumerate(zip(bars, raw_counts)):
        height = bar.get_height()
        ax.annotate(f'{kept}/{total}\n({height:.1f}%)',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    
    ax.set_xlabel('Hour of Day (24-hour format)', fontsize=12)
    ax.set_ylabel('Percentage of Timestamps Retained (%)', fontsize=12)
    ax.set_title(f'Retention Rate by Hour (threshold = 1.5 °C)\nTotal timestamps: {len(scatter_data)}', 
                 fontsize=14, fontweight='bold')
    ax.set_ylim(0, 105)
    ax.set_xticks(all_hours)
    ax.set_xticklabels([f'{int(h):02d}:00' for h in all_hours])
    ax.axhline(50, color='red', linestyle='--', alpha=0.5, label='50% retention')
    ax.axhline(90, color='green', linestyle='--', alpha=0.5, label='90% retention')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "hour_by_hour_retention.png")
    plt.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Hour-by-hour retention plot saved to: {p}")
    # ----- Save CSV with uncertainty columns -----
    csv_path = os.path.join(OUTPUT_DIR, "temperature_averages.csv")
    combined_df[[
        'DateTime',
        'Panel_1_Avg', 'Panel_1_Std', 'Panel_1_N', 'Panel_1_SEM', 'Panel_1_Status',
        'Panel_2_Avg', 'Panel_2_Std', 'Panel_2_N', 'Panel_2_SEM', 'Panel_2_Status',
        'Diff'
    ]].to_csv(csv_path, index=False)
    print(f"Averaged data (with uncertainty) saved to: {csv_path}")
    print("\nAll outputs written successfully.")


if __name__ == "__main__":
    main()
