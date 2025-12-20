import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
from typing import Literal, Optional
from pysad.models import RobustRandomCutForest
from pysad.utils import ArrayStreamer
# from sklearn.preprocessing import StandardScaler

MIN = 0.5
MAX = 2.0

def get_data_ready(data: pd.DataFrame, features: list[str], type: Literal["ui", "ud"]):  # standardize: bool, scalar: Optional[StandardScaler] = None
    """Data get's ready to be processed.

    Args:
        scalar (StandardScaler): needed to standardize the data
        data (pd.DataFrame): need the complete data
        features (list[str]): Just provide a list of feature names that you want to fit with model
        type (Literal[&quot;ui&quot;, &quot;ud&quot;]): 'ui' if the user independent else 'ud' user dependent
    """
    
    # get the data
    if type == 'ui':
        features = data[features].ffill()
        f_id = features.index
        # if standardize:
        #     features = scalar.fit_transform(features)
        #     return f_id, features
        # else:
        #     return f_id, features.to_numpy()
        return f_id, features.to_numpy()
    else:
        features = data.loc[data['speaker'] == 'B', features]
        if features.notna().all().all():
            f_id = features.index
            # if standardize:
            #     features = scalar.fit_transform(features)
            #     return f_id, features
            # else:
            #     return f_id, features.to_numpy()
            return f_id, features.to_numpy()
        else:
            features = features.ffill()
            f_id = features.index
            # if standardize:
            #     features = scalar.fit_transform(features)
            #     return f_id, features
            # else:
            #     return f_id, features.to_numpy()
            return f_id, features.to_numpy()
        

def adaptive_n_sigma(anomaly_scores: np.ndarray) -> float:
    """
    Automatically determine optimal n_sigma based on score distribution
    
    Returns:
        Optimal n_sigma value (typically 2.5 - 4.5)
    """
    from scipy import stats as scipy_stats
    
    # Calculate distribution characteristics
    skewness = scipy_stats.skew(anomaly_scores)
    kurtosis = scipy_stats.kurtosis(anomaly_scores)
    
    # Decision rules
    if kurtosis > 5:
        # Heavy tails (extreme outliers)
        n_sigma = 4.0
    elif kurtosis > 3:
        # Moderately heavy tails
        n_sigma = 3.5
    elif skewness > 1.5:
        # Strong right skew (occasional high scores)
        n_sigma = 3.5
    elif skewness > 1.0:
        # Moderate right skew
        n_sigma = 3.0
    else:
        # Normal-ish distribution
        n_sigma = 2.5
    
    return n_sigma

def get_threshold_mad(scores, n_sigma=3):
    """
    Robust Z-Score method using Median and MAD.
    Standard Z-Score = (x - mean) / std
    Robust Z-Score = (x - median) / (1.4826 * MAD)
    """
    scores = np.array(scores)
    median = np.median(scores)
    
    # Calculate MAD (Median Absolute Deviation)
    mad = np.median(np.abs(scores - median))
    
    # The factor 1.4826 makes MAD comparable to Standard Deviation for normal data
    consistent_mad = 1.4826 * mad
    
    # Threshold = Median + (3 * Robust_Std_Dev)
    threshold = median + (n_sigma * consistent_mad)
    return threshold

def run_rrcf(features: np.ndarray, num_trees: int = 40, tree_size: int = 256, shingle: int = 1):
    """Runs rrcf on the given features

    Args:
        features (np.ndarray): provide your features as numpy nd array in shape (num_samples, num_features)
        num_trees (int, optional): No of trees the model should fit. Defaults to 40.
        tree_size (int, optional): max depth of the tree. Defaults to 256.
        shingle (int, optional): _description_. Defaults to 1.

    Returns:
        list: returns list of anomaly which is equal to the length of the feature array.
    """
    # initializing the model
    model = RobustRandomCutForest(num_trees=num_trees, tree_size=tree_size, shingle_size=shingle)
    
    # This simulates a live stream from a static array
    streamer = ArrayStreamer(shuffle=False)
    
    anomaly_scores = []
    
    for X in streamer.iter(features):
        # fit_score_partial updates the model and returns the score in one step
        score = model.fit_score_partial(X)
        anomaly_scores.append(score)
    
    print(f"Processed {len(anomaly_scores)} points")
    
    return anomaly_scores        


def get_anomalous_time_ranges(min: int, max: int, anomalies_time: pd.Series | list) -> list[list[float]]:
    """Given the anomalous time values, This function tries to find the continous anomalous range not the sudden spikes.

    Args:
        min (int): min value of the range to check
        max (int): max value of the range to check
        anomalies_time (pd.Series | list): time values of the anomalies

    Returns:
        list[list[float]]: continuos anomalous time ranges that lie between min and max
    """
    
    if len(anomalies_time) == 0:
        return []
    
    if isinstance(anomalies_time, pd.Series):
        anomalies_time = anomalies_time.tolist()
    else:
        anomalies_time = [t.item() if hasattr(t, 'item') else t for t in anomalies_time]
    
    if len(anomalies_time) == 1:
        return [anomalies_time[0].item()]
    
    continous_ranges = []
    start = anomalies_time[0]
    continous_range = [start]
    for i in range(1, len(anomalies_time)):
        current = anomalies_time[i]
        if min <= (current - start) <= max:
            continous_range.append(current)
            start = current
        else:
            start = current
            if len(continous_range) == 1:
                continous_range = [start]
                continue
            else:
                continous_ranges.append(continous_range)
                continous_range = [start]
                continue
    
    return continous_ranges