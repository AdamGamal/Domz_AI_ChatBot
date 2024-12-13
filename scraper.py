import requests
from bs4 import BeautifulSoup
import csv
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

# Define CSS selectors for various product components
PRODUCT_LINK_SELECTORS = ['.product-block__image__link', '.grid-product__link', '.product-card__link']
NAME_SELECTORS = ['.product-title', '.product__title', '.product-single__title', '.product-card__name']
PRICE_SELECTORS = ['.money', '.price', '.product__price', '.product-card__price']
DESCRIPTION_SELECTORS = ['.product-description', '.product__description', '.product-single__description']
COLOR_SELECTOR = "div.swatch__element[data-value], .color-swatch"
SIZE_SELECTOR = "select[data-single-option-selector] option"
STOCK_STATUS_SELECTOR = "span[data-add-to-cart-text]"  # Selector for stock status


visited_urls = set()  # Track visited URLs to avoid duplication


def get_first_matching_element(soup_element, selectors, attribute=None):
    """Retrieve the first matching element based on a list of CSS selectors."""
    for selector in selectors:
        element = soup_element.select_one(selector)
        if element:
            return element[attribute].strip() if attribute else element.get_text(strip=True)
    return "No data available"


def get_all_matching_elements(soup, selector, attribute=None):
    """Retrieve all matching elements based on a CSS selector."""
    elements = soup.select(selector)
    return [element[attribute].strip() if attribute else element.get_text(strip=True) for element in elements if element]


def scrape_product_data(url):
    """Scrape product details from a product page."""
    if url in visited_urls:
        return None
    visited_urls.add(url)
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser') if response.status_code == 200 else None
        if not soup:
            print(f"Failed to load page: {url}")
            return None

        # Stock status logic
        stock_status_element = soup.select_one(STOCK_STATUS_SELECTOR)
        stock_status = "Unknown"
        if stock_status_element:
            stock_text = stock_status_element.get_text(strip=True)
            if "Add to Cart" in stock_text:
                stock_status = "In Stock"
            elif "Sold Out" in stock_text:
                stock_status = "Out of Stock"

        product = {
            "name": get_first_matching_element(soup, NAME_SELECTORS),
            "price": get_first_matching_element(soup, PRICE_SELECTORS),
            "description": get_first_matching_element(soup, DESCRIPTION_SELECTORS),
            "colors": ", ".join(get_all_matching_elements(soup, COLOR_SELECTOR, attribute="data-value")),
            "sizes": ", ".join(get_all_matching_elements(soup, SIZE_SELECTOR)),
            "stock_status": stock_status,
            "url": url,
            

        }
        return product
    except Exception as e:
        print(f"Error scraping product page {url}: {e}")
        return None


def scrape_collection_page(collection_url):
    """Scrape product links from a collection page."""
    try:
        response = requests.get(collection_url)
        soup = BeautifulSoup(response.text, 'html.parser') if response.status_code == 200 else None
        return [collection_url.split('/collections')[0] + a['href'] for a in soup.select(', '.join(PRODUCT_LINK_SELECTORS)) if 'href' in a.attrs] if soup else []
    except Exception as e:
        print(f"Error scraping collection page {collection_url}: {e}")
        return []


def scrape_all_collections(base_url):
    """Scrape all products from all collections."""
    print("Scraping collections...")
    try:
        response = requests.get(base_url)
        soup = BeautifulSoup(response.text, 'html.parser') if response.status_code == 200 else None
        collection_urls = [base_url.rstrip("/") + element['href'] for element in soup.select('a[href^="/collections/"]') if 'href' in element.attrs] if soup else []
        all_product_links = set()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(scrape_collection_page, url) for url in list(set(collection_urls))]
            for future in futures:
                all_product_links.update(future.result())
        all_products = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(scrape_product_data, url) for url in all_product_links]
            for future in futures:
                product = future.result()
                if product:
                    all_products.append(product)
        return all_products
    except Exception as e:
        print(f"Error scraping collections: {e}")
        return []


def export_to_csv(products, filename="scraper/products.csv"):
    """Export product data to a CSV file."""
    if not products:
        print("No products to export.")
        return

    with open(filename, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "price", "description", "colors", "sizes", "stock_status", "url"])
        writer.writeheader()
        for product in products:
            writer.writerow({
                "name": product["name"],
                "price": product["price"],
                "description": product["description"],
                "colors": product["colors"],
                "sizes": product["sizes"],
                "stock_status": product["stock_status"],
                "url": product["url"],
                
            })
    print(f"Data exported to {filename}")


if __name__ == "__main__":
    base_url = input("Enter the base URL of the e-commerce website: ")
    products = scrape_all_collections(base_url)
    export_to_csv(products)
