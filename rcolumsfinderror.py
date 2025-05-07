import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import interp1d

# Load data while treating empty cells as separate datasets
df = pd.read_excel(r"D:\bricks laid\2025 bitches\forpy1.py.xlsx")

# ================================================
# 1. Process Calibrated Tracer Data
# ================================================
# Get only rows where calibrated data exists
calib_data = df[['Voltage_Calib', 'Current_Calib']].dropna()
voltage_calib = calib_data['Voltage_Calib'].values
current_calib = calib_data['Current_Calib'].values*1000

# ================================================
# 2. Process Uncalibrated Tracer Data
# ================================================
# Get only rows where uncalibrated data exists
uncalib_data = df[['Voltage_Uncalib', 'Current_Uncalib']].dropna()
voltage_uncalib = uncalib_data['Voltage_Uncalib'].values
current_uncalib = uncalib_data['Current_Uncalib'].values

#=============================================
# 3. Validate Data
# ================================================
print(f"Calibrated data points: {len(voltage_calib)}")
print(f"Uncalibrated data points: {len(voltage_uncalib)}")

if len(voltage_calib) == 0 or len(voltage_uncalib) == 0:
    raise ValueError("One or both datasets are empty after cleaning")

# ================================================
# 4. Calculate Key Parameters (for each dataset separately)
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
    
    # Print results
    print(f"\n=== {name.upper()} RESULTS ===")
    print(f"Maximum Power (Pmax): {results['Pmax']:.4f} W")
    print(f"Voltage at Pmax (Vmax): {results['Vmax']:.4f} V")
    print(f"Current at Pmax (Imax): {results['Imax']:.4f} A")
    print(f"Short Circuit Current (Isc): {results['Isc']:.4f} A")
    print(f"Open Circuit Voltage (Voc): {results['Voc']:.4f} V")
    
    return results

calib_results = calculate_iv_parameters(voltage_calib, current_calib, "CALIBRATED")
uncalib_results = calculate_iv_parameters(voltage_uncalib, current_uncalib, "UNCALIBRATED")

interp_func = interp1d(
    voltage_uncalib, 
    current_uncalib, 
    kind='cubic',  # 'linear' for faster but less smooth
    fill_value='extrapolate'  # Handles voltages outside the uncalibrated range
)
# Interpolate uncalibrated currents at calibrated voltages
interpolated_current = interp_func(voltage_calib)



# ======================
# 3. CALCULATE ERRORS
# ======================
# Absolute error (A)
absolute_error = np.abs(interpolated_current - current_calib)

# Relative error (%)
relative_error = (absolute_error / current_calib) * 100

# Avoid division by zero (if current_calib = 0)
relative_error[np.isinf(relative_error)] = 0

# Summary statistics
mean_abs_error = np.mean(absolute_error)
mean_rel_error = np.mean(relative_error)
max_rel_error = np.max(relative_error)

# ======================
# 4. PLOT RESULTS
# ======================
plt.figure(figsize=(12, 6))

# Plot IV curves
plt.subplot(1, 2, 1)
plt.plot(voltage_calib, current_calib, 'b-', label='Calibrated Tracer', linewidth=2)
plt.plot(voltage_calib, interpolated_current, 'g--', label='Uncalibrated (Interpolated)', linewidth=1.5)
plt.xlabel('Voltage (V)')
plt.ylabel('Current (A)')
plt.title('IV Curve Comparison')
plt.legend()
plt.grid(True)




# Plot relative errors
plt.subplot(1, 2, 2)
plt.plot(voltage_calib, relative_error, 'k-', label='Relative Error (%)')
plt.axhline(y=5, color='r', linestyle='--', label='5% Error Threshold')
plt.xlabel('Voltage (V)')
plt.ylabel('Error (%)')
plt.title('Relative Error Analysis')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

# ======================
# 5. PRINT ERROR STATISTICS
# ======================
print("\n===== ERROR ANALYSIS =====")
print(f"Mean Absolute Error: {mean_abs_error:.4f} A")
print(f"Mean Relative Error: {mean_rel_error:.2f} %")
print(f"Max Relative Error: {max_rel_error:.2f} %")
# 
# ================================================
# 5. Visualization (with interpolation if needed)
# ================================================
plt.figure(figsize=(14, 6))

# IV Curve Plot
plt.subplot(1, 2, 1)
plt.plot(voltage_calib, current_calib, 'b-', label='Calibrated')
plt.plot(voltage_uncalib, current_uncalib, 'ro', label='Uncalibrated')

# Mark MPP points
plt.plot(calib_results['Vmax'], calib_results['Imax'], 'bs', 
         label=f'Calib MPP ({calib_results["Vmax"]:.2f}V, {calib_results["Imax"]:.2f}A)')
plt.plot(uncalib_results['Vmax'], uncalib_results['Imax'], 'rs', 
         label=f'Uncalib MPP ({uncalib_results["Vmax"]:.2f}V, {uncalib_results["Imax"]:.2f}A)')

plt.xlabel('Voltage (V)')
plt.ylabel('Current (A)')
plt.title('IV Characteristics')
plt.legend()
plt.grid(True)

# Power Curve Plot
plt.subplot(1, 2, 2)
plt.plot(voltage_calib, voltage_calib*current_calib, 'b-', label='Calibrated Power')
plt.plot(voltage_uncalib, voltage_uncalib*current_uncalib, 'r-', label='Uncalibrated Power')

plt.xlabel('Voltage (V)')
plt.ylabel('Power (W)')
plt.title('Power Characteristics')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
