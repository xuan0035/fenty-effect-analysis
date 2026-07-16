import pandas as pd
import time
import requests
from tqdm import tqdm
import os


CHECKPOINT_FILE = "data/02-processed/release_date_checkpoint.csv"
INPUT_FILE = "data/02-processed/merged_full_with_release_dates.csv"
OUTPUT_FILE = "data/02-processed/merged_full_with_release_dates_UPDATED_fast.csv"

WAYBACK_API = "http://web.archive.org/cdx/search/cdx"


# --------------------------
# Load main dataset
# --------------------------
df = pd.read_csv(INPUT_FILE)

# Load checkpoint if exists
if os.path.exists(CHECKPOINT_FILE):
    done_df = pd.read_csv(CHECKPOINT_FILE)
    already_done = set(done_df['index'].tolist())
    print(f"Resuming: {len(already_done)} products already processed.")
else:
    already_done = set()
    done_df = pd.DataFrame(columns=["index", "new_release_date"])
    print("No checkpoint found — starting fresh.")


# Identify missing rows
missing_df = df[df["approx_release_date"].isna()].copy()
missing_df = missing_df[~missing_df.index.isin(already_done)]

print(f"Total missing: {len(df[df['approx_release_date'].isna()])}")
print(f"Remaining to process: {len(missing_df)}\n")


# --------------------------
# Fast Wayback snapshots
# --------------------------
def get_snapshots(url, limit=10):
    """FAST version: fewer retries, tiny limit, no heavy backoffs."""
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original",
        "filter": "statuscode:200",
        "collapse": "digest",
        "limit": limit
    }
    try:
        resp = requests.get(WAYBACK_API, params=params, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            return data[1:] if len(data) > 1 else []
    except:
        return []
    return []


def get_earliest_wayback_date(url):
    url = str(url)
    # Try minimal variants
    variants = [
        url,
        url.split("?")[0],
        url.replace("https://", "http://"),
        url.replace("http://", "https://"),
    ]

    all_snaps = []

    for v in variants:
        snaps = get_snapshots(v, limit=8)
        all_snaps.extend(snaps)
        time.sleep(0.05)  # much faster than before

    if not all_snaps:
        return None

    times = [s[0] for s in all_snaps]
    earliest = min(times)

    return f"{earliest[4:6]}/{earliest[2:4]}"


# --------------------------
# Scrape loop (resume-safe)
# --------------------------
batch = []

try:
    for idx, row in tqdm(missing_df.iterrows(), total=len(missing_df)):

        url = row["url"]
        if pd.isna(url):
            batch.append((row.name, None))
            continue

        date = get_earliest_wayback_date(url)

        batch.append((row.name, date))

        # Save every 25 entries
        if len(batch) >= 25:
            temp_df = pd.DataFrame(batch, columns=["index", "new_release_date"])
            done_df = pd.concat([done_df, temp_df], ignore_index=True)
            done_df.to_csv(CHECKPOINT_FILE, index=False)
            batch = []
            print("Checkpoint saved.")

except KeyboardInterrupt:
    print("⏸ Interrupted by user — saving partial progress...")
finally:
    # Save whatever is left
    if batch:
        temp_df = pd.DataFrame(batch, columns=["index", "new_release_date"])
        done_df = pd.concat([done_df, temp_df], ignore_index=True)
    done_df.to_csv(CHECKPOINT_FILE, index=False)
    print("Final checkpoint saved.")


# --------------------------
# Merge into main CSV
# --------------------------
for _, r in done_df.iterrows():
    df.loc[int(r["index"]), "approx_release_date"] = r["new_release_date"]

df.to_csv(OUTPUT_FILE, index=False)

print("\n🎉 Done!")
print(f"Updated file written to: {OUTPUT_FILE}")
print(f"Missing remaining: {df['approx_release_date'].isna().sum()}")




# import pandas as pd
# import time
# from tqdm import tqdm
# import requests
# from datetime import datetime



# # =============================
# # LOAD DATA
# # =============================
# df = pd.read_csv("data/02-processed/merged_full_with_release_dates.csv")

# # Identify missing release dates
# missing_df = df[df["approx_release_date"].isna()].copy()

# print(f"Total products: {len(df)}")
# print(f"Missing release dates: {len(missing_df)}")

# # If nothing is missing, stop
# if len(missing_df) == 0:
#     print("No missing release dates left!")
# else:
#     print("Beginning scraping of missing rows...\n")

# # --- Improved Wayback scraper (only used for missing rows) ---


# WAYBACK_API = "http://web.archive.org/cdx/search/cdx"

# def get_snapshots(url, limit=50):
#     params = {
#         "url": url,
#         "output": "json",
#         "fl": "timestamp,original",
#         "filter": "statuscode:200",
#         "collapse": "digest",
#         "limit": limit
#     }
#     for _ in range(3):
#         try:
#             resp = requests.get(WAYBACK_API, params=params, timeout=15)
#             if resp.status_code == 200:
#                 data = resp.json()
#                 if len(data) > 1:
#                     return data[1:]
#                 return []
#         except Exception:
#             time.sleep(1)
#     return []

# def get_earliest_wayback_date(url):

#     def try_variants(u):
#         yield u
#         yield u.replace("https://", "http://")
#         yield u.replace("http://", "https://")
#         yield u.split("?")[0]

#     all_snaps = []

#     for v in try_variants(url):
#         snaps = get_snapshots(v, limit=50)
#         all_snaps.extend(snaps)
#         time.sleep(0.15)

#     if not all_snaps:
#         return None

#     times = [s[0] for s in all_snaps]
#     earliest = min(times)

#     return f"{earliest[4:6]}/{earliest[2:4]}"


# # =============================
# # SCRAPE ONLY MISSING ONES
# # =============================
# results = []

# for idx, row in tqdm(missing_df.iterrows(), total=len(missing_df)):
#     url = row["url"]
#     pid = row["product_id"] if "product_id" in row else idx

#     # Try scraping this URL
#     try:
#         date = get_earliest_wayback_date(url)
#     except Exception as e:
#         print(f"Error scraping {url}: {e}")
#         date = None

#     results.append((row.name, date))  # row.name = original index

#     # (Optional) small pause so archive.org likes you
#     time.sleep(0.2)

# # Convert results into DF
# results_df = pd.DataFrame(results, columns=["index", "new_release_date"])
# results_df.set_index("index", inplace=True)

# # =============================
# # MERGE RESULTS BACK INTO FULL DF
# # =============================
# df.loc[results_df.index, "release_date"] = results_df["new_release_date"]

# # =============================
# # SAVE FINAL OUTPUT
# # =============================
# df.to_csv("merged_full_with_release_dates_UPDATED.csv", index=False)

# print("\n🎉 Finished scraping missing release dates!")
# print(f"Updated file saved as: merged_full_with_release_dates_UPDATED.csv")
# print(f"Remaining missing dates: {df['release_date'].isna().sum()}")
