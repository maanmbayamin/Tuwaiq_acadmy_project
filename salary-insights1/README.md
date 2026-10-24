# Data & AI Salaries

An analysis of 13,972 salary records for data and AI jobs (2020 to 2024), a comparison between Saudi Arabia and the rest of the world, and a model that estimates salaries. It comes with a 6-page interactive Streamlit app.

## What is inside

```
salary-insights/
├── app.py                      # Streamlit entry point (top navigation + currency switch)
├── utils.py                    # Data loading, currency helpers, chart style
├── views/
│   ├── overview.py             # 1. Overview
│   ├── the_data.py             # 2. The Data
│   ├── explore.py              # 3. Explore Salaries
│   ├── saudi.py                # 4. Saudi Arabia vs the World
│   ├── model.py                # 5. How the Prediction Model Works
│   └── estimate.py             # 6. Estimate a Salary
├── notebooks/
│   └── salary_analysis.ipynb   # Full analysis: cleaning, EDA, Saudi comparison, modeling
├── data/
│   ├── salaries.csv                # Raw global data
│   ├── saudi_benchmark.csv         # Raw Saudi benchmark (11 ranges, SAR per month)
│   ├── salaries_clean.csv          # Clean data (created by the notebook)
│   ├── saudi_benchmark_clean.csv   # Clean benchmark (created by the notebook)
│   └── test_predictions.csv        # Test-set predictions used on page 5
├── models/
│   ├── salary_model.pkl            # Final model + two range models
│   └── model_metadata.json         # Metrics, feature importance, form options
├── .streamlit/config.toml      # Theme
└── requirements.txt
```

## Key results

- **Experience** and **company country** are the strongest drivers of salary, followed by **job family**.
- Machine Learning & AI and Research roles pay the most. Analytics & BI pays the least.
- On-site and remote jobs pay about the same.
- **Saudi Arabia:** individual roles (analyst, data scientist) pay below the US but similar to or above many European countries. Leadership roles (Head of Data, AI, ML) are paid above the global median.
- **Best model:** Gradient Boosting. Test R² = 0.40, average error (MAE) about $38K. Each estimate also has a likely range (10th to 90th percentile) that contains the real salary about 78% of the time.

## Data decisions

- **Duplicates** (38% of rows share the same values with a different ID) stay in the charts and are removed before training.
- **Job titles** with the same meaning were merged (146 titles became 120), then grouped into 7 job families.
- `salary` and `salary_currency` are not used as features because `salary_in_usd` is computed from them (data leakage).
- **Outliers** (IQR method) are flagged and kept in the charts, removed for training.
- **Saudi Arabia** has only 2 rows in the global data, so Saudi numbers come from the benchmark file. Currency: 1 USD = 3.75 SAR.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

To re-run the notebook you also need: `pip install seaborn matplotlib pycountry jupyter`.

## Publish a shareable link (Streamlit Community Cloud, free)

1. Create a new **public** GitHub repository and upload everything in this folder (keep the same structure, including the hidden `.streamlit` folder).
2. Go to **share.streamlit.io** and sign in with GitHub.
3. Click **Create app**, then choose **Deploy a public app from GitHub**.
4. Select your repository, branch `main`, and main file path **`app.py`**.
5. Open **Advanced settings** and choose **Python 3.13**.
6. Click **Deploy**. After a few minutes you get a link like `https://your-app-name.streamlit.app` that anyone can open.

If you change the notebook and re-run it, commit the new files in `data/` and `models/` so the app uses them.
