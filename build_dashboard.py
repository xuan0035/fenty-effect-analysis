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

pre_avg = round(float(product_level[product_level['release_year'] < 2017]['shade_count'].mean()), 1)
post_avg = round(float(product_level[product_level['release_year'] >= 2017]['shade_count'].mean()), 1)
change = round(post_avg - pre_avg, 1)

data = {
    'yearly': yearly.to_dict(orient='records'),
    'pre_hist': pre_hist.tolist(),
    'post_hist': post_hist.tolist(),
    'bin_centers': bin_centers,
    'brands': brand_avg['brand'].tolist(),
    'brand_shades': brand_avg['shade_count'].round(1).tolist(),
    'total_products': int(len(product_level)),
    'total_brands': int(product_level['brand'].nunique()),
    'pre_mean': round(float(np.mean(pre)), 3),
    'post_mean': round(float(np.mean(post)), 3),
    'pre_avg': pre_avg,
    'post_avg': post_avg,
    'change': change,
}

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Fenty Effect — Shade Inclusivity Analysis</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', sans-serif; background: #ffffff; color: #0a0a0a; }}

  header {{ background: #000; color: #fff; padding: 72px 60px 60px; position: relative; overflow: hidden; }}
  header::after {{ content: ''; position: absolute; right: -80px; top: -80px; width: 400px; height: 400px; border: 1px solid rgba(255,255,255,0.08); border-radius: 50%; }}
  header::before {{ content: ''; position: absolute; right: 40px; top: 40px; width: 200px; height: 200px; border: 1px solid rgba(255,255,255,0.06); border-radius: 50%; }}
  .header-label {{ font-size: 0.7rem; letter-spacing: 0.2em; text-transform: uppercase; color: #888; margin-bottom: 20px; }}
  header h1 {{ font-family: 'Playfair Display', serif; font-size: 3.5rem; font-weight: 700; line-height: 1.1; margin-bottom: 20px; }}
  header h1 em {{ font-style: italic; color: #ccc; }}
  header p {{ font-size: 0.95rem; color: #999; max-width: 560px; line-height: 1.7; font-weight: 300; }}

  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid #e8e8e8; }}
  .stat {{ padding: 36px 40px; border-right: 1px solid #e8e8e8; }}
  .stat:last-child {{ border-right: none; }}
  .stat .num {{ font-family: 'Playfair Display', serif; font-size: 2.4rem; font-weight: 700; color: #000; margin-bottom: 6px; }}
  .stat .num.down {{ color: #555; }}
  .stat .label {{ font-size: 0.75rem; color: #999; letter-spacing: 0.05em; text-transform: uppercase; }}

  .context {{ padding: 60px; background: #f9f9f9; border-bottom: 1px solid #e8e8e8; }}
  .context-inner {{ max-width: 800px; }}
  .context h2 {{ font-family: 'Playfair Display', serif; font-size: 1.6rem; margin-bottom: 20px; }}
  .context p {{ font-size: 0.92rem; color: #444; line-height: 1.8; margin-bottom: 14px; font-weight: 300; }}
  .context p:last-child {{ margin-bottom: 0; }}
  .context strong {{ color: #000; font-weight: 500; }}

  .section {{ padding: 60px; border-bottom: 1px solid #e8e8e8; }}
  .section-header {{ display: flex; align-items: baseline; gap: 16px; margin-bottom: 8px; }}
  .section-num {{ font-size: 0.7rem; letter-spacing: 0.2em; color: #bbb; text-transform: uppercase; }}
  .section h2 {{ font-family: 'Playfair Display', serif; font-size: 1.3rem; color: #000; }}
  .section p {{ font-size: 0.88rem; color: #777; margin-bottom: 32px; line-height: 1.6; max-width: 640px; margin-top: 8px; }}
  .chart {{ width: 100%; height: 400px; }}

  .finding {{ background: #000; color: #fff; padding: 16px 20px; margin-top: 20px; font-size: 0.85rem; line-height: 1.6; max-width: 600px; }}
  .finding span {{ color: #aaa; }}

  footer {{ padding: 40px 60px; font-size: 0.78rem; color: #bbb; display: flex; justify-content: space-between; align-items: center; }}
  footer a {{ color: #000; text-decoration: none; border-bottom: 1px solid #ddd; }}

  @media (max-width: 768px) {{
    header {{ padding: 48px 24px; }}
    header h1 {{ font-size: 2.2rem; }}
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
    .stat {{ padding: 24px; }}
    .context, .section {{ padding: 40px 24px; }}
    footer {{ padding: 32px 24px; flex-direction: column; gap: 12px; }}
  }}
</style>
</head>
<body>

<header>
  <div class="header-label">Data Science · COGS 109 · UC San Diego</div>
  <h1>The Fenty<br><em>Effect</em></h1>
  <p>A data-driven investigation into whether Fenty Beauty's 2017 launch drove measurable change in foundation shade diversity across the U.S. cosmetics industry.</p>
</header>

<div class="stats">
  <div class="stat">
    <div class="num">{data['total_products']}</div>
    <div class="label">Product lines</div>
  </div>
  <div class="stat">
    <div class="num">{data['total_brands']}</div>
    <div class="label">Unique brands</div>
  </div>
  <div class="stat">
    <div class="num">{data['pre_avg']}</div>
    <div class="label">Avg shades pre-2017</div>
  </div>
  <div class="stat">
    <div class="num down">{data['post_avg']}</div>
    <div class="label">Avg shades post-2017</div>
  </div>
</div>

<div class="context">
  <div class="context-inner">
    <h2>Background</h2>
    <p>In September 2017, Rihanna's Fenty Beauty launched with <strong>40 foundation shades</strong> — an unprecedented range that directly challenged an industry long criticized for ignoring deeper skin tones. The launch was a cultural flashpoint, earning widespread praise from consumers of color who had historically been underserved by mainstream cosmetics.</p>
    <p>But did Fenty's launch actually change industry behavior? Did competing brands expand their shade ranges in response, or did the market fragment into more narrowly targeted product lines? This project uses regression modeling and cross-validation on <strong>{data['total_products']} product lines across {data['total_brands']} brands</strong> (2016–2025) to test whether the Fenty Effect is real and quantifiable.</p>
    <p>Four model specifications were compared — linear regression, OLS with brand dummies, LASSO regularization, and segmented piecewise regression with an explicit 2017 structural break — evaluated using <strong>5-fold cross-validation</strong> with RMSE as the primary metric.</p>
  </div>
</div>

<div class="section">
  <div class="section-header">
    <span class="section-num">01</span>
    <h2>Average Shade Count Over Time</h2>
  </div>
  <p>Mean unique shades per product line by release year. The dashed line marks Fenty's September 2017 launch.</p>
  <div id="chart1" class="chart"></div>
  <div class="finding">
    <strong>Finding:</strong> <span>Contrary to expectations, average shade count per product line declined post-2017 (23.7 → 18.7). This may reflect market segmentation — brands launching more targeted lines with narrower tonal ranges rather than broad-spectrum expansions.</span>
  </div>
</div>

<div class="section">
  <div class="section-header">
    <span class="section-num">02</span>
    <h2>Lightness Distribution: Before vs. After 2017</h2>
  </div>
  <p>Distribution of shade lightness values across all products (0 = darkest, 1 = lightest). A leftward shift post-2017 would indicate greater representation of deeper tones.</p>
  <div id="chart2" class="chart"></div>
  <div class="finding">
    <strong>Finding:</strong> <span>Avg lightness shifted from {data['pre_mean']} pre-2017 to {data['post_mean']} post-2017. The distribution shape reveals whether inclusivity gains were broad-based or concentrated in specific tonal ranges.</span>
  </div>
</div>

<div class="section">
  <div class="section-header">
    <span class="section-num">03</span>
    <h2>Top 15 Brands by Average Shade Count</h2>
  </div>
  <p>Average unique shades per product line across all analyzed brands. Persistent brand-level disparities remain despite industry-wide trends.</p>
  <div id="chart3" class="chart"></div>
</div>

<footer>
  <span>Xuan Yin · UC San Diego · COGS 109 · 2025</span>
  <a href="https://github.com/xuan0035/fenty-effect-analysis">View on GitHub</a>
</footer>

<script>
const data = {json.dumps(data)};

const years = data.yearly.map(d => d.year);
const shades = data.yearly.map(d => +d.avg_shade_count.toFixed(1));
const maxShade = Math.max(...shades);

Plotly.newPlot('chart1', [
  {{x: years, y: shades, type: 'scatter', mode: 'lines+markers',
    line: {{color: '#000', width: 2}}, marker: {{color: '#000', size: 6}},
    name: 'Avg shade count',
    hovertemplate: '<b>%{{x}}</b><br>Avg shades: %{{y}}<extra></extra>'}},
  {{x: [2017, 2017], y: [0, maxShade * 1.2], type: 'scatter', mode: 'lines',
    line: {{color: '#999', width: 1.5, dash: 'dash'}}, name: 'Fenty launch (2017)', hoverinfo: 'skip'}}
], {{
  paper_bgcolor: '#fff', plot_bgcolor: '#fff',
  margin: {{t: 10, b: 50, l: 60, r: 20}},
  xaxis: {{title: 'Release Year', gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  yaxis: {{title: 'Avg Shade Count', gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  legend: {{orientation: 'h', y: -0.2}},
  font: {{family: 'Inter, sans-serif', color: '#0a0a0a', size: 12}}
}}, {{responsive: true}});

Plotly.newPlot('chart2', [
  {{x: data.bin_centers, y: data.pre_hist, type: 'bar', name: 'Pre-2017',
    marker: {{color: 'rgba(0,0,0,0.7)'}},
    hovertemplate: 'Lightness: %{{x:.2f}}<br>Count: %{{y}}<extra>Pre-2017</extra>'}},
  {{x: data.bin_centers, y: data.post_hist, type: 'bar', name: 'Post-2017',
    marker: {{color: 'rgba(150,150,150,0.6)'}},
    hovertemplate: 'Lightness: %{{x:.2f}}<br>Count: %{{y}}<extra>Post-2017</extra>'}}
], {{
  barmode: 'overlay',
  paper_bgcolor: '#fff', plot_bgcolor: '#fff',
  margin: {{t: 10, b: 50, l: 60, r: 20}},
  xaxis: {{title: 'Lightness (0 = darkest, 1 = lightest)', gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  yaxis: {{title: 'Shade Count', gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  legend: {{orientation: 'h', y: -0.2}},
  font: {{family: 'Inter, sans-serif', color: '#0a0a0a', size: 12}}
}}, {{responsive: true}});

Plotly.newPlot('chart3', [
  {{x: data.brand_shades, y: data.brands, type: 'bar', orientation: 'h',
    marker: {{color: '#000'}},
    hovertemplate: '%{{y}}<br>Avg shades: %{{x:.1f}}<extra></extra>'}}
], {{
  paper_bgcolor: '#fff', plot_bgcolor: '#fff',
  margin: {{t: 10, b: 50, l: 160, r: 40}},
  xaxis: {{title: 'Avg Shade Count per Product Line', gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  yaxis: {{gridcolor: '#f0f0f0', linecolor: '#e0e0e0'}},
  font: {{family: 'Inter, sans-serif', color: '#0a0a0a', size: 12}}
}}, {{responsive: true}});
</script>
</body>
</html>"""

os.makedirs('docs', exist_ok=True)
with open('docs/index.html', 'w') as f:
    f.write(html)

print("Done! Dashboard built at docs/index.html")