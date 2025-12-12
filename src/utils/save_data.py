import pandas as pd
import numpy as np
import json
import pyarrow

def _is_scalar_na(x):
    """Return True if x is considered NA (handles array-like pd.isna results)."""
    try:
        res = pd.isna(x)
        # if pd.isna returned a scalar boolean
        if isinstance(res, (bool, np.bool_)):
            return bool(res)
        # if pd.isna returned an array-like, consider it NA only if all elements are NA
        return bool(np.all(res))
    except Exception:
        return False

def _jsonify_cell(x):
    """Convert a single cell to a JSON-string if it's not NaN/None. Handles numpy types/arrays."""
    if _is_scalar_na(x):
        return None  # Return None instead of x to ensure consistent type
    
    # numpy arrays -> convert to python list first
    if isinstance(x, np.ndarray):
        return json.dumps(x.tolist())
    
    # numpy scalar (e.g. np.int64) -> get python scalar then dump
    if isinstance(x, (np.generic,)):
        return json.dumps(x.item())
    
    # attempt normal json dump, fallback to string if object isn't serializable
    try:
        return json.dumps(x)
    except (TypeError, OverflowError):
        return json.dumps(str(x))

def save_df_parquet_safe(df: pd.DataFrame, path: str):
    """saves the dataframe a Parquet file while preserving the object type columns

    Args:
        df (pd.DataFrame): dataframe you want to save.
        path (str): directory where you want to save.
    """
    
    # let's make a copy of the dataframe so that we don't mess with the original df
    df = df.copy()
    
    # we initialize this will keep track of which columns are normal and which columns has to be json encoded
    schema = {}
    
    for col in df.columns:
        if df[col].dtype == 'object':
            # we will json encode them
            df[col] = df[col].apply(_jsonify_cell)
            # Explicitly convert to string dtype to ensure PyArrow recognizes it correctly
            df[col] = df[col].astype('string')
            # we will keep the info
            schema[col] = 'json'
        else:
            schema[col] = 'normal'
            
    # now, let's save the data as parquet file
    df.to_parquet(path=path, engine='pyarrow')
    
    # saving the schema next to it
    schema_path = path + '.schema.json'
    with open(schema_path, 'w') as f:
        json.dump(schema, f)
        
    print(f"Saved Parquet: {path}")
    print(f"Saved schema: {schema_path}")
    

def load_df_parquet_safe(path: str) -> pd.DataFrame:
    """loads the dataframe and restores the json formatted cols into python DS

    Args:
        path (str): path to the dir where data is saved
    """
    
    df = pd.read_parquet(path=path, engine='pyarrow')
    
    # load schema
    schema_path = path + '.schema.json'
    with open(schema_path, 'r') as f:
        schema = json.load(f)
        
    # restore the columns
    for col, col_type in schema.items():
        if col_type == 'json':
            df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) else None)
        
    return df