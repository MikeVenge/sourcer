import json
import csv
import os

def convert_json_to_csv(json_file_path, csv_file_path):
    try:
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        if not data:
            print("JSON file is empty.")
            return

        # Assuming data is a list of dictionaries
        if not isinstance(data, list):
            print("JSON data is not a list.")
            return

        if len(data) == 0:
             print("JSON list is empty.")
             return

        # Extract headers from the first dictionary
        headers = list(data[0].keys())

        with open(csv_file_path, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"Successfully converted {json_file_path} to {csv_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    json_path = '/Users/michaelkim/code/sourcer/examples/output/nvda_trades_sample.json'
    csv_path = '/Users/michaelkim/code/sourcer/examples/output/nvda_trades_sample.csv'
    convert_json_to_csv(json_path, csv_path)
