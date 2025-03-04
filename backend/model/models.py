from sentence_transformers import SentenceTransformer
from backend.model.train import Model
from backend.model.utils import evaluate, plot_feature_importance, get_shap
from backend.config import DATA_DIR
import pandas as pd
import json
class Models:
    def __init__(self, targets: list[str]):
        self.targets = targets
        self.models = {}

    def train(self):
        metrics = {}
        for target in self.targets:
            print(f"Training model for {target}")
            model_instance = Model(target=target)
            df = model_instance.get_data()
            X_train, X_test, y_train, y_test = model_instance.split_data(df)
            trained_model = model_instance.train(X_train, X_test, y_train, y_test)
            model_metrics = evaluate(DATA_DIR,trained_model, X_test, y_test, y_train)
            plot_feature_importance(DATA_DIR,trained_model, model_instance.num_features + model_instance.cat_features + model_instance.text_feat, model_instance.transformer)
            get_shap(DATA_DIR,trained_model, X_test, model_instance.transformer)
            model_instance.save()
            metrics[target] = model_metrics
        
        # save metrics to json
        with open(DATA_DIR / "metrics.json", "w") as f:
            json.dump(metrics, f, indent=4)

    @classmethod
    def load(cls, targets: list[str]):
        transformer = SentenceTransformer('all-MiniLM-L6-v2')
        models = {}
        for target in targets:
            model_instance = Model.load(DATA_DIR / f"model_{target}.pkl", sentece_transformer=transformer)
            models[target] = model_instance
        obj = cls(targets)
        obj.models = models
        return obj
    

    def predict(self, data: dict, age_hours: list[int]):
        in_data = []
        for age_hour in age_hours:
            in_data.append({**data, "age_hours": age_hour})
        in_data = pd.DataFrame(in_data)
        predictions = {}
        for target in self.targets:
            model_instance = self.models[target]
            prediction = model_instance.predict(in_data)
            fmt_out = [{"value": float(pred), "age_hours": hours} for hours, pred in zip(age_hours, prediction)]
            predictions[target] = fmt_out
        return predictions
    
    def predict_bulk(self, data: list[dict], age_hours: list[int]):
        in_data = []
        for idx, tweet in enumerate(data):
            tw = tweet.copy()
            tw["tweet_idx"] = idx
            for age_hour in age_hours:
                in_data.append({**tw, "age_hours": age_hour})
        in_data = pd.DataFrame(in_data)

        for target in self.targets:
            model_instance = self.models[target]
            in_data[target] = model_instance.predict(in_data)
        
        # we need to return [{"tweet_idx": 0, "text": "...", "views": [{"value": 100, "age_hours": 0.1} ...,
        out = []
        for (tweet_idx, text), values in in_data.groupby(["tweet_idx", "text"]):
            tmp = {"tweet_idx": int(tweet_idx), "text": text}
            for target in self.targets:
                tmp[target] = [float(v) for v in values[target].tolist()]
            out.append(tmp)
        return out
        
    
if __name__ == "__main__":
    import sys
    import time
    
    # Simple command line argument parsing
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        print("Starting model training...")
        models = Models(["views", "likes", "retweets", "comments"])
        models.train()
        print("Model training complete!")
    else:
        # Default behavior - load and test prediction
        start_time = time.time()
        loaded_models = Models.load(["views", "likes", "retweets", "comments"])
        print(f"Time taken to load models: {time.time() - start_time} seconds")
        start_time = time.time()
        predictions = loaded_models.predict({"text": "Hello, world!", "author_followers_count": 100, "is_blue_verified": 1}, [0,1,2,3,4,5,6,7,8,9,10])
        print(f"Time taken to predict: {time.time() - start_time} seconds")
        print(predictions)
    