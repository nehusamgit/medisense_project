import pandas as pd
from ucimlrepo import fetch_ucirepo 
import os

def download_and_clean_data():
    print("Fetching dataset from UCI...")
    # fetch dataset 
    cdc_diabetes_health_indicators = fetch_ucirepo(id=891) 
    
    # data (as pandas dataframes) 
    X = cdc_diabetes_health_indicators.data.features 
    y = cdc_diabetes_health_indicators.data.targets 

    print("Data fetched successfully!")
    print(f"Features shape: {X.shape}")
    
    # Combine into a single dataframe
    df = pd.concat([X, y], axis=1)
    
    # Save the raw data
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    raw_path = os.path.join(data_dir, 'cdc_diabetes_raw.csv')
    df.to_csv(raw_path, index=False)
    print(f"Raw data saved to {raw_path}")
    
    # --- Cleaning & Preprocessing ---
    print("Cleaning data...")
    # The CDC dataset has 21 features. Let's filter to the ones most relevant 
    # to the vitals we collect in our app (if possible), or keep the most important ones for risk assessment.
    
    # Here is what our app tracks: Age, Systolic BP, Diastolic BP, Heart Rate, Blood Sugar, SpO2.
    # The CDC dataset has HighBP, HighChol, BMI, Smoker, Stroke, HeartDiseaseorAttack, etc.
    # It doesn't have exact Systolic/Diastolic/SpO2 values (it's survey data). 
    # For a real ML model matching our EXACT vitals, we often have to map features or use a synthetic generator
    # trained on the distributions of real data.
    
    # For this proof of concept based on your guide's rule (real data only), 
    # we will use the CDC data to predict "HeartDiseaseorAttack" or "Diabetes_binary" 
    # based on the patient's HighBP, BMI, Age, etc.
    
    cleaned_path = os.path.join(data_dir, 'cdc_diabetes_cleaned.csv')
    df.dropna(inplace=True) # Basic cleaning: drop missing rows
    df.to_csv(cleaned_path, index=False)
    print(f"Cleaned data saved to {cleaned_path}")

if __name__ == "__main__":
    download_and_clean_data()
