from flask import Flask, request, render_template
import requests
import os
from anthropic import Anthropic
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)

def extract_video_id(url):
    # Extract video ID from YouTube URL
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_description(video_id):
    api_key = os.getenv('YOUTUBE_API_KEY')
    url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'items' in data and data['items']:
            return data['items'][0]['snippet']['description']
    return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([item['text'] for item in transcript])
    except:
        return None

def extract_exercises(text):
    client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""Extract all workout exercises from the following text with clear timing/sets and reps details.

Text: {text}

Instructions:
- Determine if this is a timed interval workout (e.g., "40s work / 20s rest", "EMOM", "AMRAP", etc.) or a traditional sets/reps workout.
- If timed interval, include a top section with the global interval format, e.g.:
  Timing: 40s work / 20s rest
- For each exercise, output a bullet item with one of:
  - Exercise name: X sets x Y reps
  - Exercise name: X sets x Y reps + Z rest
  - Exercise name: X minutes (or seconds) work / Y seconds rest
  - Exercise name: X rounds
- If both types are present, include both with context in bullets.
- Preserve ordering of exercises as they appear.
- If no concrete exercises can be extracted, return an empty list.

Output format:
- Exercise 1: ...
- Exercise 2: ...

Also include a brief line at top when interval format is detected:
Timing: <work/rest interval>

Only provide the final bullet list (no extra commentary)."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    exercises = response.content[0].text.strip()
    return exercises if exercises else None

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            video_id = extract_video_id(url)
            if video_id:
                description = get_video_description(video_id)
                if description:
                    results = extract_exercises(description)
                if not results:
                    transcript = get_transcript(video_id)
                    if transcript:
                        results = extract_exercises(transcript)
            else:
                results = "Invalid YouTube URL"
    return render_template('index.html', results=results)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)