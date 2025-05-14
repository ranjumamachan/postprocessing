import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import interp1d

# Load and process data
df = pd.read_excel(r"D:\bricks laid\2025 bitches\forpy1.py.xlsx")

# ================================================
# 1. Process Calibrated Tracer Data with Voltage Transition Check
# ================================================
calib_data = df[['Voltage_Calib', 'Current_Calib']].dropna()
voltage_calib_raw = calib_data['Voltage_Calib'].values
current_calib_raw = calib_data['Current_Calib'].values * 1000  # mA to A

# Identify where voltage drops rapidly below 1V from above 10V
voltage_diff = np.diff(voltage_calib_raw)
abrupt_drop_indices = np.where((voltage_calib_raw[:-1] > 10) & (voltage_calib_raw[1:] < 1))[0]

if len(abrupt_drop_indices) > 0:
    cutoff_idx = abrupt_drop_indices[0]
    print(f"Warning: Found abrupt voltage drop at index {cutoff_idx} (from {voltage_calib_raw[cutoff_idx]:.2f}V to {voltage_calib_raw[cutoff_idx+1]:.2f}V)")
    voltage_calib = voltage_calib_raw[:cutoff_idx+1]
    current_calib = current_calib_raw[:cutoff_idx+1]
else:
    voltage_calib = voltage_calib_raw
    current_calib = current_calib_raw

# Further filter out any remaining low-voltage regions with current climbing
low_voltage_mask = (voltage_calib >= 1) | (current_calib < np.percentile(current_calib[voltage_calib >= 1], 90))
voltage_calib = voltage_calib[low_voltage_mask]
current_calib = current_calib[low_voltage_mask]

# ================================================
# 2. Process Uncalibrated Tracer Data
# ================================================
uncalib_data = df[['Voltage_Uncalib', 'Current_Uncalib']].dropna()
voltage_uncalib = uncalib_data['Voltage_Uncalib'].values
current_uncalib = uncalib_data['Current_Uncalib'].values

# ================================================
# 3. Data Validation
# ================================================
print(f"\nCalibrated data points (after cleaning): {len(voltage_calib)}")
print(f"Uncalibrated data points: {len(voltage_uncalib)}")

if len(voltage_calib) == 0 or len(voltage_uncalib) == 0:
    raise ValueError("One or both datasets are empty after cleaning")

# ================================================
# 4. Calculate Key Parameters
# ================================================
def calculate_iv_parameters(voltage, current, name):
    power = voltage * current
    
    max_power_idx = np.argmax(power)
    results = {
        'Pmax': power[max_power_idx],
        'Vmax': voltage[max_power_idx],
        'Imax': current[max_power_idx],
        'Isc': current[np.argmin(voltage)],
        'Voc': voltage[np.argmin(current)]
    }
    
    print(f"\n=== {name.upper()} RESULTS ===")
    print(f"Maximum Power (Pmax): {results['Pmax']:.4f} W")
    print(f"Voltage at Pmax (Vmax): {results['Vmax']:.4f} V")
    print(f"Current at Pmax (Imax): {results['Imax']:.4f} A")
    print(f"Short Circuit Current (Isc): {results['Isc']:.4f} A")
    print(f"Open Circuit Voltage (Voc): {results['Voc']:.4f} V")
    
    return results

calib_results = calculate_iv_parameters(voltage_calib, current_calib, "CALIBRATED")
uncalib_results = calculate_iv_parameters(voltage_uncalib, current_uncalib, "UNCALIBRATED")

# ================================================
# 5. Interpolation and Improved Error Analysis
# ================================================
interp_func = interp1d(
    voltage_uncalib, 
    current_uncalib, 
    kind='cubic',
    bounds_error=False,
    fill_value=(current_uncalib[0], current_uncalib[-1])
)

interpolated_current = interp_func(voltage_calib)

# Calculate absolute error (in Amperes)
absolute_error = np.abs(interpolated_current - current_calib)

# Get key parameters from calibrated data
Isc = calib_results['Isc']
Pmax = calib_results['Pmax']
Vmax = calib_results['Vmax']
Voc = calib_results['Voc']

# Define regions
mpp_mask = (voltage_calib > 0.7*Vmax) & (voltage_calib < 0.6*Voc)
isc_mask = voltage_calib < 0.1*Voc
voc_mask = voltage_calib > 0.6*Voc

# Calculate different error metrics for each region
with np.errstate(divide='ignore', invalid='ignore'):
    # MPP region - standard relative error
    mpp_error = np.zeros_like(voltage_calib)
    mpp_error[mpp_mask] = (absolute_error[mpp_mask] / current_calib[mpp_mask]) * 100
    
    # ISC region - error relative to Isc
    isc_error = np.zeros_like(voltage_calib)
    isc_error[isc_mask] = (absolute_error[isc_mask] / Isc) * 100
    
    # VOC region - absolute error in A (changed from mA)
    voc_error = absolute_error.copy()  *.001 # Now in Amperes
    
    # Combined weighted error (emphasize MPP region)
    combined_error = np.where(
        mpp_mask, 
        mpp_error,  # Full weight to MPP region
        np.where(
            isc_mask,
            isc_error * 0.5,  # Half weight to ISC region
            voc_error * 0.2    # Low weight to VOC region
        )
    )

# Calculate statistics on valid points only
valid_mask = ~np.isnan(combined_error)
mean_abs_error = np.mean(absolute_error[valid_mask])
mean_combined_error = np.mean(combined_error[valid_mask])
max_combined_error = np.max(combined_error[valid_mask])

# ================================================
# 6. Plotting
# ================================================
plt.figure(figsize=(14, 6))

# IV Curve Plot
plt.subplot(1, 2, 1)
plt.plot(voltage_calib, current_calib, 'b-', label='Calibrated (Cleaned)')
plt.plot(voltage_uncalib, current_uncalib, 'ro', label='Uncalibrated (Raw)')
plt.plot(voltage_calib, interpolated_current, 'g--', label='Uncalibrated (Interpolated)')

# Highlight regions
plt.axvspan(0.7*Vmax, 1.3*Vmax, alpha=0.1, color='green', label='MPP Region')
plt.axvspan(0, 0.1*Voc, alpha=0.1, color='red', label='ISC Region')
plt.axvspan(0.9*Voc, max(voltage_calib), alpha=0.1, color='blue', label='VOC Region')

plt.xlabel('Voltage (V)')
plt.ylabel('Current (mA)')
plt.title('IV Curve with Analysis Regions')
plt.legend()
plt.grid(True)

# Error Plot
plt.subplot(1, 2, 2)
plt.plot(voltage_calib[mpp_mask], mpp_error[mpp_mask], 'g-', label='MPP Error (%)')
plt.plot(voltage_calib[isc_mask], isc_error[isc_mask], 'r-', label='ISC Error (% of Isc)')
plt.plot(voltage_calib[voc_mask], voc_error[voc_mask], 'b-', label='VOC Error (A)')  # Changed from mA to A
plt.plot(voltage_calib, combined_error, 'k--', label='Combined Weighted Error', linewidth=1)
plt.axhline(y=5, color='gray', linestyle='--', label='5% Threshold')
plt.xlabel('Voltage (V)')
plt.ylabel('Error')
plt.title('Region-Specific Error Analysis')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

# ================================================
# 7. Results Output
# ================================================
print("\n===== COMPREHENSIVE ERROR ANALYSIS =====")
print(f"Valid data points: {sum(valid_mask)}/{len(voltage_calib)}")
print(f"\n--- Absolute Errors ---")
print(f"Mean Absolute Error: {mean_abs_error:.4f} A")  # Changed from mA to A

print(f"\n--- Region-Specific Errors ---")
print(f"MPP Region (Relative): Mean = {np.mean(mpp_error[mpp_mask]):.2f}%, Max = {np.max(mpp_error[mpp_mask]):.2f}%")
print(f"ISC Region (% of Isc): Mean = {np.mean(isc_error[isc_mask]):.2f}%, Max = {np.max(isc_error[isc_mask]):.2f}%")
print(f"VOC Region (Absolute): Mean = {np.mean(voc_error[voc_mask]):.4f} A, Max = {np.max(voc_error[voc_mask]):.4f} A")  # Changed from mA to A

print(f"\n--- Combined Weighted Error ---")
print(f"Mean: {mean_combined_error:.2f}")
print(f"Max: {max_combined_error:.2f}")
