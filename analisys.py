import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pandas.plotting import lag_plot
from statsmodels.graphics.tsaplots import plot_acf

df = pd.read_csv('processed_cloud_data.csv')

plt.figure(figsize=(12, 10)) # Increased size
sns.heatmap(df.corr(), annot=True, cmap='coolwarm', fmt='.2f', 
            annot_kws={"size": 10}) # Adjust font size of numbers
plt.xticks(rotation=45, ha='right') # Rotate x-axis labels
plt.yticks(rotation=0)
plt.title('Correlation Matrix of Cloud Telemetry')
plt.tight_layout() # This prevents labels from being cut off
plt.show()

# plt.figure(figsize=(6, 6))
# lag_plot(df['CPU usage [%]'], lag=1)
# plt.title('Lag Plot (t vs t+1): Proving Predictability')
# plt.show()


# sns.jointplot(x='CPU usage [%]', y='Energy_Consumption_Watts', data=df, kind='hex', color='#4CB391')
# plt.suptitle('Density Analysis: Where is Energy Consumed?', y=1.02)
# plt.show()


# plt.figure(figsize=(10, 4))
# plot_acf(df['CPU usage [%]'].dropna(), lags=50)
# plt.title('Autocorrelation: How far back should our model look?')
# plt.show()