import warnings
from transformers import logging
import MySQLdb
import MySQLdb.constants.CLIENT
import pandas as pd
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import math
import torch
from dotenv import load_dotenv

load_dotenv()



# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
logging.set_verbosity_error()

# Define sigmoid function
def sigmoid(x):
    return 1 / (1 + math.exp(-x))

# Function to get the embedding for a given text
def get_embedding(text, model, tokenizer, max_length):
    if text is None or not isinstance(text, str) or text.strip() == "":
        return None  # Return None for invalid inputs

    try:
        # Decode if it's bytes
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')

        # Tokenize the text
        tokens = tokenizer.encode(text, add_special_tokens=True)
        
        # If the text is too long, use a sliding window approach
        if len(tokens) > max_length:
            embeddings = []
            for i in range(0, len(tokens) - max_length + 1, max_length // 2):  # 50% overlap
                chunk = tokens[i:i+max_length]
                input_ids = torch.tensor([chunk]).to(model.device)
                with torch.no_grad():
                    outputs = model(input_ids)
                embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy())
            
            # Average the embeddings of all chunks
            return np.mean(embeddings, axis=0)
        else:
            # For shorter texts, process as before
            input_ids = torch.tensor([tokens]).to(model.device)
            with torch.no_grad():
                outputs = model(input_ids)
            return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
    except Exception as e:
        print(f"Error generating embedding for text: {text[:50]}..., error: {e}")
        return None

# Function to get the appropriate text to use (lyrics or ai_theme)
def get_text_for_embedding(lyrics, ai_theme):
    # Ensure the lyrics and ai_theme are strings, use empty string if None
    lyrics = str(lyrics).strip() if lyrics is not None else ""
    ai_theme = str(ai_theme).strip() if ai_theme is not None else ""

    # If both are empty, return None
    if not lyrics and not ai_theme:
        return None

    # Use lyrics if available, otherwise use ai_theme
    return lyrics if lyrics else ai_theme

def get_happiness(lyrics, ai_theme, tempo, valence):
    # Load the model and tokenizer
    model_name = "sentence-transformers/all-distilroberta-v1"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    max_length = tokenizer.model_max_length

    # Define the expanded themes dictionary with reference and opposite phrases for happiness
    themes = {
        "happiness": {
            "reference_themes": [
                "happiness", "bliss","heaven", "euphoria","jubilation","joy",
                "delight", "laughing with friends","elation","mirth","jubilation","delight","rapture"
            ],
            "opposite_themes": [
                "unhappiness", "oppressed","deep sadness", "hopelessness", "entrapment",
                "misery", "sorrow", "anguish","agony","woe","desolation","gloom", "profound sadness", "despair", "horrific suffering", 
                "mourning a tragedy", "horror","terror", "trauma",
                "grief", "hopelessness", "feeling haunted by memories"
            ]
        }
    }

    # Pre-calculate embeddings for reference and opposite phrases of happiness
    reference_embeddings_happy = [get_embedding(phrase, model, tokenizer, max_length) for phrase in themes["happiness"]["reference_themes"]]
    opposite_embeddings_sad = [get_embedding(phrase, model, tokenizer, max_length) for phrase in themes["happiness"]["opposite_themes"]]

    # Remove None embeddings from the lists
    reference_embeddings_happy = [emb for emb in reference_embeddings_happy if emb is not None]
    opposite_embeddings_sad = [emb for emb in opposite_embeddings_sad if emb is not None]

    # Ensure that we have valid embeddings for both references and opposites
    if not reference_embeddings_happy or not opposite_embeddings_sad:
        raise ValueError("Failed to generate valid embeddings for reference or opposite phrases of happiness.")

    # Convert tempo and valence to float, with error handling
    try:
        tempo = float(tempo) if tempo is not None else 120  # Default to 120 if None
        valence = float(valence) if valence is not None else 0.5  # Default to 0.5 if None
    except ValueError:
        print(f"Invalid tempo or valence value: tempo={tempo}, valence={valence}")
        return None

    # Get the appropriate text to use
    text = get_text_for_embedding(lyrics, ai_theme)
    if text is None:
        print(f"No valid text found for embedding. Lyrics: {lyrics[:50]}..., AI Theme: {ai_theme[:50]}...")
        return None

    theme_embedding = get_embedding(text, model, tokenizer, max_length)
    if theme_embedding is None:
        return None  # Return None if the embedding cannot be obtained

    # Calculate similarity to all happy-related phrases
    similarities_to_happy = [cosine_similarity([ref_emb], [theme_embedding])[0][0] for ref_emb in reference_embeddings_happy]
    avg_similarity_to_happy = sum(similarities_to_happy) / len(similarities_to_happy)

    # Calculate similarity to all sad-related phrases
    similarities_to_sad = [cosine_similarity([opp_emb], [theme_embedding])[0][0] for opp_emb in opposite_embeddings_sad]
    avg_similarity_to_sad = sum(similarities_to_sad) / len(similarities_to_sad)

    # Apply a scaling factor to amplify the difference between positive and negative similarities
    scaling_factor = 45  # Use a higher scaling factor for more spread
    difference = avg_similarity_to_happy - avg_similarity_to_sad
    scaled_difference = scaling_factor * difference

    # Apply sigmoid function for non-linear transformation
    text_score = sigmoid(scaled_difference)

    # Tempo adjustment with diminishing returns past 160 BPM
    if tempo <= 0:
        tempo_score = 0
    elif tempo <= 160:
        tempo_score = tempo / 160
    elif tempo <= 240:
        # Use a logarithmic curve for diminishing returns between 160 and 240 BPM
        base_score = 1  # Score at 160 BPM
        max_additional = 0.25  # Maximum additional score between 160 and 240 BPM
        normalized_tempo = (tempo - 160) / (240 - 160)
        additional_score = max_additional * (math.log(normalized_tempo * 19 + 1) / math.log(20))
        tempo_score = base_score + additional_score
    else:
        tempo_score = 1.25  # Maximum score, same as at 240 BPM

    # Normalize tempo_score to be between 0 and 1
    tempo_score = tempo_score / 1.25

    # Combine scores
    final_score = 0.6 * text_score + 0.2 * valence + 0.2 * tempo_score

    # Ensure the score is between 0.01 and 1.0
    final_score = max(0.01, min(final_score, 1.0))

    # Adjust score for known dark themes
    if "racial violence" in text.lower() or "lynching" in text.lower() or "horrific suffering" in text.lower():
        final_score = 0.01  # Force score to 0.01 for themes of extreme violence or suffering

    return final_score

def happiness():
    # Database connection setup
    db = MySQLdb.Connection(
        host=os.getenv('BI_HOST'),
        user=os.getenv('BI_USER'),
        password=os.getenv('BI_PASS'),
        port=3306,
        db=os.getenv('BI_DB_NAME'),
    )
    cursor = db.cursor()
    
    # The query
    query = """
        SELECT
            t.spotify_id,
            t.artist_spotify_id AS artist_id,
            t.lyrics,
            t.song_themes as ai_theme,
            t.name,
            t.album,
            t.tempo,
            t.valence
        FROM
            playlist_app.tracks t
        WHERE
            t.song_themes IS NOT NULL
            and t.happiness IS NULL
    """
    
    # Execute the query
    cursor.execute(query)
    
    # Fetch all rows from the executed query
    rows = cursor.fetchall()
    columns = ["spotify_id", "artist_id", "lyrics", "ai_theme", "name", "album", "tempo", "valence"]
    
    # Convert the fetched rows into a pandas DataFrame
    df = pd.DataFrame(rows, columns=columns)
    
    # Close the database connection
    cursor.close()
    db.close()
    
    # Debug information
    print("DataFrame shape:", df.shape)
    print("DataFrame columns:", df.columns)
    print("Number of rows fetched:", len(rows))

    if df.empty:
        print("No data returned from the query. Exiting function.")
        return
    
    print("First row:", df.iloc[0].to_dict())

    # Convert tempo and valence to numeric values
    df['tempo'] = pd.to_numeric(df['tempo'], errors='coerce')
    df['valence'] = pd.to_numeric(df['valence'], errors='coerce')

    # Safely calculate happiness ratings
    def safe_get_happiness(row):
        try:
            return get_happiness(row['lyrics'], row['ai_theme'], row['tempo'], row['valence'])
        except Exception as e:
            print(f"Error processing row: {row}")
            print(f"Error message: {str(e)}")
            return None

    # Create new column using the safe function
    df['happiness_rating'] = df.apply(safe_get_happiness, axis=1)

    # Check for any null values in the new column
    print("Null values in happiness_rating:", df['happiness_rating'].isnull().sum())

    # Initialize an array to store the rows to be updated
    update_data = []

    # Process each row in the DataFrame and calculate the happiness score
    for index, row in df.iterrows():
        spotify_id = row['spotify_id']
        tempo = row['tempo']
        valence = row['valence']
        lyrics = row['lyrics']
        ai_theme = row['ai_theme']
        
        # Skip rows with invalid tempo, valence, or missing text data
        if pd.isna(tempo) or pd.isna(valence):
            print(f"Skipping row due to invalid tempo or valence: spotify_id={spotify_id}, tempo={tempo}, valence={valence}")
            continue
        
        happiness_score = row['happiness_rating']
        if happiness_score is not None:
            update_data.append((happiness_score, spotify_id))
        else:
            print(f"Failed to calculate happiness score for spotify_id={spotify_id}")

    # Database update function
    def execute_bulk_update(update_data):
            db = MySQLdb.Connection(
            host=os.getenv('BI_HOST'),
            user=os.getenv('BI_USER'),
            password=os.getenv('BI_PASS'),
            port=3306,
            db=os.getenv('BI_DB_NAME'),
            client_flag=MySQLdb.constants.CLIENT.MULTI_STATEMENTS
        )
        cursor = db.cursor()

        update_query = """
            UPDATE playlist_app.tracks
            SET happiness = %s
            WHERE spotify_id = %s;
        """

        try:
            print("Executing bulk update with executemany:")
            cursor.executemany(update_query, update_data)
            db.commit()
            print(f"Successfully updated {cursor.rowcount} rows.")
        except Exception as e:
            db.rollback()
            print(f"Error updating database: {e}")
        finally:
            cursor.close()
            db.close()

    # Execute the bulk update
    if update_data:
        execute_bulk_update(update_data)
    else:
        print("No data to update in the database.")

    # Save to CSV
    output_csv_path = 'tracks_with_happiness_rating_debug.csv'
    df.to_csv(output_csv_path, index=False, na_rep='NULL')

    print(f"CSV file saved as '{output_csv_path}' with happiness ratings.")

# Main execution
if __name__ == "__main__":
    happiness()
