import requests
from bs4 import BeautifulSoup
import csv
import re

# URL
url = "https://citysquares.com/search?utf8=%E2%9C%93&search%5Bterm%5D=medical+clinics+&search%5Blocation%5D=Texas+City-league+City%2C+TX"

# Download the page
response = requests.get(url)
response.raise_for_status()
soup = BeautifulSoup(response.text, 'html.parser')

# Extract all text blocks (lines) — this is broad but works for your simple layout
all_text = soup.get_text(separator="\n")
lines = [line.strip() for line in all_text.split("\n") if line.strip()]

# Regex pattern for US phone numbers like (409) 965-0077
phone_pattern = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")

# Group lines by logic: name → address → phone
data = []
temp = {"Name": "", "Address": "", "Phone": ""}

for line in lines:
    if phone_pattern.search(line):
        temp["Phone"] = line
        data.append(temp.copy())
        temp = {"Name": "", "Address": "", "Phone": ""}
    else:
        if not temp["Name"]:
            temp["Name"] = line
        elif not temp["Address"]:
            temp["Address"] = line
        else:
            # If address spans multiple lines
            temp["Address"] += ", " + line

# Save to CSV
with open("citysquares_clean.csv", mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Name", "Address", "Phone"])
    writer.writeheader()
    for row in data:
        writer.writerow(row)

print("✅ Done! Check 'citysquares_clean.csv'")
