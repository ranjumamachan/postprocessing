import pandas as pd
import matplotlib.pyplot as plt

# Read Excel file
df = pd.read_excel(r"D:\PhD\similarity\day 1 2nd.xlsx")

# Debug: Print columns and data types
print("Columns in Excel:", df.columns.tolist())
print("\nData types:\n", df.dtypes)

# Fix 1: Handle datetime conversion properly
date_column = "Date:"
time_column = "Time:"

# Convert Time column to string if it's not already
df[time_column] = df[time_column].astype(str)

# Combine date and time
if pd.api.types.is_datetime64_any_dtype(df[date_column]):
    df['Timestamp'] = df[date_column] + pd.to_timedelta(df[time_column].str.extract(r'(\d+):(\d+):(\d+)').astype(float).apply(
        lambda x: f"{int(x[0])} hours {int(x[1])} minutes {int(x[2])} seconds", axis=1))
else:
    df['Timestamp'] = pd.to_datetime(df[date_column].astype(str) + ' ' + df[time_column])

# Fix 2: Handle 'OPEN' strings and filter temperatures outside 50-70°F
for i in range(1, 6):
    channel = f"Channel - {i}"
    df[channel] = pd.to_numeric(df[channel], errors='coerce')
    df[channel] = df[channel].where((df[channel] >= 50) & (df[channel] <= 70))  # Mask values <50 or >70

for i in range(11, 16):
    channel = f"Channel - {i}"
    df[channel] = pd.to_numeric(df[channel], errors='coerce')
    df[channel] = df[channel].where((df[channel] >= 50) & (df[channel] <= 70))  # Mask values <50 or >70

# Plotting
plt.figure(figsize=(14, 8))

# Panel 1 (Channels 1-5)
plt.subplot(2, 1, 1)
for i in range(1, 6):
    channel = f"Channel - {i}"
    plt.plot(df['Timestamp'], df[channel], label=channel, marker='o', markersize=3, linestyle='-')
plt.title('Panel 1 Temperature Data (50-70°C only)')
plt.ylabel('Temperature (°C)')
plt.ylim(50, 70)  # Set y-axis limits
plt.legend()
plt.grid(True)

# Panel 2 (Channels 11-15)
plt.subplot(2, 1, 2)
for i in range(11, 16):
    channel = f"Channel - {i}"
    plt.plot(df['Timestamp'], df[channel], label=channel, marker='o', markersize=3, linestyle='-')
plt.title('Panel 2 Temperature Data (50-70°C only)')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.ylim(50, 70)  # Set y-axis limits
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
