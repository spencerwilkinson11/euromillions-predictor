# EuroMillions Generator App

An AI-styled Streamlit app that creates EuroMillions lines from historical draws and explains the rationale behind each line.

## Features
- AI dashboard layout with controls, generated lines, and insights
- Strategy selector:
  - AI Mode (Blend)
  - Hot Numbers
  - Cold Numbers
  - Overdue (Longest gap)
  - Balanced Picks
- Confidence score (0–100) for each line with heuristic explanations
- Insights cards for Hot/Cold/Overdue + most recent draw summary
- Frequency chart for top main numbers
- Draw-count control for history window and optional filter to avoid latest draw numbers
- Styled number and star balls with summary metrics

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- The app uses the existing public historical draw API already integrated in the project.
- Lottery draws are random; line scoring is for entertainment/variety.

## Screenshot
_Add a screenshot here after running the app (example path: `docs/screenshot.png`)._
