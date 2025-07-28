
import time
from summarize import bulk_summarize_and_process_silent
from display import console

# Settings
emails_per_batch = 5
sleep_between_batches = 30  # seconds
max_batches = 10  # or set to None to run indefinitely

def run_batches():
    batch_count = 0
    while True:
        console.print(f"\n📦 Running batch {batch_count + 1}...")
        bulk_summarize_and_process_silent(num_emails=emails_per_batch, confirm_all=True)

        batch_count += 1
        if max_batches and batch_count >= max_batches:
            console.print("✅ Reached maximum batch count. Exiting.")
            break

        console.print(f"⏳ Sleeping for {sleep_between_batches} seconds...")
        time.sleep(sleep_between_batches)

if __name__ == "__main__":
    run_batches()
