from backend.config import DATA_DIR
from backend.lib.database import db_query
import pandas as pd
from sklearn.model_selection import GroupKFold
import numpy as np
from sentence_transformers import SentenceTransformer
import lightgbm as lgb
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
from backend.model.utils import  preprocess_text, transform_features, evaluate, plot_feature_importance, get_shap, compare_predictions


class Model:
    def __init__(self, target="views", sentece_transformer=None, max_ratio=2000):
        self.num_features = [
            "author_followers_count",
            # "author_following_count",
            # "author_tweet_count",
            "age_hours",
            # "author_age_years",
            "is_blue_verified",
            # "checkmark_color",
        ]

        self.cat_features = []
        self.target = target
        # self.target = "likes"
        # self.target = "retweets"
        # self.target = "comments"

        self.text_features = ["text"]
        # Using sentence-transformer model instead of TF-IDF
        self.transformer_model_name = 'all-MiniLM-L6-v2'  # Small but effective model
        self.embedding_size = 384  # Size of embeddings from all-MiniLM-L6-v2
        self.text_feat = [f"text_emb_{i}" for i in range(self.embedding_size)]
        if sentece_transformer is None:
            self.transformer = SentenceTransformer(self.transformer_model_name)
        else:
            self.transformer = sentece_transformer

        self.monotonic_constraints = {
            "author_followers_count": 1,
            "author_following_count": 1,
            "author_tweet_count": 1,
            "age_hours": 1,
            "is_blue_verified": 1
        }
        self.max_ratio = max_ratio
    def get_data(self):
        df = db_query("SELECT * FROM twitter_forecast")
        df = pd.DataFrame(df)
        df["observation_time"] = pd.to_datetime(df["observation_time"])
        df["tweet_time"] = pd.to_datetime(df["tweet_time"])
        df["age_hours"] = (df["observation_time"] - df["tweet_time"]).dt.total_seconds() / 3600
        df["author_created_at"] = pd.to_datetime(df["author_created_at"])
        df["author_age_years"] = (df["observation_time"] - df["author_created_at"]).dt.total_seconds() / (3600 * 24 * 365)

        # constraints
        MIN_HOURS = 1
        MAX_HOURS = 48
        MIN_VIEWS = 10

        mask = (df["age_hours"] >= MIN_HOURS) & (df["age_hours"] <= MAX_HOURS) & (df["views"] >= MIN_VIEWS)
        df = df[mask].copy()
        df["text"] = df["text"].apply(preprocess_text)

        df["ratio"] = df["views"] / df["author_followers_count"]
        df = df[df["ratio"] < self.max_ratio].copy()

        df = transform_features(df)
        return df
    

    def split_data(self, df):
        n_splits = 5  # Number of folds
        group_kfold = GroupKFold(n_splits=n_splits)

        # Use the defined features from earlier
        X = df.copy()
        X = transform_features(X)
        y = np.log1p(X[self.target])
        X = X[self.num_features + self.cat_features + self.text_features].copy()

        # Use author as the group
        groups = df['author']

        # Get train and test indices for the first fold
        train_idx, test_idx = next(group_kfold.split(X, y, groups))

        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        # Transform text features using sentence transformers
        X_train_text_embeddings = self.transformer.encode(X_train["text"].tolist())
        X_test_text_embeddings = self.transformer.encode(X_test["text"].tolist())

        # Convert embeddings to DataFrame and concatenate with original features
        X_train_text_df = pd.DataFrame(
            X_train_text_embeddings,
            columns=self.text_feat,
            index=X_train.index
        )
        X_test_text_df = pd.DataFrame(
            X_test_text_embeddings,
            columns=self.text_feat,
            index=X_test.index
        )

        # Drop the original text column and concatenate with transformer embeddings
        X_train = X_train.drop(columns=["text"]).join(X_train_text_df)
        X_test = X_test.drop(columns=["text"]).join(X_test_text_df)

        # Print split information
        print(f"Training set size: {len(X_train)}")
        print(f"Test set size: {len(X_test)}")
        print(f"Number of unique authors in training: {X_train.index.map(df['author']).nunique()}")
        print(f"Number of unique authors in test: {X_test.index.map(df['author']).nunique()}")
        print(f"Features used: {X.columns.tolist()}")
        return X_train, X_test, y_train, y_test
    
    def train(self, X_train, X_test, y_train, y_test):
        early_stop_callback = lgb.early_stopping(stopping_rounds=50)
        
        # Create a constraint array based on feature presence
        feature_names = X_train.columns.tolist()
        monotone_constraints_array = []
        
        for feature in feature_names:
            if feature in self.monotonic_constraints:
                monotone_constraints_array.append(self.monotonic_constraints[feature])
            else:
                monotone_constraints_array.append(0)  # No constraint
        
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            # 'metric': 'mse',
            'boosting_type': 'gbdt',
            'n_estimators': 500,
            'learning_rate': 0.05,
            'num_leaves': 31,
            'random_state': 42,
            'monotone_constraints': monotone_constraints_array
        }
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train, callbacks=[early_stop_callback], eval_set=[(X_test, y_test)], feature_name=feature_names)
        self.model = model  # Store the trained model in the instance
        return model
    
    def save(self):
        """
        Save the model and its components to disk.
        
        Args:
            filepath (str): Path where the model will be saved
        """
        import pickle
        import os
        
        # Create directory if it doesn't exist
        filepath = DATA_DIR / f"model_{self.target}.pkl"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare a dictionary with all components needed for prediction
        model_data = {
            'model': self.model,
            'transformer_model_name': self.transformer_model_name,
            'num_features': self.num_features,
            'cat_features': self.cat_features,
            'text_features': self.text_features,
            'text_feat': self.text_feat,
            'embedding_size': self.embedding_size,
            'target': self.target
        }
        
        # Save the model data
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Model saved to {filepath}")
    
    @classmethod
    def load(cls, filepath, sentece_transformer=None):
        import pickle
        
        # Load the model data
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        # Create a new instance
        instance = cls()
        
        # Restore all components
        instance.model = model_data['model']
        instance.transformer_model_name = model_data['transformer_model_name']
        if sentece_transformer is None:
            instance.transformer = SentenceTransformer(instance.transformer_model_name)
        else:
            instance.transformer = sentece_transformer
        instance.num_features = model_data['num_features']
        instance.cat_features = model_data['cat_features']
        instance.text_features = model_data['text_features']
        instance.text_feat = model_data['text_feat']
        instance.embedding_size = model_data['embedding_size']
        
        return instance
    
    def predict(self, data):
        import numpy as np
        import pandas as pd
        from backend.model.utils import transform_features, preprocess_text
        
        # Check if model exists
        if not hasattr(self, 'model'):
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        # Convert dictionary to DataFrame if needed
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        
        # Make a copy to avoid modifying the original data
        X = data.copy()
        
        # Check if data needs text preprocessing or if it's already processed
        if "text" in X.columns:
            # Raw data with text - needs preprocessing
            X["text"] = X["text"].apply(preprocess_text)
            
            # Transform numeric features
            X = transform_features(X)
            
            # Extract features in the right order
            X = X[self.num_features + self.cat_features + self.text_features].copy()

            # Transform text features using sentence transformers
            X_text_embeddings = self.transformer.encode(X["text"].tolist())
            
            # Convert embeddings to DataFrame
            X_text_df = pd.DataFrame(
                X_text_embeddings,
                columns=self.text_feat,
                index=X.index
            )
            
            # Drop text column and join with embedding features
            X = X.drop(columns=["text"]).join(X_text_df)
        else:
            # Check if this is already processed data (has embedding feature columns)
            has_text_features = all(feature in X.columns for feature in self.text_feat[:5])
            
            if not has_text_features:
                raise ValueError("Input data must contain either 'text' column or transformer processed text features")
            
        # Make predictions
        y_pred_log = self.model.predict(X)
        
        # Convert from log space back to original scale
        y_pred = np.expm1(y_pred_log)
        
        # Return a single value if only one prediction, otherwise return array
        if len(y_pred) == 1:
            return y_pred[0]
        return y_pred


if __name__ == "__main__":
    model_instance = Model()
    df = model_instance.get_data()
    X_train, X_test, y_train, y_test = model_instance.split_data(df)
    trained_model = model_instance.train(X_train, X_test, y_train, y_test)
    evaluate(DATA_DIR,trained_model, X_test, y_test, y_train)
    plot_feature_importance(DATA_DIR,trained_model, model_instance.num_features + model_instance.cat_features + model_instance.text_feat, model_instance.transformer)
    get_shap(DATA_DIR,trained_model, X_test, model_instance.transformer)

    model_instance.save()

    loaded_model = Model.load(DATA_DIR / "model_views.pkl")
    compare_predictions(model_instance, loaded_model, X_test, df)


    vals_for_inference = [
        {"text": "This is a sample tweet", "author_followers_count": 100, "age_hours": i, "is_blue_verified": 1}
        for i in range(1, 49)
    ]
    res = loaded_model.predict(pd.DataFrame(vals_for_inference))
    print(res)

    vals_for_inference = [
        {"text": "You can just do things, in the end it doesn't matter, this will be banger", "author_followers_count": 100, "age_hours": i, "is_blue_verified": 1}
        for i in range(1, 49)
    ]
    res = loaded_model.predict(pd.DataFrame(vals_for_inference))
    print(res)