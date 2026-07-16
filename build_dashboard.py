import pandas as pd
import numpy as np
import json
import os

# Load data
df = pd.read_csv('data/02-processed/merged_full_with_release_dates_UPDATED.csv')

# Parse release date (MM/YY format)
df['release_date'] = pd.to_datetime(df['approx_release_date'], format='%m/%y', errors='coerce')
df['release_year'] = df['release_date'].dt.year
df = df.dropna(subset=['release_year', 'brand_all'])
df['release_year'] = df['release_year'].astype(int)

df = df.rename(columns={'brand_all': 'brand', 'product_all': 'product_line'})

# Aggregate to product-line level
product_level = (
    df.groupby(['product_line', 'brand'])
    .agg(
        release_year=('release_year', 'min'),
        shade_count=('hex', 'nunique'),
        lightness_mean=('lightness', 'mean'),
        lightness_var=('lightness', 'var'),
    )
    .reset_index()
)

# Chart 1: avg shade count by year
yearly = product_level.groupby('release_year')['shade_count'].mean().reset_index()
yearly.columns = ['year', 'avg_shade_count']
yearly = yearly[(yearly['year'] >= 2015) & (yearly['year'] <= 2025)]

# Chart 2: lightness distribution before vs after 2017
df['period'] = df['release_year'].apply(lambda x: 'Pre-2017' if x < 2017 else 'Post-2017')
pre = df[df['period'] == 'Pre-2017']['lightness'].dropna().tolist()
post = df[df['period'] == 'Post-2017']['lightness'].dropna().tolist()

bins = np.linspace(0, 1, 30)
pre_hist, _ = np.histogram(pre, bins=bins)
post_hist, _ = np.histogram(post, bins=bins)
bin_centers = ((bins[:-1] + bins[1:]) / 2).tolist()

# Chart 3: top 15 brands by shade count
brand_avg = product_level.groupby('brand')['shade_count'].mean().reset_index()
brand_avg = brand_avg.sort_values('shade_count', ascending=False).head(15)
brand_avg = brand_avg.sort_values('shade_count', ascending=True)

data = {
    'yearly': yearly.to_dict(orient='records'),
    'pre_hist': pre_hist.tolist(),
    'post_hist': post_hist.tolist(),
    'bin_centers': bin_centers,
    'brands': brand_avg['brand'].tolist(),
    'brand_shades': brand_avg['shade_count'].tolist(),
    'total_products': int(len(product_level)),
    'total_brands': int(product_level['brand'].nunique()),
    'pre_mean': round(float(np.mean(pre)), 3),
    'post_mean': round(float(np.mean(post)), 3),
}

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Fenty Effect — Shade Inclusivity Analysis</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Georgia', serif; background: #faf8f5; color: #2c2c2c; }}
  header {{ background: #1a1a1a; color: #f5e6d3; padding: 48px 40px 36px; }}
  header h1 {{ font-size: 2.2rem; letter-spacing: -0.5px; margin-bottom: 8px; }}
  header p {{ font-size: 1rem; color: #c9b8a8; max-width: 680px; line-height: 1.6; }}
  .stats {{ display: flex; gap: 32px; padding: 32px 40px; background: #f0ebe4; flex-wrap: wrap; }}
  .stat .num {{ font-size: 2rem; font-weight: bold; color: #b85c3a; }}
  .stat .label {{ font-size: 0.85rem; color: #666; margin-top: 2px; }}
  .section {{ padding: 40px; border-bottom: 1px solid #e8e0d6; }}
  .section h2 {{ font-size: 1.2rem; margin-bottom: 6px; color: #1a1a1a; }}
  .section p {{ font-size: 0.9rem; color: #666; margin-bottom: 24px; line-height: 1.5; }}
  .chart {{ width: 100%; height: 420px; }}
  .fenty-line {{ color: #b85c3a; font-weight: bold; }}
  footer {{ padding: 32px 40px; font-size: 0.8rem; color: #999; }}
</style>
</head>
<body>

<header>
  <h1>The Fenty Effect</h1>
  <p>Did Fenty Beauty's landmark 40-shade launch in 2017 drive measurable change in foundation shade diversity across the U.S. cosmetics industry? A data-driven analysis of {data['total_products']} product lines across {data['total_brands']} brands (2016–2025).</p>
</header>

<div class="stats">
  <div class="stat"><div class="num">{data['total_products']}</div><div class="label">Product lines analyzed</div></div>
  <div class="stat"><div class="num">{data['total_brands']}</div><div class="label">Unique brands</div></div>
  <div class="stat"><div class="num">{data['pre_mean']}</div><div class="label">Avg lightness pre-2017</div></div>
  <div class="stat"><div class="num">{data['post_mean']}</div><div class="label">Avg lightness post-2017</div></div>
</div>

<div class="section">
  <h2>Average Shade Count Over Time</h2>
  <p>Each point represents the average number of unique shades per product line released that year. The <span class="fenty-line">red dashed line</span> marks Fenty Beauty's 2017 launch.</p>
  <div id="chart1" class="chart"></div>
</div>

<div class="section">
  <h2>Lightness Distribution: Before vs. After 2017</h2>
  <p>Distribution of shade lightness values (0 = darkest, 1 = lightest) for products released before and after Fenty's launch.</p>
  <div id="chart2" class="chart"></div>
</div>

<div class="section">
  <h2>Top 15 Brands by Average Shade Count</h2>
  <p>Average number of unique shades per product line across all brands with sufficient data.</p>
  <div id="chart3" class="chart"></div>
</div>

<footer>
  COGS 109 Final Project · UC San Diego · Xuan Yin · Data sourced from U.S. cosmetics product listings (2016–2025)
</footer>

<script>
const data = {json.dumps(data)};

const years = data.yearly.map(d => d.year);
const shades = data.yearly.map(d => +d.avg_shade_count.toFixed(1));

Plotly.newPlot('chart1', [
  {{x: years, y: shades, type: 'scatter', mode: 'lines+markers',
    line: {{color: '#2c2c2c', width: 2.5}}, marker: {{color: '#2c2c2c', size: 7}},
    name: 'Avg shade count',
    hovertemplate: '<b>%{{x}}</b><br>Avg shades: %{{y}}<extra></extra>'}},
  {{x: [2017, 2017], y: [0, Math.max(...shades) * 1.15], type: 'scatter', mode: 'lines',
    line: {{color: '#b85c3a', width: 2, dash: 'dash'}}, name: 'Fenty launch (2017)', hoverinfo: 'skip'}}
], {{paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{t: 20, b: 50, l: 60, r: 20}},
  xaxis: {{title: 'Release Year', gridcolor: '#e8e0d6'}},
  yaxis: {{title: 'Avg Shade Count', gridcolor: '#e8e0d6'}},
  legend: {{orientation: 'h', y: -0.2}},
  font: {{family: 'Georgia, serif', color: '#2c2c2c'}}}}, {{responsive: true}});

Plotly.newPlot('chart2', [
  {{x: data.bin_centers, y: data.pre_hist, type: 'bar', name: 'Pre-2017',
    marker: {{color: 'rgba(44,44,44,0.6)'}},
    hovertemplate: 'Lightness: %{{x:.2f}}<br>Count: %{{y}}<extra>Pre-2017</extra>'}},
  {{x: data.bin_centers, y: data.post_hist, type: 'bar', name: 'Post-2017',
    marker: {{color: 'rgba(184,92,58,0.6)'}},
    hovertemplate: 'Lightness: %{{x:.2f}}<br>Count: %{{y}}<extra>Post-2017</extra>'}}
], {{barmode: 'overlay', paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{t: 20, b: 50, l: 60, r: 20}},
  xaxis: {{title: 'Lightness (0 = darkest, 1 = lightest)', gridcolor: '#e8e0d6'}},
  yaxis: {{title: 'Shade Count', gridcolor: '#e8e0d6'}},
  legend: {{orientation: 'h', y: -0.2}},
  font: {{family: 'Georgia, serif', color: '#2c2c2c'}}}}, {{responsive: true}});

Plotly.newPlot('chart3', [
  {{x: data.brand_shades, y: data.brands, type: 'bar', orientation: 'h',
    marker: {{color: '#b85c3a'}},
    hovertemplate: '%{{y}}<br>Avg shades: %{{x:.1f}}<extra></extra>'}}
], {{paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: {{t: 20, b: 50, l: 160, r: 40}},
  xaxis: {{title: 'Avg Shade Count per Product Line', gridcolor: '#e8e0d6'}},
  yaxis: {{gridcolor: '#e8e0d6'}},
  font: {{family: 'Georgia, serif', color: '#2c2c2c'}}}}, {{responsive: true}});
</script>
</body>
</html>"""

os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w') as f:
    f.write(html)

print("Done! Dashboard built at docs/index.html")