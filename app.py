import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import os
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import chromedriver_autoinstaller
from urllib.parse import urljoin

# Functions for scraping emails and finding contact pages (unchanged from your original code)
def scrape_emails_with_selenium(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        page_text = soup.get_text()
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails_from_text = re.findall(email_pattern, page_text)

        emails_from_mailto = [
            tag['href'].replace('mailto:', '').strip()
            for tag in soup.find_all('a', href=True)
            if tag['href'].startswith('mailto:')
        ]

        emails = list(set(emails_from_text + emails_from_mailto))
        return emails
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def find_contact_pages_with_selenium(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        contact_keywords = ['contact', 'contact-us', 'about', 'about-us']

        found_pages = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if any(keyword in href for keyword in contact_keywords):
                found_pages.append(urljoin(url, link['href']))

        return list(set(found_pages))
    except Exception as e:
        print(f"Error finding contact pages for {url}: {e}")
        return []

def process_csv_with_selenium(driver, csv_file):
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
        return None

    if 'Website' not in df.columns:
        st.error("The CSV file does not have a 'Website' column.")
        return None

    df['Extracted Emails'] = ''
    
    for index, row in df.iterrows():
        url = row['Website']
        st.write(f"Processing {url}...")
        emails = scrape_emails_with_selenium(driver, url)

        if not emails:
            contact_pages = find_contact_pages_with_selenium(driver, url)
            for page in contact_pages:
                emails += scrape_emails_with_selenium(driver, page)
                emails = list(set(emails))

        email_list = ', '.join(emails)
        df.at[index, 'Extracted Emails'] = email_list

    return df

# Streamlit UI
st.title("Email Scraper with Selenium")
st.write("Upload a CSV file with a column 'Website' to extract emails from web pages.")

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    # Set up Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    chromedriver_autoinstaller.install()

    driver = webdriver.Chrome(options=chrome_options)

    # Process the uploaded CSV
    with st.spinner('Processing CSV...'):
        result_df = process_csv_with_selenium(driver, uploaded_file)

    driver.quit()

    if result_df is not None:
        # Show the result and allow the user to download it
        st.write("Extracted emails:")
        st.dataframe(result_df)

        # Allow user to download the updated CSV
        output_csv = f"extracted_emails_{uploaded_file.name}"
        result_df.to_csv(output_csv, index=False)
        st.download_button("Download Updated CSV", data=open(output_csv, 'rb'), file_name=output_csv)

