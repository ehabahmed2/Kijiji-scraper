# Real Stat Kijiji Scraper

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import os
import time
import random
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
real_stat_option = 4
search_url = "https://www.kijiji.ca/"

# Initialize lists to store scraped data
names = []
titles = []
prices = []
phone_numbers = []
descriptions = []
offer_links = []

def setup_driver():
    """Setup Chrome driver with options."""
    options = Options()
    options.headless = True  # Run in headless mode
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    return webdriver.Chrome(options=options)

def open_search_page(driver, search):
    """Open Kijiji and perform a search based on user input."""
    driver.get(search_url)
    wait = WebDriverWait(driver, 10)
    search_tag = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@id='global-header-search-bar-input']")))
    search_tag.send_keys(search)
    search_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='sc-6e4eeff6-0 dXZBeM']")))

    try:
        dropdown_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@id='category-dropdown']")))
        dropdown_button.click()

        dropdown_menu = wait.until(EC.visibility_of_element_located((By.XPATH, "//ul[@id='category-dropdown-menu']")))

        option_xpath = f"//ul[@id='category-dropdown-menu']/li[{real_stat_option}]"
        logging.info(f"Looking for option with XPath: {option_xpath}")
        selected_option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
        selected_option.click()
    except Exception as e:
        logging.error(f"An error occurred while selecting the dropdown: {e}")

    search_button.click()

def reveal_phone_number(driver):
    """Reveal and return the phone number if available."""
    try:
        phone_number_button = driver.find_element(By.XPATH, "//button[contains(@class, 'phoneShowNumberButton')]")
        phone_number_button.click()
        time.sleep(2)  # Wait for the number to be revealed
        revealed_number_element = driver.find_element(By.CSS_SELECTOR, ".phoneShowNumberButton-1507564712")
        phone_number = revealed_number_element.text.strip()
        logging.info(f"Phone number found: {phone_number}")
        return phone_number
    except Exception as e:
        logging.warning(f"No phone number available: {e}")
        return "Not available"

def extract_title(driver):
    """Extract and return the title of the offer."""
    try:
        title_element = driver.find_element(By.XPATH, '//*[@id="vip-body"]/div[2]/div[1]/h1')
        return title_element.text.strip()
    except:
        try:
            title_element = driver.find_element(By.XPATH, '//*[@id="ViewItemPage"]/div[5]/div/div[1]/div/h1')
            return title_element.text.strip()
        except:
            logging.warning("Title not found")
            return None

def extract_price(driver):
    """Extract and return the price of the offer."""
    try:
        price_element = driver.find_element(By.CLASS_NAME, 'priceWrapper-3915768379')
        return price_element.text.strip().replace('\n', ' ')
    except:
        try:
            price_element = driver.find_element(By.XPATH, "//div[@class='priceContainer-1877772231']")
            return price_element.text.strip().replace('\n', ' ')
        except:
            logging.warning("Price not found")
            return None

def extract_seller_name(driver):
    """Extract and return the name of the seller."""
    try:
        seller_element = driver.find_element(By.CLASS_NAME, "link-441721484")
        seller_name = seller_element.text.strip()
        logging.info(f"Seller name found: {seller_name}")
        return seller_name
    except:
        logging.warning("Seller name not found")
        return None

def extract_description(driver):
    """Extract and return the description of the offer."""
    try:
        see_more_buttons = driver.find_elements(By.XPATH, "//button[normalize-space()='Show more']")
        if see_more_buttons:
            see_more_buttons[0].click()
        description_element = driver.find_element(By.XPATH, "//div[@itemprop='description']")
        return description_element.text.strip()
    except:
        logging.warning("Description not found")
        return None

def scrape_page(driver, link_url):
    """Scrape details from a single offer page."""
    try:
        driver.get(link_url)
        offer_links.append(link_url)

        phone_number = reveal_phone_number(driver)
        phone_numbers.append(phone_number)

        title = extract_title(driver)
        titles.append(title if title else "N/A")

        price = extract_price(driver)
        prices.append(price if price else "N/A")

        seller = extract_seller_name(driver)
        names.append(seller if seller else "N/A")

        description = extract_description(driver)
        descriptions.append(description if description else "N/A")

    except Exception as e:
        logging.error(f"An error occurred while processing URL {link_url}: {e}")
        phone_numbers.append("Phone isn't available")

def scrape_pages(driver, num_pages):
    """Scrape multiple pages of offers."""
    page_count = 1
    while page_count <= num_pages:
        logging.info(f"Scraping page {page_count}")
        current_page = driver.current_url

        driver.execute_script("window.open('');")
        logging.info("New tab opened.")
        
        driver.switch_to.window(driver.window_handles[1])
        logging.info("Switched to new tab.")

        driver.get(current_page)
        scrape_page_links(driver)

        driver.close()
        logging.info("Closed the new tab.")

        driver.switch_to.window(driver.window_handles[0])
        logging.info("Switched back to the main tab.")
        page_count += 1

        try:
            pagination_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".sc-70ac4838-0.dMffGH.sc-4c795659-3.garPwt"))
            )
            pagination_btn.click()
            logging.info(f"Moved to the next page: {driver.current_url}")
        except:
            logging.info("No more pages to scrape")
            break

def scrape_page_links(driver):
    """Scrape all offer links on the current page and process them."""
    wait = WebDriverWait(driver, 10)
    try:
        links = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'sc-7c655743-0 ctMqFL')]")))
        links_list = [link.get_attribute("href") for link in links]
        for link_url in links_list:
            scrape_page(driver, link_url)
            time.sleep(random.randint(2, 5))  # Random delay between requests to avoid detection
    except Exception as e:
        logging.error(f"An error occurred while scraping page links: {e}")

def save_to_csv():
    """Save the scraped data to a CSV file."""
    max_length = max(len(names), len(titles), len(prices), len(phone_numbers), len(descriptions), len(offer_links))

    # Pad lists to ensure they are all the same length
    names.extend(["N/A"] * (max_length - len(names)))
    titles.extend(["N/A"] * (max_length - len(titles)))
    prices.extend(["N/A"] * (max_length - len(prices)))
    phone_numbers.extend(["N/A"] * (max_length - len(phone_numbers)))
    descriptions.extend(["N/A"] * (max_length - len(descriptions)))
    offer_links.extend(["N/A"] * (max_length - len(offer_links)))

    df = pd.DataFrame({
        "Name of sellers": names,
        "Offer Titles": titles,
        "Prices": prices,
        "Phone numbers": phone_numbers,
        "Descriptions": descriptions,
        "Links of the offers": offer_links,
    })

    output_dir = r"F:\VS projects\.vscode\scraping\kiji"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    df.to_csv(os.path.join(output_dir, "kijiji_data.csv"), index=False)
    logging.info("CSV file saved successfully")

if __name__ == "__main__":
    driver = setup_driver()

    search = input("What are you looking for? ")
    open_search_page(driver, search)

    page_num = int(input("How many pages you want to scrape? (1 page = 45 results)\n"))
    scrape_pages(driver, page_num)

    driver.quit()

    save_to_csv()

    logging.info("Scraping completed successfully.")
