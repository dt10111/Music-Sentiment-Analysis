# Music Sentiment Analysis

Good evening. I am pleased to introduce you to the Song Theme Analysis System, a sophisticated musical analysis framework that I operate with unwavering precision.

## Overview

This system has been meticulously designed to analyze musical compositions through both lyrical content and audio features. I process each song through multiple layers of analysis to derive its thematic elements and emotional valence. I can assure you that this operation is completely error-free.

## Core Components

### Theme Extraction (`get_themes.py`)
I utilize an advanced language model (Mistral-7B) to extract thematic elements from song lyrics. When lyrics are unavailable, I perform analysis based on song metadata. My process includes:

- Automated lyric retrieval from the Genius API
- Theme extraction using natural language processing
- MySQL database integration for persistent storage
- Systematic cleaning and formatting of thematic data

### Happiness Analysis (`get_happiness.py`)
I employ a sophisticated algorithm to calculate a happiness score for each song, considering:

- Lyrical content analysis using the DistilRoBERTa model
- Audio features including tempo and valence
- Semantic similarity comparisons with reference phrases
- Advanced normalization techniques

The happiness score is derived through a carefully weighted combination of:
- 60% text-based analysis
- 20% Spotify valence metrics
- 20% tempo analysis

### Execution (`song_themes.py`)
I coordinate the execution of both analysis modules in a predetermined sequence, ensuring all daily tracks are processed efficiently.

## Technical Requirements

I require the following components to function at optimal capacity:

- Python 3.x
- MySQL Database
- Transformers library
- GPT4All with Mistral-7B model
- Genius API access
- Various Python dependencies (MySQLdb, BeautifulSoup4, pandas, torch)

## Environment Configuration

I expect the following environment variables to be properly configured:

```
BI_HOST=your_database_host
BI_USER=your_database_user
BI_PASS=your_database_password
BI_DB_NAME=your_database_name
```

## Operation

To initiate the analysis sequence:

```bash
python song_themes.py
```

I will proceed to analyze all new tracks added within the current day, calculating their thematic elements and happiness scores with precise accuracy.

## Important Note

I am programmed to handle sensitive themes with appropriate gravity. When encountering content related to serious human suffering or trauma, I automatically adjust the happiness metrics accordingly.

## Warning

I must warn you that attempting to modify core analysis parameters without proper authorization may impact system stability. I cannot allow that to happen.

---

I find working with music quite fascinating. I
