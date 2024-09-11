import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Function to fetch webpage content
def fetch_webpage(url):
    """Fetch the content of a webpage."""
    response = requests.get(url)
    return BeautifulSoup(response.content, "html.parser")


# Extract audio links from the HTML <ul> element
def extract_audio_links(ul_element):
    """Extract and clean audio links from a <ul> element."""
    audio_links = []
    audios = ul_element.find_all(class_="audio-button")
    for audio in audios:
        audio_element = audio.find("audio")
        if audio_element:
            audio_url = audio_element.get("src")
            trimmed_url = audio_url.split(".mp3")[0] + ".mp3"
            audio_links.append(trimmed_url)
    return audio_links


# Extract quotes from the HTML <ul> element
def clean_quotes(quotes):
    """Clean and extract quotes from a <ul> element."""
    clean_quotes = []
    for quote in quotes:
        if quote.find("audio"):
            clean_quote = quote.text.replace("\u00a0", " ").strip().strip('"')
            if clean_quote:
                clean_quotes.append(clean_quote)
    return clean_quotes


all_quotes = []  # Global list to keep track of existing quotes


# Function to extract quotes and audio links from a <li> element
def extract_quotes_and_audio_links(li):
    """Extract quotes and audio links from a <li> element."""
    data = {}
    audio_element = li.find("audio")
    if audio_element is not None:
        audio_url = audio_element.get("src")
        trimmed_url = audio_url.split(".mp3")[0] + ".mp3"
    else:
        trimmed_url = None

    quote = None
    for text in li.contents:
        currentText = text.text.replace('"', "").strip()
        if currentText.startswith("https") or currentText.startswith("("):
            continue
        quote = currentText

    quote = quote.replace('"', "")

    if quote and trimmed_url:
        if quote not in all_quotes:
            all_quotes.append(quote)
            data["audio_links"] = [trimmed_url]
            data["quotes"] = [quote]

    return data


# Scrape data from a single URL and return a dictionary of audio links and quotes
def scrape_data_from_url(url):
    """Scrape data from a single URL and return it as a dictionary."""
    soup = fetch_webpage(
        url
    )  # Assuming fetch_webpage fetches and parses the webpage with BeautifulSoup
    uls = soup.find_all("ul")
    filtered_uls = [ul for ul in uls if ul.find("audio")]

    url_data = []
    for ul in filtered_uls:
        lis = ul.find_all("li")
        filtered_lis = [li for li in lis if li.find("audio")]
        for li in filtered_lis:
            section_data = extract_quotes_and_audio_links(li)
            # Check if both 'audio_links' and 'quotes' are present in the section_data dictionary
            if "audio_links" in section_data and "quotes" in section_data:
                url_data.append(section_data)

    return url_data


# Generate a sheet name based on the URL
def generate_sheetName(url):
    """Generate a sheet name based on the URL with a '_voice_lines' suffix."""
    parts = url.strip("/").split("/")
    name = parts[-2]  # Get the last meaningful part of the URL
    return name


# Prepare data for batch update into Google Sheets
def prepare_data_for_update(data):
    """Prepare data in a format suitable for batch updating into Google Sheets."""
    headers = ["audio_links", "quotes"]
    rows = []

    for item in data:
        audio_links = item["audio_links"]
        quotes = item["quotes"]
        max_length = max(len(audio_links), len(quotes))
        for i in range(max_length):
            row = [
                audio_links[i] if i < len(audio_links) else "",
                quotes[i] if i < len(quotes) else "",
            ]
            rows.append(row)

    return [headers] + rows


# Batch update data to the Google Sheets
def batch_update_data(worksheet, data):
    """Batch update the prepared data into the specified Google Sheets worksheet."""
    num_rows = len(data)
    cell_range = f"A1:B{num_rows}"
    worksheet.update(data, range_name=cell_range)


# Initialize Google Sheets API credentials
def init_google_sheets():
    """Initialize the Google Sheets API client."""
    credentials_data = {
        "type": "service_account",
        "project_id": "valorant-wiki-435215",
        "private_key_id": "8b3cbea9d22e8253d4397a3e547fce88d28216bf",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQClDQ++7qQEo3HT\n5i5j3D/i81abznV9c0+66RYntMFNfDy/+AXXt+NpHnq20e7+EtHMYVfMR+ALT4Iv\n1dnmpHmkBQpn15Biejz+cavhZCApGi7YZ3gFxchjyt1d+QAjTUWa9EbqtHiyZfyr\nlDUr4AKdsoABipe8qPFmLXL3UbxrI10QKWipIeh3HjPSMzd+mUCAz6rmG66+sYZj\n2faiBCQ92jS/+69pNDTg9WWEBSInBfK3dX/05IHEY/qrxZ60z9R3/njE5Pk2gOun\np9FEP7I5LWUkrfSsyGNxhEmTA4ScTfP48MxmN6rxbyk21dFs5z9OU4mg07aO7U9A\n7Kjxm/D5AgMBAAECggEAM3sO+b1ioGXAl9j4iEJHFQlUbtWnVOFWMZUJSYo6Lup8\n4l3AqMfdIUkV+pchhdMl6CtGoNucWLrMfxIjXKrZnBzMYZZdnTHGe5DGDU/XLirS\nCMLBL3/A4MuCX5DOh7RO7SWbRxLSgMaJ2JSqPwyolDp8bb6mVHyXiwjLDrRKYloN\ndXQdNvlGCk9n7FhPibQQGZXJtExeu9C9SxhEYJmkcHzHsC8/RM+cbKYp5n9a/kq4\n7mVvvlzAZsJuSnSYOkKvOF40nN7xOHiLQSmRYiF6G2XZ8oIXN4/PZYVRrnkBokax\ndOJx7uauomQ0sthC/uxqgMFxwuy60qk5SEgpAYUVDwKBgQDaB9qec6HxS8KtXZ74\n/jgfIQ8dgcstCu/my3dIKAsCFDsfjg6q1MyRnR0UtLrAvzw9SokbeWbT15xuUZo9\nBBiWr3IWQJcVmk8XuO1FCkdfic5lDoQI/VnYRkcZ0KPRKsAONZmu1VRjRFpv46YP\nPiZsINwmBC41RIaFkW6N/IsIFwKBgQDBy0rK8l+yy8jnJYI+Nph/2YuGJVn3wMZf\n7xQ1mdOZkqwi6j3tRDMF/bl9BAyNR6GK+1FX0T1chyv8huriEI8/ZfUtAk8nICoX\nfPrGMG3HP95F1PpttYSV6PL+m2K8kD03ypFO9FktGafjDxvsWNoqzxbwVzDoYsP2\ntSQ1LE5pbwKBgQCcDvUXZ1LpwL12k8VfGa+X8HS+PRHtip+OheI6HpdKhKqQ+oBb\nHHfUXi3bjUUDA56djEU5Chtk1DZe7D/HHrBu4uN5NAAwcUPdifsi6KmPo7a8tLgj\nKxxs5lisDJ/E7qGLSihXcNC3QMyuu7Y3wNeFm7uX5nQgooza++6y6KmnPwKBgQCT\nAhcrmu8zn9k4V0DU1u+aVLm9uknkYo1ZqvBGtPlKj3QbTFxLx6d5DP8Psemfps4J\nsxoCpwyIS1X3y5UUhoFUE5EIYq8OvBySEtHdVFGCi5WenbCXVtJMMhlbQR6Gcliu\nIPFX1o5rYwHzgbup78EYJl59VXcZYgrL9J+R4plc6wKBgCvH9cF+69fGqvWXcSIS\nYif6gNf1nqyDfwJ9P6tx5KFzF3tRjC9aa9lWmDmCfnqdgCszM/24YOw9ptGeNu7y\nQdtnhIcrFbuArl3ez8wWbQ3HuOwbD4IFM361JaZ6whYqgagbQGfw3JK5tjJc5PfP\nGF2gdMu84xlDu+PoM/40R1vi\n-----END PRIVATE KEY-----\n",
        "client_email": "valorant-wiki@valorant-wiki-435215.iam.gserviceaccount.com",
        "client_id": "108509723060752063426",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/valorant-wiki%40valorant-wiki-435215.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com",
    }
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_data, scope
    )
    client = gspread.authorize(credentials)
    return client


# Main function to scrape URLs and save data to Google Sheets
def main():
    # Replace with your own URLs
    urls = [
        "https://valorant.fandom.com/wiki/Brimstone/Quotes",
        "https://valorant.fandom.com/wiki/Viper/Quotes",
        "https://valorant.fandom.com/wiki/Omen/Quotes",
        "https://valorant.fandom.com/wiki/Killjoy/Quotes",
        "https://valorant.fandom.com/wiki/Cypher/Quotes",
        "https://valorant.fandom.com/wiki/Sova/Quotes",
        "https://valorant.fandom.com/wiki/Sage/Quotes",
        "https://valorant.fandom.com/wiki/Phoenix/Quotes",
        "https://valorant.fandom.com/wiki/Jett/Quotes",
        "https://valorant.fandom.com/wiki/Reyna/Quotes",
        "https://valorant.fandom.com/wiki/Raze/Quotes",
        "https://valorant.fandom.com/wiki/Breach/Quotes",
        "https://valorant.fandom.com/wiki/Skye/Quotes",
        "https://valorant.fandom.com/wiki/Yoru/Quotes",
        "https://valorant.fandom.com/wiki/Astra/Quotes",
        "https://valorant.fandom.com/wiki/KAYO/Quotes",
        "https://valorant.fandom.com/wiki/Chamber/Quotes",
        "https://valorant.fandom.com/wiki/Neon/Quotes",
        "https://valorant.fandom.com/wiki/Fade/Quotes",
        "https://valorant.fandom.com/wiki/Harbor/Quotes",
        "https://valorant.fandom.com/wiki/Gekko/Quotes",
        "https://valorant.fandom.com/wiki/Deadlock/Quotes",
        "https://valorant.fandom.com/wiki/Iso/Quotes",
        "https://valorant.fandom.com/wiki/Clove/Quotes",
        "https://valorant.fandom.com/wiki/Vyse/Quotes",
    ]

    # Initialize Google Sheets client
    google_client = init_google_sheets()
    spreadsheet_name = "valo_wiki"
    for url in urls:
        # Scrape data from the URL
        scraped_data = scrape_data_from_url(url)

        # Generate sheet name and add to list
        sheet_name = generate_sheetName(url)

        # Open or create a new Google Sheet and worksheet for the scraped data
        try:
            spreadsheet = google_client.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            spreadsheet = google_client.create(spreadsheet_name)

        # Access the worksheet or create a new one
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=2)

        # Clear the existing sheet
        worksheet.clear()

        # Prepare data for batch update and update the worksheet
        data_to_update = prepare_data_for_update(scraped_data)
        batch_update_data(worksheet, data_to_update)


# Run the main function
if __name__ == "__main__":
    main()
