
# Temperature Data Analysis and Visualization

## 📌 Overview
This Python script processes and visualizes temperature data from multiple sensor channels (grouped into two panels). It cleans the raw data, computes average temperatures for each panel, and generates time-series plots for analysis.

## 🔍 Features
- **Data Cleaning**:  
  - Converts timestamps into a standardized format.  
  - Handles outliers by filtering unrealistic temperature values (below 30°C or above 80°C).  
- **Averaging**:  
  - Computes mean temperatures for **Panel 1 (Channels 1-5)** and **Panel 2 (Channels 11-15)**.  
- **Visualization**:  
  - Plots averaged temperature trends over time for both panels in separate subplots.  
  - Customizable markers, colors, and axis limits.  

## ⚙️ Dependencies
- Python 3.x  
- Libraries:  
  ```bash
  pandas numpy matplotlib openpyxl
  ```
  Install via:  
  ```bash
  pip install pandas numpy matplotlib openpyxl
  ```

## 📂 Input Data
- **Format**: Excel file (`.xlsx`) with columns:  
  - `Date:` (e.g., `DD-MM-YYYY`)  
  - `Time:` (e.g., `HH:MM:SS`)  
  - Temperature columns named `Channel - {i}` (e.g., `Channel - 1`, `Channel - 2`, etc.).  

## 🚀 Usage
1. **Configure Path**:  
   Replace the input file path in the script:  
   ```python
   df = pd.read_excel(r"D:\\PhD\\similarity\\temperatures\\day 2\\day 2 avg.xlsx")
   ```

2. **Run Script**:  
   ```bash
   python temperature_analysis.py
   ```

3. **Output**:  
   - A plot window showing:  
     - **Top Subplot**: Panel 1 average temperature (Channels 1-5).  
     - **Bottom Subplot**: Panel 2 average temperature (Channels 11-15).  
   - Example:  
     ![Example Plot](https://via.placeholder.com/600x400?text=Panel1+and+Panel2+Temperature+Trends)  

## 🛠️ Customization
- **Adjust Thresholds**: Modify outlier limits (30°C and 80°C) in the cleaning step:  
  ```python
  df.loc[(df[channel] < 30) | (df[channel] > 80), channel] = np.nan
  ```
- **Plot Styling**: Change colors, markers, or axis limits in the `plt.plot()` calls.  
