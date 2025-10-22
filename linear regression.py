import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress

# Provided irradiation data
panel_a = np.array([28.47,27.71,27.88,27.86,28.09,27.34,3.981,28.25,27.56,27.25,27.58,28.01,25.85,26.11,26.14,27.37,27.1,26.64,25.77,25.74,5.429,16.47,23.16])
panel_b = np.array([27.71,28.09,26.04,27.97,24.28,27.88,4.904,30.22,28.57,25.84,26.66,26.81,26.66,28.71,27.13,26.83,25.75,22.39,25.73,25.82,6.534,20.86,25.09])

# Perform linear regression
slope, intercept, r_value, p_value, std_err = linregress(panel_a, panel_b)

# Generate regression line
x_vals = np.array([0, 1000])
y_vals = intercept + slope * x_vals

# Create the plot with exact formatting from the image
plt.figure(figsize=(8, 6))

# Scatter plot with small black dots
plt.scatter(panel_a, panel_b, color='black', s=15, alpha=0.7)

# Regression line in red
plt.plot(x_vals, y_vals, color='red', linewidth=1.5)

# Set titles and labels exactly as in the image
plt.title('Day 2', fontsize=14, fontweight='bold', pad=20)
plt.xlabel('Panel A', fontsize=12, labelpad=10)
plt.ylabel('Panel B', fontsize=12, labelpad=10)

# Set axis limits and ticks
plt.xlim(20, 30)
plt.ylim(20, 30)
plt.xticks([20, 25])
plt.yticks([20, 25])

# Add grid lines (light gray, dashed)
plt.grid(True, color='lightgray', linestyle='--', linewidth=0.5, alpha=0.7)

# Remove top and right spines for cleaner look
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['right'].set_visible(False)

# Ensure equal aspect ratio
plt.gca().set_aspect('equal')

# Add panel labels in the top-left corner (similar to the image)
plt.text(0.02, 0.98, 'Panel B', transform=plt.gca().transAxes, 
         fontsize=12, va='top', ha='left')
plt.text(0.98, 0.02, 'Panel A', transform=plt.gca().transAxes, 
         fontsize=12, va='bottom', ha='right')

plt.tight_layout()
plt.savefig('styled_regression_plot.png', dpi=300, bbox_inches='tight')
plt.show()

print("Styled regression plot saved as 'styled_regression_plot.png'.")
