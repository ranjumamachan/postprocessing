# Temperature Data Analysis and Visualization

This Python script processes and visualizes temperature data collected from multiple channels over time. The data is read from an Excel file, filtered, and plotted to help analyze temperature trends for two panels of channels.

## Key Features

- **Data Import:** Reads data from an Excel file using `pandas`.
- **Datetime Handling:** Combines separate date and time columns into a unified timestamp, handling various data types and formats.
- **Data Cleaning:**
  - Converts temperature readings to numeric, coercing non-numeric values (like 'OPEN') to NaN.
  - Filters out temperature values outside the range 50°C to 70°C for analysis.
- **Visualization:**
  - Plots two subplots using `matplotlib`:
    - **Panel 1:** Channels 1 to 5.
    - **Panel 2:** Channels 11 to 15.
  - Each channel is plotted with distinct markers and lines.
  - X-axis represents time, Y-axis shows temperature (limited from 50°C to 70°C).
  - Legends and grid lines added for clarity.

## How It Works

1. **Read the Excel File:**  
   Loads the specified Excel file into a DataFrame.

2. **Debug Info:**  
   Prints the columns and datatypes for quick inspection.

3. **Timestamp Creation:**  
   - Handles both standard datetime and string formats for date and time.
   - Merges them into a single `Timestamp` column for plotting.

4. **Cleaning Channel Data:**  
   - Iterates over channels 1-5 and 11-15.
   - Converts values to numeric and removes any entries outside the 50-70°C range.

5. **Plotting:**  
   - Plots two separate panels (subplots) for the specified channels.
   - Each channel's data is shown with markers and lines.
   - Legends, axis labels, and grid lines are included for better interpretation.

## Usage

Edit the file path to your Excel file as needed:
```python
df = pd.read_excel(r"D:\PhD\similarity\day 1 2nd.xlsx")
```

Run the script to visualize the temperature data for the specified channels.

---

**Note:**  
- Ensure your Excel file column headers match those in the script (e.g., "Date:", "Time:", "Channel - 1", ...).
- Requires `pandas` and `matplotlib` libraries.
