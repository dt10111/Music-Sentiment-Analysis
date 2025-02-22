# Music Sentiment Analysis

A Python-based system that analyzes songs to extract themes and calculate a "happiness score" using natural language processing and machine learning. This tool processes song data from a MySQL database, fetches lyrics from Genius, and uses both traditional NLP and the Mistral-7B model to analyze song content.

## Key Features

- Extracts lyrics from Genius API for given songs
- Generates thematic analysis using GPT4All's Mistral-7B model
- Calculates a happiness score based on multiple factors:
  - Semantic analysis of lyrics and themes using RoBERTa embeddings
  - Musical features (tempo and valence)
  - Contextual understanding of sensitive topics
- Processes daily song additions automatically
- Stores results in a MySQL database for further analysis

## Components

### Theme Extraction (`get_themes.py`)
- Fetches lyrics using Genius API
- Uses Mistral-7B to identify prominent themes
- Cleans and formats theme data
- Updates database with lyrics and themes

### Happiness Analysis (`get_happiness.py`)
- Utilizes the `sentence-transformers/all-distilroberta-v1` model
- Compares song content against curated happy/sad reference phrases
- Incorporates musical features for a comprehensive score
- Handles edge cases and sensitive content
- Implements batch processing with error handling

## Technical Stack

- Python 3.x
- MySQL
- GPT4All (Mistral-7B model)
- Hugging Face Transformers
- BeautifulSoup4
- Genius API
- pandas
- scikit-learn

## Requirements

- MySQL database
- GPT4All with Mistral-7B model
- Python environment with required packages
- Genius API credentials
- Environment variables for database configuration

## Usage

```python
# Run the complete analysis pipeline
python song_themes.py
```

This will process new songs added to the database, extract themes, and calculate happiness scores.
