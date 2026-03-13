# BICEP PDF Scraper

This project is a Python automation tool that scrapes the BICEP website and automatically downloads PDF notices based on specific **date and subject filters**.

The script monitors the notices published on the website and collects relevant PDF documents for further analysis or record keeping.

---

## Features

- Scrapes notices from the BICEP website
- Filters notices based on **date**
- Filters notices based on **subject keywords**
- Automatically downloads matching PDF files
- Organizes downloaded PDFs locally

---

## Project Structure
bicep-pdfs-data-extractor
│
├── src
│ ├── main.py
│ ├── webscrp.py
│ └── biceps_pdf_scraper.py
│
├── README.md
├── requirements.txt
└── .gitignore
---

## Technologies Used

- Python
- Requests
- BeautifulSoup
- Web Scraping
- Automation

---

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/bicep-pdfs-data-extractor.git
pip install -r requirements.txt
python src/main.py
