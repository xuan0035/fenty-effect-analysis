# The Fenty Effect: Data-Driven Analysis of Inclusivity in Cosmetic Shade Ranges

A data science project analyzing whether Fenty Beauty's 2017 launch (with its groundbreaking 40-shade range) drove a measurable industry-wide shift in foundation shade diversity across U.S. cosmetic brands from 2016 to 2025.

## Overview

This project uses regression modeling and cross-validation to test two hypotheses:
- **Primary:** Did release year predict higher shade counts, particularly after 2017?
- **Secondary:** Did newer product lines target narrower tonal ranges (lower lightness variance), suggesting market segmentation?

## Methods

Four model specifications were compared for the primary outcome (shade count):

| Model | Description |
|-------|-------------|
| M1 | Linear regression: `shade_count ~ year` |
| M2 | Linear regression: `shade_count ~ year + brand` (103 brand dummies) |
| M3 | LASSO on M2 predictors (regularization to handle brand sparsity) |
| M4 | Segmented (piecewise) regression with explicit Fenty break at 2017 |

All models were evaluated using 5-fold cross-validation with RMSE as the primary metric. The train/CV gap was used as an overfitting diagnostic.

Three additional models (L1–L3) mirrored M1–M3 with lightness variance as the outcome to test the segmentation hypothesis.

## Key Findings

- Release year showed a positive association with shade count, with a measurable level shift at 2017
- Brand-level disparities persisted despite overall industry progress
- LASSO regularization outperformed the full brand dummy model on CV RMSE, confirming overfitting in M2
- Lightness variance analysis provided evidence on whether brands began targeting narrower tonal ranges post-Fenty

## Tech Stack

- **Python:** pandas, NumPy, scikit-learn (LinearRegression, LassoCV, KFold, Pipeline, StandardScaler)
- **Visualization:** matplotlib
- **Data:** U.S. foundation product data (2016–2025), aggregated to product-line level

## Repository Structure

```
├── data/
│   └── 02-processed/          # Cleaned and merged shade-level dataset
├── fenty_effect_109_final.ipynb  # Main analysis notebook
└── merge_df.py                # Data merging and preprocessing script
```

## How to Run

1. Clone the repo
2. Install dependencies: `pip install pandas numpy scikit-learn matplotlib`
3. Run the notebook in order: each section maps directly to a section of the analysis