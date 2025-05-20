import requests
import json

def fetch_companies():
    """
    Fetch the list of companies from the API and return it as a list of dictionaries.
    """
    url = "https://www.lseg.com/bin/esg/esgsearchsuggestions"
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'Cookie': 'encaddr=w2XdZPyUQlBQjV4bjx0HCV8Vv1L+j7XjzTBAIg==; AWSALB=ywTppvgpwaamhrXirEWm3c2yDBT2Im++Ff1zheKsABZZ8lvrOx0h6PRFBy2BLX4CgzR9C51m/LNv8ew6JRRlIhs0AswsrFyuHo6vmrDkymV5nAAAw9QMBn2P/8NY; AWSALBCORS=ywTppvgpwaamhrXirEWm3c2yDBT2Im++Ff1zheKsABZZ8lvrOx0h6PRFBy2BLX4CgzR9C51m/LNv8ew6JRRlIhs0AswsrFyuHo6vmrDkymV5nAAAw9QMBn2P/8NY'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch data from the API")
        return []

def clean_tokens(name):
    """
    Remove common generic tokens from the company name.
    """
    common_tokens = {"s.a.", "ltd", "inc", "co", "company", "corporation", "limited", "plc", "corp"}
    tokens = name.lower().split()
    return [token for token in tokens if token not in common_tokens]

def find_best_match(user_input, companies):
    """
    Find the single best match for the user's input using enhanced partial matching logic.

    :param user_input: The full or partial company name entered by the user.
    :param companies: The list of company data (name and ric code).
    :return: The best-matched company name or None if no suitable match is found.
    """
    user_input_lower = user_input.lower()
    user_tokens = clean_tokens(user_input_lower)
    best_match = None
    highest_score = 0

    for company in companies:
        company_name = company['companyName']
        company_ric_code = company['ricCode']
        company_name_lower = company_name.lower()
        company_tokens = clean_tokens(company_name_lower)

        if user_input_lower == company_name_lower:
            return company_name, company_ric_code
        
        common_tokens = set(user_tokens) & set(company_tokens)
        token_overlap_score = len(common_tokens) / len(user_tokens)
        if token_overlap_score >= 0.8:
            length_similarity = 1 - abs(len(user_input_lower) - len(company_name_lower)) / max(len(user_input_lower), len(company_name_lower))
            score = (token_overlap_score * 0.7) + (length_similarity * 0.3)
            if score > highest_score:
                highest_score = score
                best_match = company_name
                best_ric_code = company_ric_code
    if highest_score < 0.6:
        return None

    return best_match, best_ric_code

def company_details(ric_code):
    """
    Fetch detailed company information using the ricCode.
    """
    url = f"https://www.lseg.com/bin/esg/esgsearchresult?ricCode={ric_code}"

    headers = {
      'accept': '*/*',
      'accept-language': 'en-US,en;q=0.9',
      'cookie': 'tr_ewp_tracking_params={}; sourceSystem=marketing; at_check=true; OptanonAlertBoxClosed=2024-06-11T08:54:40.185Z; AMCVS_3E1F57795B977DEB0A495EEA%40AdobeOrg=1; _ga=GA1.1.1426948850.1719291896; s_ips=945; s_cc=true; s_tp=7886; s_ppv=esg-scores%253Adata%253A%253Aglobal%253Aen%2C12%2C12%2C945%2C1%2C8; s_plt=4.01; s_pltp=esg-scores:data::global:en; _ga_PVBWSDTKTC=GS1.1.1719298169.2.0.1719298169.0.0.0; redirectUrl=/en/data-analytics/sustainable-finance/esg-scores; AMCV_3E1F57795B977DEB0A495EEA%40AdobeOrg=179643557%7CMCMID%7C36627003661935848164365977478234114574%7CvVersion%7C5.5.0%7CMCIDTS%7C20048%7CMCOPTOUT-1732091423s%7CNONE%7CMCAAMLH-1719896696%7C6%7CMCAAMB-1732084222%7Cj8Odv6LonN4r3an7LhD3WZrU1bUpAkFkkiY1ncBR96t2PTI; mbox=PC#a7f2484c797d43a1878e83d3a4a47216.37_0#1795329026|session#c121e41df6f4421e9baf4f3e70435034#1732086086; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Nov+20+2024+10%3A30%3A26+GMT%2B0400+(Gulf+Standard+Time)&version=202406.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=6ca724ff-84fc-4b2b-935f-e75486cc2471&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&intType=1&geolocation=AE%3BDU&AwaitingReconsent=false; AWSALB=H/fRAxMEB6mz0EdqP8EcPJ9GX7PBlVhXVNonkEqruGp9ehcUT1AC6k2ruZCoV5otcpvhKP+djGaSPuIK47aSfHjk7cbi1hBt3WcqRqUxnR6ixa4osBni7QeXa/ss; AWSALBCORS=H/fRAxMEB6mz0EdqP8EcPJ9GX7PBlVhXVNonkEqruGp9ehcUT1AC6k2ruZCoV5otcpvhKP+djGaSPuIK47aSfHjk7cbi1hBt3WcqRqUxnR6ixa4osBni7QeXa/ss; encaddr=w2XdZPyUQlBQjV4bjx0HCV8Vv1L+j7XjzTBAIg==; AWSALB=sXXGed1NemCL7fXF65lHN4usP7kMvW2ED2yWbU1J93aB0FVembFA7cJ9U9AlS4clhmz466WgHg/EaRmb3IQRP0DNS9CqEOFkA3Nlhwcuz3uWP8/68J6/hAZLkRl7; AWSALBCORS=sXXGed1NemCL7fXF65lHN4usP7kMvW2ED2yWbU1J93aB0FVembFA7cJ9U9AlS4clhmz466WgHg/EaRmb3IQRP0DNS9CqEOFkA3Nlhwcuz3uWP8/68J6/hAZLkRl7',
      'priority': 'u=1, i',
      'referer': 'https://www.lseg.com/en/data-analytics/sustainable-finance/esg-scores?esg=ACWA+Power+Co',
      'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }


    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        try:
            data = response.json()
            company_details = {}
            industry_comparison = data.get("industryComparison", {})
            company_details["Industry Type"] = industry_comparison.get("industryType", "N/A")
            company_details["Score Year"] = industry_comparison.get("scoreYear", "N/A")
            company_details["Rank"] = f"{industry_comparison.get('rank', 'N/A')} out of {industry_comparison.get('totalIndustries', 'N/A')}"
            esg_scores = data.get("esgScore", {})
            #company_details["url"] = url
            for key, value in esg_scores.items():
                company_details[key] = value.get("score", "N/A")
            return company_details

        except json.JSONDecodeError:
            print("Failed to parse JSON response.")
    else:
        print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")

def lseg_score(company_name):
    companies_data = fetch_companies()
    
    if companies_data:
        result = find_best_match(company_name, companies_data)

        if result:
            best_match, ric_code = result
            company_data = {
                "Company Name": best_match,
                "Ric Code" : ric_code,
                "source": "LSEG"
            }
            company_data.update(company_details(ric_code))
            return company_data
        else:
            return {"error": "No match found for company in LSEG database."}
    else:
        return {"error": "Failed to fetch company data from LSEG."}
