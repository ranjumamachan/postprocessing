import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import pandas as pd

# ======================
# 1. GENERATE SAMPLE DATA (REPLACE WITH YOUR DATA)


df = pd.read_excel("D:\\bricks laid\\2025 bitches\\forpy.xlsx")  # or pd.read_csv('your_file.csv')
# ======================
# Dataset 1 (Calibrated Tracer)
voltage_calib = df['Voltage_Calib'].values  # 100 points (0V to 40V)
current_calib = df['Current_Calib'].values  # Simulated IV curve (nonlinear)

# Dataset 2 (Uncalibrated Tracer - fewer points)
voltage_uncalib = df['Voltage_Uncalib'].values  # Only 30 points
current_uncalib = df['Current_Uncalib'].values  # Adds slight noise

# ======================
# 2. INTERPOLATE UNCALIBRATED DATA TO MATCH CALIBRATED VOLTAGE POINTS
# ======================
# Create interpolation function (cubic spline for smoothness)


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
plt.plot(voltage_uncalib, current_uncalib, 'ro', label='Uncalibrated (Raw)', markersize=5)
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
