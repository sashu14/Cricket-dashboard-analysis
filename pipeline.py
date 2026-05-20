import pandas as pd
import logging
import os

# Configure logging to capture errors without crashing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_errors.log"),
        logging.StreamHandler()
    ]
)

def clean_and_process_data(matches_path="matches.csv", deliveries_path="deliveries.csv"):
    """
    Reads Cricsheet CSV data, cleans dirty/missing records, and outputs aggregated DataFrames.
    Built to be fault-tolerant and schema-agnostic (extracts entities dynamically).
    """
    try:
        logging.info("Starting data ingestion process.")
        
        # 1. Fault Tolerance: Gracefully handle missing files
        if not os.path.exists(matches_path) or not os.path.exists(deliveries_path):
            logging.error(f"Missing input files. Ensure '{matches_path}' and '{deliveries_path}' are present.")
            # Do not raise error to prevent crashing, just log and return empty.
        
        # Ingest matches
        try:
            matches = pd.read_csv(matches_path)
            logging.info(f"Loaded {len(matches)} rows from {matches_path}.")
            
            # Fault Tolerance: Drop rows that are entirely NaN
            initial_match_len = len(matches)
            matches.dropna(how='all', inplace=True)
            if len(matches) < initial_match_len:
                logging.warning(f"Dropped {initial_match_len - len(matches)} fully NaN rows from matches.")
                
            # Standardize missing data in critical columns
            if 'winner' in matches.columns:
                matches['winner'] = matches['winner'].fillna('No Result')
            if 'player_of_match' in matches.columns:
                matches['player_of_match'] = matches['player_of_match'].fillna('Unknown')
                
        except Exception as e:
            logging.error(f"Failed to process matches data: {e}")
            matches = pd.DataFrame()
            
        # Ingest deliveries
        try:
            deliveries = pd.read_csv(deliveries_path)
            logging.info(f"Loaded {len(deliveries)} rows from {deliveries_path}.")
            
            # Fault Tolerance: Drop rows that are entirely NaN
            initial_del_len = len(deliveries)
            deliveries.dropna(how='all', inplace=True)
            if len(deliveries) < initial_del_len:
                logging.warning(f"Dropped {initial_del_len - len(deliveries)} fully NaN rows from deliveries.")

            # Fault Tolerance: Ensure numeric columns are actually numeric, coercing strings/errors to NaN, then to 0
            numeric_cols_del = ['batsman_runs', 'extra_runs', 'total_runs']
            for col in numeric_cols_del:
                if col in deliveries.columns:
                    deliveries[col] = pd.to_numeric(deliveries[col], errors='coerce').fillna(0)
                    
        except Exception as e:
            logging.error(f"Failed to process deliveries data: {e}")
            deliveries = pd.DataFrame()

        # 2. Schema Generalization: dynamically extract unique entities
        # We don't hardcode any team or player names. We discover them from whatever dataset is provided.
        if not matches.empty:
            teams = pd.concat([matches.get('team1', pd.Series()), matches.get('team2', pd.Series())]).dropna().unique()
            logging.info(f"Extracted {len(teams)} unique teams dynamically.")
            
            venues = matches.get('venue', pd.Series()).dropna().unique()
            logging.info(f"Extracted {len(venues)} unique venues dynamically.")
        
        # Save cleaned dataframes to disk if they have data
        if not matches.empty:
            matches.to_csv("cleaned_matches.csv", index=False)
        if not deliveries.empty:
            deliveries.to_csv("cleaned_deliveries.csv", index=False)
            
        logging.info("Cleaned data successfully saved to 'cleaned_matches.csv' and 'cleaned_deliveries.csv'.")
        
        return matches, deliveries

    except pd.errors.EmptyDataError:
        logging.error("One of the CSV files is completely empty.")
    except Exception as e:
        # Final catch-all to prevent application crash
        logging.error(f"An unexpected error occurred during the pipeline execution: {e}")
        
    return pd.DataFrame(), pd.DataFrame()

if __name__ == "__main__":
    # Run the pipeline (assumes matches.csv and deliveries.csv exist in the directory)
    clean_and_process_data('matches.csv', 'deliveries.csv')
