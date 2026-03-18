import numpy as np
import pandas as pd
import joblib
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Import your cleaned data and feature list
from dataClean import df_final, features, target

def run_pipeline():
    print("--- 1. Data Splitting & Scaling ---")
    train_size = int(len(df_final) * 0.8)
    train, test = df_final.iloc[:train_size], df_final.iloc[train_size:]

    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    joblib.dump(scaler, 'scaler.pkl')

    print("--- 2. Model Training (RF & LSTM) ---")
    # Random Forest
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train_scaled, y_train)
    rf_preds = rf_model.predict(X_test_scaled)
    joblib.dump(rf_model, 'rf_model.joblib')

    # LSTM
    X_train_lstm = X_train_scaled.reshape((X_train_scaled.shape[0], 1, X_train_scaled.shape[1]))
    X_test_lstm = X_test_scaled.reshape((X_test_scaled.shape[0], 1, X_test_scaled.shape[1]))

    lstm_model = Sequential([
        LSTM(50, activation='relu', input_shape=(X_train_lstm.shape[1], X_train_lstm.shape[2])),
        Dropout(0.2),
        Dense(1)
    ])
    lstm_model.compile(optimizer='adam', loss='mse')
    lstm_model.fit(X_train_lstm, y_train, epochs=20, batch_size=32, verbose=0)
    lstm_preds = lstm_model.predict(X_test_lstm).flatten()
    lstm_model.save('lstm_model.h5')

    print("--- 3. Hybrid Stacking (Meta-Learner) ---")
    meta_features = np.column_stack((rf_preds, lstm_preds))
    meta_learner = LinearRegression()
    meta_learner.fit(meta_features, y_test)
    final_predictions = meta_learner.predict(meta_features)
    joblib.dump(meta_learner, 'meta_learner.joblib')

    print("--- 4. Evaluation & CSV Export ---")
    def calculate_metrics(y_true, y_pred):
        return [mean_absolute_error(y_true, y_pred), np.sqrt(mean_squared_error(y_true, y_pred)), r2_score(y_true, y_pred)]

    results = pd.DataFrame({
        'Metric': ['MAE', 'RMSE', 'R2_Score'],
        'Random Forest': calculate_metrics(y_test, rf_preds),
        'LSTM': calculate_metrics(y_test, lstm_preds),
        'Hybrid': calculate_metrics(y_test, final_predictions)
    })
    results.to_csv('model_evaluation_matrix.csv', index=False)
    print("\n[SUCCESS] Performance Matrix saved to 'model_evaluation_matrix.csv'")
    print(results)

    # Save final predictions to CSV
    output_df = test.copy()
    output_df['Actual_Energy'] = y_test
    output_df['Predicted_Energy_Hybrid'] = final_predictions


    print("--- 5. Generating Visualizations ---")
    # Plot 1: Actual vs Predicted (Time Series)
    plt.figure(figsize=(15, 6))
    plt.plot(y_test.values[:100], label='Actual Energy', color='black', linewidth=2)
    plt.plot(final_predictions[:100], label='Hybrid Prediction', color='red', linestyle='--')
    plt.title('Comparison: Actual vs Hybrid Prediction (First 100 samples)')
    plt.legend()
    plt.savefig('prediction_comparison.png')
    
    # Plot 2: Error Distribution
    plt.figure(figsize=(10, 5))
    errors = y_test.values - final_predictions
    plt.hist(errors, bins=50, color='skyblue', edgecolor='black')
    plt.title('Prediction Error Distribution (Residuals)')
    plt.xlabel('Error (Watts)')
    plt.savefig('error_distribution.png')
    
    plt.show()

if __name__ == "__main__":
    run_pipeline()