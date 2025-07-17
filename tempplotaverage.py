import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Read Excel file
df = pd.read_excel(r"D:\\PhD\\similarity\\temperatures\\day 2\\day 2 average.xlsx")

# Debug: Print columns and data types
print("Columns in Excel:", df.columns.tolist())
print("\nData types:\n", df.dtypes)

# Fix datetime conversion
date_column = "Date:"
time_column = "Time:"

# Convert to string and clean time format
df[time_column] = df[time_column].astype(str).str.replace(r'\.\d+', '', regex=True)  # Remove milliseconds if present

# Combine date and time with proper format
try:
    df['Timestamp'] = pd.to_datetime(
        df[date_column].astype(str) + ' ' + df[time_column],
        dayfirst=True,
        format='%d-%m-%Y %H:%M:%S'
    )
except ValueError:
    df['Timestamp'] = pd.to_datetime(
        df[date_column].astype(str) + ' ' + df[time_column],
        dayfirst=True,
        format='mixed'
    )

# Clean temperature data
for i in list(range(1, 6)) + list(range(11, 16)):
    channel = f"Channel - {i}"
    if channel in df.columns:
        df[channel] = pd.to_numeric(df[channel], errors='coerce')
        df.loc[(df[channel] < 30) | (df[channel] > 80), channel] = np.nan

# Calculate mean temperatures for each panel
panel1_channels = [f"Channel - {i}" for i in range(1, 6) if f"Channel - {i}" in df.columns]
panel2_channels = [f"Channel - {i}" for i in range(11, 16) if f"Channel - {i}" in df.columns]

df['Panel1_Avg'] = df[panel1_channels].mean(axis=1)  # Mean of Channels 1-5
df['Panel2_Avg'] = df[panel2_channels].mean(axis=1)  # Mean of Channels 11-15

# Plotting
plt.figure(figsize=(14, 8))

# Panel 1 Average (Channels 1-5)
plt.subplot(2, 1, 1)
plt.plot(df['Timestamp'], df['Panel1_Avg'], label='Panel 1 Average', color='blue', marker='o', markersize=3, linestyle='-')
plt.title('Panel 1 Average Temperature (Channels 1-5)')
plt.ylabel('Temperature (°C)')
plt.ylim(10, 80)
plt.legend()
plt.grid(True)

# Panel 2 Average (Channels 11-15)
plt.subplot(2, 1, 2)
plt.plot(df['Timestamp'], df['Panel2_Avg'], label='Panel 2 Average', color='red', marker='o', markersize=3, linestyle='-')
plt.title('Panel 2 Average Temperature (Channels 11-15)')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.ylim(10, 80)
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
