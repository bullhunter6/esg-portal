import requests
from bs4 import BeautifulSoup
import json
import re

def normalize_text(text):
    """
    Normalize text by:
    - Removing common terms like 'Inc.', 'Ltd.'
    - Replacing dashes with spaces
    - Removing special characters
    - Converting to lowercase
    """
    common_terms = {"company", "corporation", "inc", "limited", "ltd", "co", "corp", "berhad", "bhd", "public"}
    text = text.lower()
    text = re.sub(r"[-]", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    tokens = text.split()
    return " ".join(token for token in tokens if token not in common_terms)

def calculate_match_score(input_text, title):
    """
    Calculate a match score based on:
    - Exact match priority
    - Substring inclusion
    - Token overlap
    """
    input_tokens = set(input_text.split())
    title_tokens = set(title.split())
    if input_text == title:
        return 1.0
    if input_text in title or title in input_text:
        substring_score = 0.8
    else:
        substring_score = 0.0
    token_overlap = len(input_tokens & title_tokens) / max(len(input_tokens), len(title_tokens))
    return substring_score + (0.7 * token_overlap)

def fetch_issuerid(company_name):
    """
    Fetch company details from the API and find the closest match using enhanced scoring logic.
    
    :param company_name: The company name entered by the user.
    :return: A dictionary containing the matched company's details or None if no match is found.
    """
    url = f"https://www.msci.com/our-solutions/esg-investing/esg-ratings-climate-search-tool?p_p_id=esgratingsprofile&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=searchEsgRatingsProfiles&p_p_cacheability=cacheLevelPage&_esgratingsprofile_keywords={company_name}"
    
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        try:
            data = response.json()
            clean_user_input = normalize_text(company_name)
            
            best_match = None
            highest_score = 0.0
            
            for company in data:
                title = company.get("title", "")
                clean_title = normalize_text(title)
                match_score = calculate_match_score(clean_user_input, clean_title)
                if match_score > highest_score:
                    highest_score = match_score
                    best_match = company
            if best_match and highest_score > 0.5:
                return {
                    "encodedTitle": best_match.get("encodedTitle", "N/A"),
                    "title": best_match.get("title", "N/A"),
                    "url": best_match.get("url", "N/A")
                }
            else:
                return None
        except json.JSONDecodeError:
            return None
    else:
        return None

def extract_esg_score(class_name):
    if "esg-rating-circle-" in class_name:
        return class_name.split("esg-rating-circle-")[-1].upper()
    return "N/A"

def company_details(issuer_id, encoded_title):
    if not issuer_id or not encoded_title:
        return None

    url = f"https://www.msci.com/our-solutions/esg-investing/esg-ratings-climate-search-tool?p_p_id=esgratingsprofile&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=showEsgRatingsProfile&p_p_cacheability=cacheLevelPage&_esgratingsprofile_issuerId={issuer_id}"

    headers = {
      'Accept': '*/*',
      'Accept-Language': 'en-US,en;q=0.9',
      'Connection': 'keep-alive',
      'Cookie': 'msci-appgw-affinityCORS=58d050eff25537bf052edeafd1a28ae7; msci-appgw-affinity=58d050eff25537bf052edeafd1a28ae7; COOKIE_SUPPORT=true; EVICT_LIFERAY_LANGUAGE_ID=en_US; OptanonAlertBoxClosed=2024-06-12T08:32:08.044Z; msci_esg_issuers=04891f719524d12c50243574e59a1a04g1303ead4415bbb571891cb2e49e5a0e9g9979af514f01e104a27d59861e18b7f6g9053bb14821d3c6da8319dbf5a065400; INGRESSCOOKIE=5fc43646bdf5c57ea0908c4896af3ce5|966b3c2cb4f050ee70514f516ad4417d; MSCIJSESSIONID=4D38EC8FF22C9438724ED109F00C838A.jvmRoute-azure-liferay-0; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Nov+20+2024+12%3A51%3A10+GMT%2B0400+(Gulf+Standard+Time)&version=202307.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=cef433bc-597f-4785-be84-531ebe6e9e0b&interactionCount=2&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false&geolocation=AE%3BDU; LFR_SESSION_STATE_10163=1732099821269; COOKIE_SUPPORT=true; EVICT_LIFERAY_LANGUAGE_ID=en_US',
      'Referer': f'https://www.msci.com/our-solutions/esg-investing/esg-ratings-climate-search-tool/issuer/{encoded_title}/{issuer_id}',
      'Sec-Fetch-Dest': 'empty',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      'X-Requested-With': 'XMLHttpRequest',
      'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"'
    }

    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        company_name = soup.select_one('.header-company-title')
        company_ticker = soup.select_one('.header-company-ticker')
        industry = soup.select_one('.header-esg-industry')
        country = soup.select_one('.header-country')
        esg_rating_class = soup.select_one('.ratingdata-company-rating')

        company_name = company_name.text.strip() if company_name else "N/A"
        company_ticker = company_ticker.text.strip("()\n\t ") if company_ticker else "N/A"
        industry = industry.text.replace("Industry:", "").strip() if industry else "N/A"
        country = country.text.replace("Country/Region:", "").strip() if country else "N/A"
        esg_rating = extract_esg_score(esg_rating_class.get("class")[-1]) if esg_rating_class else "N/A"

        return {
            'Company Name': company_name,
            'Ticker': company_ticker,
            'Industry': industry,
            'Country/Region': country,
            'ESG Rating': esg_rating,
            'source': "MSCI"
        }
    return None

def msci_score(company_name):
    company_data = fetch_issuerid(company_name)
    if company_data:
        issuer_id = company_data.get('url')
        encoded_title = company_data.get('encodedTitle')
        details = company_details(issuer_id, encoded_title)
        if details:
            return details
        else:
            return {"ESG Rating": "-", "source": "MSCI"}
    else:
        return {"ESG Rating": "-", "source": "MSCI"}

