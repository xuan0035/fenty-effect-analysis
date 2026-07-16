import pandas as pd

df = pd.read_csv("data/02-processed/merged_full_with_release_dates.csv").copy()

done_df = pd.read_csv("data/02-processed/release_date_checkpoint.csv")

done_df["new_release_date"] = done_df["new_release_date"].astype(str).str.strip()
done_df = done_df[done_df["new_release_date"] != ""] 

for _, row in done_df.iterrows():
    idx = int(row["index"])
    df.loc[idx, "approx_release_date"] = row["new_release_date"]

OUTPUT_FILE = "data/02-processed/merged_full_with_release_dates_UPDATED.csv"
df.to_csv(OUTPUT_FILE, index=False)

print("Merged partial scraped dates into full dataset and saved to:", OUTPUT_FILE)
