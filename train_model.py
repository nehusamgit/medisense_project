import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

def train_diabetes_risk_model():
    print("Loading cleaned dataset...")
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    cleaned_path = os.path.join(data_dir, 'cdc_diabetes_cleaned.csv')
    
    # Load the dataset
    df = pd.read_csv(cleaned_path)
    
    # Define what we are trying to predict (Target)
    # The CDC dataset has 'Diabetes_binary' where 0 = No Diabetes, 1 = Prediabetes/Diabetes
    target_column = 'Diabetes_binary'
    
    print(f"Target variable: {target_column}")
    
    # Define our Features (X) and Target (y)
    # We drop the target column from our features
    y = df[target_column]
    X = df.drop(columns=[target_column])
    
    # Split the data: 80% for training, 20% for testing
    print("Splitting data into Training and Testing sets (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Initialize the Machine Learning Algorithm
    # We use a Random Forest because it handles medical/tabular data extremely well and doesn't overfit easily
    print("Training Random Forest Classifier... (This might take a minute or two)")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    
    # Train the model
    model.fit(X_train, y_train)
    
    # Test the model on the 20% unseen data
    print("Evaluating model performance...")
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save the trained model to a file so Django can use it
    model_path = os.path.join(data_dir, 'diabetes_risk_model.pkl')
    joblib.dump(model, model_path)
    print(f"\nSuccess! Trained model saved to: {model_path}")
    
    # Also save a list of the exact feature columns the model expects
    # This is crucial so we pass the right inputs from Django later
    features_path = os.path.join(data_dir, 'model_features.pkl')
    joblib.dump(list(X.columns), features_path)
    print(f"Expected model features saved to: {features_path}")

if __name__ == "__main__":
    train_diabetes_risk_model()
