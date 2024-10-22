# -*- coding: utf-8 -*-
"""Waze_App.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1QYx5rAGhX1XjYUfaW7WEOkCS8dUV2ab8
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import requests
import io
from sklearn.metrics import classification_report

# Function to load .pkl files from a GitHub URL
def load_pickle_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        print(response.text)  # Debugging line to print fetched content
        file_content = io.BytesIO(response.content)
        return pickle.load(file_content)
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to load the file from {url}: {e}")
        return None
    except pickle.UnpicklingError as e:
        st.error(f"Error unpickling the file: {e}")
        return None

# Load the scaler and model using the custom function
scaler = load_pickle_from_url('https://github.com/ManarM7md/Waze-Project/raw/main/scaler.pkl')
model, selector = load_pickle_from_url('https://github.com/ManarM7md/Waze-Project/raw/main/lasso_model_and_selector.pkl')
logistic_regression_model = load_pickle_from_url('https://github.com/ManarM7md/Waze-Project/raw/main/logistic_regression_model.pkl')

# Ensure the loaded selector is a SelectFromModel instance
if not isinstance(selector, lasso_model_and_selector):
    st.error("Loaded selector is not of type SelectFromModel.")
    return None

def segment_users(row, median_sessions, median_sessions_2, median_sessions_3, median_sessions_4):
    """Segment users based on engagement levels."""
    if (row['sessions'] > median_sessions and
        row['total_navigations_fav1'] >= median_sessions_2 and
        row['n_days_after_onboarding'] >= median_sessions_3 and
        row['drives'] <= median_sessions_4):
        return 'High Engagement'
    return 'Low Engagement'

def segment_driving_days(row, median_sessions, median_sessions_2):
    """Segment users based on day levels."""
    if row['activity_days'] <= median_sessions and row['driving_days'] <= median_sessions_2:
        return 'High day'
    return 'Low day'

def preprocess_dataframe(df):
    """Preprocess the input DataFrame."""
    columns_to_drop = ['ID', 'device']
    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    df.drop(columns=existing_columns_to_drop, inplace=True)
    return df

def make_predictions(df):
    """Make predictions based on the provided DataFrame."""
    if df is None or df.empty:
        st.error("Input DataFrame is empty or not provided.")
        return None

    X_test = df.drop('label', axis=1, errors='ignore')
    
    # Segmenting engagement levels and day levels
    X_test['engagement_level'] = X_test.apply(segment_users, axis=1, args=(
        X_test['sessions'].median(),
        X_test['total_navigations_fav1'].median(),
        X_test['n_days_after_onboarding'].median(),
        X_test['drives'].median()
    ))

    X_test['day_level'] = X_test.apply(segment_driving_days, axis=1, args=(
        X_test['activity_days'].median(),
        X_test['driving_days'].median()
    ))

    # Calculating new features
    X_test['activity_ratio'] = X_test['driving_days'] / X_test['activity_days'].replace(0, np.nan)
    X_test['avg_distance_per_drive'] = X_test['driven_km_drives'] / X_test['drives'].replace(0, np.nan)
    X_test['engagement_ratio'] = X_test['total_sessions'] / X_test['driving_days'].replace(0, np.nan)
    X_test['avg_navigations_fav'] = (X_test['total_navigations_fav1'] + X_test['total_navigations_fav2']) / 2

    # Filling NaN values
    for col in ['activity_ratio', 'avg_distance_per_drive', 'engagement_ratio', 'avg_navigations_fav']:
        X_test[col] = X_test[col].fillna(X_test[col].median())

    # Mapping engagement and day levels to numerical values
    X_test['engagement_level'] = X_test['engagement_level'].map({'Low Engagement': 0, 'High Engagement': 1})
    X_test['day_level'] = X_test['day_level'].map({'Low day': 0, 'High day': 1})

    # Prepare the DataFrame for scaling
    temp_X_test = X_test.copy()

    # Scale necessary features
    temp_X_test['n_days_after_onboarding'] = (X_test['n_days_after_onboarding'] / 365).astype(float)
    temp_X_test['duration_minutes_drives'] = (X_test['duration_minutes_drives'] / (60 * 24)).astype(float)

    columns = ['total_navigations_fav1', 'total_navigations_fav2', 'total_sessions', 'driven_km_drives']

    try:
        temp_X_test[columns] = scaler.transform(temp_X_test[columns])
    except ValueError as e:
        st.error(f"Error during scaling: {e}")
        return None

   # Feature Selection
    try:
        temp_X_test_filtered = temp_X_test.copy()  # Ensure this is defined correctly
        X_test_selected = selector.transform(temp_X_test_filtered)
    except AttributeError as e:
        st.error(f"Attribute error during feature selection: {e}")
        return None
    except Exception as e:
        st.error(f"Error during feature selection: {e}")
        return None

    # Make predictions
    try:
        y_pred = logistic_regression_model.predict(X_test_selected)
        y_pred_label = ['churned' if pred == 0 else 'retained' for pred in y_pred]
        return pd.DataFrame({'Predicted': y_pred_label})
    except Exception as e:
        st.error(f"Error during prediction: {e}")
        return None

# Streamlit app
st.title("Waze App User Churn Prediction")
st.write("Upload a CSV file with user records for churn prediction.")

# File uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Make predictions
    results = make_predictions(df)
    if results is not None:
        st.write("Prediction Results:")
        st.dataframe(results)
