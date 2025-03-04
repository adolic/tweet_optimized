import re
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


stopwords = {'har', 'they', 'those', 'through', 'each', 'as', 'being', 'blive', 'why', 'thi', 'her', 'how',
                          'this', 'shouldn', 'won', 'nor', 'most', 'too', 'os', 'does', 'blev', "didn't", "hasn't",
                          "it's", 'det', 'mustn', 'into', 'further', 'du', 'have', 'o', 'på', 'være', "shan't", 'are',
                          'of', "don't", 'off', 'doesn', 'sine', 'han', 'dog', 'theirs', 'yourself', 'until', 'needn',
                          'også', 'themselves', "mustn't", "needn't", 'hans', 'som', "you're", 'from', 'both', 'here',
                          'their', 'its', 'few', 'din', 'man', 'jeg', 'it', 'and', 'til', 'anden', 'hasn', 'shan', 'i',
                          'has', 'alt', 'end', 'up', 'noget', 'on', 'there', 'own', 'more', 'above', 'deres', 'at',
                          'mine', "you've", 'herself', 'below', 'all', 'isn', "you'd", 'itself', 'where', 'we', 'wasn',
                          'ain', 'such', 'while', 'but', 'been', 'whom', 'couldn', 'skal', "you'll", 'yours', 'de',
                          'against', 'in', 'ma', 'og', 'during', 'what', 'which', 'mod', "wasn't", 'him', 'because',
                          'his', 'himself', 'a', 'just', 'over', 'kunne', 's', 'mange', 'my', 'had', "should've",
                          "couldn't", 'en', 'an', 'these', 'er', 'nu', 'should', 'fra', 'wouldn', 'ikke', 'op', 'ud',
                          'når', 'disse', 'myself', 'efter', 'weren', 'af', 'don', 'nogle', 'only', 'for', 'sådan',
                          'hvad', 'that', 'll', 'ad', 'who', 'hvis', 'having', 'y', 'hun', 'can', "doesn't", 'down',
                          'your', 'was', "isn't", 'mightn', "wouldn't", 'm', 'to', 'sig', 'hos', 'same', 'he', 'about',
                          'vil', "aren't", 'med', 'dette', 'yourselves', 'you', 'so', 'jo', 'sin', 'them', 'aren',
                          "that'll", 'været', 'or', 'the', 'den', 'after', 'when', 'havde', 'ham', 'before', 'mit',
                          'some', 'ourselves', 'min', 'denne', 'me', 'again', 'no', 'hadn', 'selv', 'skulle', 'doing',
                          "hadn't", 'dig', 'if', 'did', 'ind', 'var', 'other', 'once', 'haven', 'ville', 'jer', 've',
                          're', 'now', "weren't", 'dem', 'be', 'any', "mightn't", 'do', 'is', 'with', "won't", 'hers',
                          'ours', 'der', 'et', 'under', 'men', 'da', 'hendes', "she's", 'vi', 'hende', 'out', 'then',
                          'hvor', 'vor', 'bliver', 'not', 'alle', 'd', 'by', 'between', 'were', 'than', 'didn', 'sit',
                          'ned', 'mig', 'will', 'our', "haven't", 'she', 'am', 't', 'meget', 'om', 'eller', "shouldn't",
                          'very'}

def preprocess_text(text):
    if text is None:
        return ""
    text = text.lower()
    text = re.sub(r'\W', ' ', text)
    text = re.sub(r'\d', ' ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    tokens = text.split()
    tokens = [word for word in tokens if word not in stopwords]
    text = ' '.join(tokens)
    return text

import numpy as np

def transform_features(x):
    if "author_followers_count" in x.columns:
        x["author_followers_count"] = np.log1p(x["author_followers_count"])
    if "author_following_count" in x.columns:
        x["author_following_count"] = np.log1p(x["author_following_count"])
    if "author_tweet_count" in x.columns:
        x["author_tweet_count"] = np.log1p(x["author_tweet_count"])
    if "author_age_years" in x.columns:
        x["author_age_years"] = np.log1p(x["author_age_years"])
    if "age_hours" in x.columns:
        x["age_hours"] = np.log1p(x["age_hours"])
    if "is_blue_verified" in x.columns:
        # todo: check if this works correctly
        x["is_blue_verified"] = x["is_blue_verified"].astype(int)
    if "checkmark_color" in x.columns:
        x["checkmark_color"] = x["checkmark_color"].map({"blue": 1, "verified": 1, "none": 0})

    if "text" in x.columns:
        x["text_char_count"] = x["text"].apply(len)
        x["text_word_count"] = x["text"].apply(lambda x: len(str(x).split()))
    else:
        x["text_char_count"] = 0
        x["text_word_count"] = 0
    
    return x


def plot_calibration_curve(directory,y_true, y_pred, n_bins=10):
    calib_df = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    
    # Create ntile bins with duplicates='drop' to handle duplicate bin edges
    calib_df['bin'] = pd.qcut(calib_df['y_pred'], q=n_bins, labels=False, duplicates='drop')
    
    # Calculate mean predicted and true values per bin
    bin_stats = calib_df.groupby('bin').agg({
        'y_pred': 'mean',
        'y_true': 'mean'
    }).reset_index()
    
    # Plot calibration curve
    plt.figure(figsize=(10, 6))
    plt.plot(bin_stats['y_pred'], bin_stats['y_true'], marker='o', linestyle='-', label='Model')
    
    # Plot perfect calibration line
    min_val = min(bin_stats['y_pred'].min(), bin_stats['y_true'].min())
    max_val = max(bin_stats['y_pred'].max(), bin_stats['y_true'].max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', label='Perfect Calibration')
    
    plt.xlabel('Mean Predicted Value')
    plt.ylabel('Mean True Value')
    plt.title(f'Calibration Curve (n_bins={n_bins})')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save plot instead of showing it
    plt.savefig(f"{directory}/calibration_plot.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    return bin_stats



def evaluate(directory, model, X_test, y_test, y_train):
    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"Root Mean Squared Error: {rmse:.2f}")
    print(f"Mean Absolute Error: {mae:.2f}")
    print(f"R² Score: {r2:.4f}")

    # Calculate baseline metrics (using training set mean)
    baseline_pred = np.full_like(y_test, y_train.mean())
    baseline_mse = mean_squared_error(y_test, baseline_pred)
    baseline_rmse = np.sqrt(baseline_mse)
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_r2 = r2_score(y_test, baseline_pred)

    print(f"Baseline Root Mean Squared Error: {baseline_rmse:.2f}")
    print(f"Baseline Mean Absolute Error: {baseline_mae:.2f}")
    print(f"Baseline R² Score: {baseline_r2:.4f}")

    # Calculate improvement over baseline
    if baseline_rmse > 0:
        print(f"Model improvement over baseline (RMSE): {(baseline_rmse - rmse) / baseline_rmse * 100:.2f}%")
    if baseline_mae > 0:
        print(f"Model improvement over baseline (MAE): {(baseline_mae - mae) / baseline_mae * 100:.2f}%")
    if baseline_r2 != 0:
        print(f"Model improvement over baseline (R²): {(baseline_r2 - r2) / baseline_r2 * 100:.2f}%")
    
    # Save the calibration plot instead of showing it
    plt.figure(figsize=(10, 6))
    plot_calibration_curve(directory,y_test, y_pred)
    plt.tight_layout()
    plt.savefig(f"{directory}/calibration_curve.png", dpi=300, bbox_inches='tight')
    plt.close()

    # Plot actual vs predicted views
    plt.figure(figsize=(10, 6))
    plt.scatter(y_test, y_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
    plt.xlabel('Actual Views')
    plt.ylabel('Predicted Views')
    plt.title('Actual vs Predicted Views')
    plt.tight_layout()
    
    # Save plot instead of showing it
    plt.savefig(f"{directory}/actual_vs_predicted.png", dpi=300, bbox_inches='tight')
    plt.close()

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "baseline_rmse": baseline_rmse,
        "baseline_mae": baseline_mae,
        "baseline_r2": baseline_r2
    }



def plot_feature_importance(directory, model, features, transformer):
    # Check if model is a Pipeline or a direct regressor
    if hasattr(model, 'named_steps'):
        # It's a Pipeline
        regressor = model.named_steps['regressor']
        feature_importance = regressor.feature_importances_
    else:
        # It's a direct regressor
        feature_importance = model.feature_importances_
        
    
    # Create a mapping of feature names to more readable names
    feature_names = []
    for feature in features:
        if feature.startswith('text_emb_'):
            # For sentence transformer embeddings, we use a simplified naming convention
            # since we don't have direct mapping to words
            feature_idx = int(feature.split('_')[-1])
            feature_names.append(f"embedding_{feature_idx}")
        else:
            feature_names.append(feature)

    # Plot only top 20 features if there are many
    plt.figure(figsize=(10, 6))
    if len(feature_importance) > 20:
        # Sort and get indices of top 20 features
        sorted_idx = np.argsort(feature_importance)[-20:]
    else:
        sorted_idx = np.argsort(feature_importance)
        
    plt.barh(range(len(sorted_idx)), feature_importance[sorted_idx])
    plt.yticks(range(len(sorted_idx)), [feature_names[i] for i in sorted_idx])
    plt.xlabel('Feature Importance')
    plt.title('LightGBM Feature Importance')
    plt.tight_layout()
    
    # Save the plot instead of showing it
    plt.savefig(f"{directory}/feature_importance.png", dpi=300, bbox_inches='tight')
    plt.close()



def get_shap(directory, model, X_test, transformer):
    import shap

    # Create a SHAP explainer for the model
    # Check if model is a Pipeline or a direct regressor
    if hasattr(model, 'named_steps'):
        # It's a Pipeline
        regressor = model.named_steps['regressor']
    else:
        # It's a direct regressor
        regressor = model
        
    explainer = shap.TreeExplainer(regressor)

    # Calculate SHAP values for the test set
    X_test_array = X_test.values
    shap_values = explainer.shap_values(X_test_array)

    # Create a mapping from feature index to feature names
    # For transformer embeddings, we use a simplified naming scheme
    text_feature_names = []
    for col in X_test.columns:
        if col.startswith('text_emb_'):
            # For sentence transformer embeddings, use a simplified naming
            embedding_idx = int(col.split('_')[-1])
            text_feature_names.append(f"embedding_{embedding_idx}")
        else:
            text_feature_names.append(col)
    
    # Plot the SHAP summary plot
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_test, plot_type="bar", feature_names=text_feature_names, show=False)
    plt.savefig(f"{directory}/shap_summary.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Plot the SHAP value distributions
    plt.figure(figsize=(12, 10))
    shap.summary_plot(shap_values, X_test, feature_names=text_feature_names, show=False)
    plt.savefig(f"{directory}/shap_distributions.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Plot feature importance based on SHAP values
    plt.figure(figsize=(10, 6))
    shap_importance = np.abs(shap_values).mean(0)
    
    # Sort features by importance
    if len(shap_importance) > 20:
        # Only show top 20 features
        sorted_idx = np.argsort(shap_importance)[-20:]
    else:
        sorted_idx = np.argsort(shap_importance)
        
    plt.barh(range(len(sorted_idx)), shap_importance[sorted_idx])
    plt.yticks(range(len(sorted_idx)), [text_feature_names[i] for i in sorted_idx])
    plt.xlabel('Feature Importance')
    plt.title('LightGBM Feature Importance with Actual Text Terms')
    plt.tight_layout()
    plt.savefig(f"{directory}/shap_feature_importance.png", dpi=300, bbox_inches='tight')
    plt.close()



def compare_predictions(model_instance, loaded_model, X_test, df):
    """
    Compare predictions from the original model and the loaded model.
    
    Args:
        model_instance: Original model instance
        loaded_model: Loaded model instance from file
        X_test: Test set used with original model
        df: Original complete dataframe
    """
    print("\n" + "=" * 50)
    print("COMPARING ORIGINAL MODEL VS LOADED MODEL PREDICTIONS")
    print("=" * 50)
    
    # 1. Select a subset of the test set
    test_subset = X_test.sample(min(10, len(X_test)), random_state=42)
    
    # 2. Get predictions from original model
    print("\nGetting predictions from original model...")
    direct_predictions = model_instance.predict(test_subset)
    
    # 3. Get predictions from loaded model on same data
    print("\nGetting predictions from loaded model using the same DataFrame...")
    loaded_predictions = loaded_model.predict(test_subset)
    
    # 4. Prepare individual dictionaries for each test sample
    print("\nPreparing test dictionaries...")
    test_dicts = []
    for idx in test_subset.index:
        # Get the corresponding row from the original data
        original_row = df.loc[idx]
        
        # Create a dictionary with all required features
        sample_dict = {}
        for feature in model_instance.num_features + model_instance.cat_features:
            sample_dict[feature] = original_row[feature]
        
        # Add text feature
        sample_dict["text"] = original_row["text"]
        
        test_dicts.append(sample_dict)
    
    # 5. Get predictions from loaded model on dictionaries
    print("\nGetting predictions from loaded model using dictionaries...")
    dict_predictions = []
    for test_dict in test_dicts:
        dict_predictions.append(loaded_model.predict(test_dict))
    
    # 6. Compare predictions
    print("\nComparing predictions:")
    print(f"{'Index':<10}{'Direct Pred':<20}{'Dict Pred':<20}{'Difference':<15}{'% Diff':<10}")
    print("-" * 75)
    
    # Convert direct_predictions to a list if it's a numpy array
    if hasattr(direct_predictions, 'tolist'):
        direct_predictions = direct_predictions.tolist()
    
    for i in range(len(direct_predictions)):
        direct_pred = direct_predictions[i]
        dict_pred = dict_predictions[i]
        diff = abs(direct_pred - dict_pred)
        pct_diff = (diff / direct_pred * 100) if direct_pred != 0 else float('inf')
        
        print(f"{i:<10}{direct_pred:<20.2f}{dict_pred:<20.2f}{diff:<15.4f}{pct_diff:<10.2f}%")
    
    # 7. Summary
    avg_diff = sum(abs(direct_predictions[i] - dict_predictions[i]) 
                for i in range(len(direct_predictions))) / len(direct_predictions)
    print("\nSummary:")
    print(f"Average absolute difference: {avg_diff:.4f}")
    print(f"Predictions match: {avg_diff < 0.001}")
    print("="*50)