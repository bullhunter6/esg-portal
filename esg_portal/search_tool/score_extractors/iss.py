import requests
import json

def company_id(company_name):
    url = "https://marketingwidget.iss-corporate.com/api/searchCompany"
    payload = json.dumps({
        "searchTerm": company_name
    })
    headers = {
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.9',
      'Connection': 'keep-alive',
      'Content-Type': 'application/json',
      'Cookie': 'OptanonAlertBoxClosed=2024-06-12T08:26:11.208Z; OptanonConsent=isGpcEnabled=0&datestamp=Tue+Nov+19+2024+18%3A48%3A20+GMT%2B0400+(Gulf+Standard+Time)&version=202405.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0004%3A1&geolocation=%3B&AwaitingReconsent=false; ESG_SESSION_ID=3c527b5b02204d9f8d6d654c5f8791a72586df179aef402ab9d138934a49defbadc4799627894785b91dc825b74b3050',
      'Origin': 'https://marketingwidget.iss-corporate.com',
      'Referer': 'https://marketingwidget.iss-corporate.com/home',
      'Sec-Fetch-Dest': 'empty',
      'Sec-Fetch-Mode': 'cors',
      'Sec-Fetch-Site': 'same-origin',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
      'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"'
    }

    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            company_data = {}
            if isinstance(data, list) and len(data) > 0:
                for company in data:
                    company_data['entity_id'] = company.get("entityId", "-")
                    company_data['entity_name'] = company.get("entityName", "-")
                    company_data['ticker'] = company.get("ticker", "-")
                    company_data['country'] = company.get("Country", "-")
                    company_data['row_num'] = company.get("RowNum", "-")
                    company_data['isin'] = company.get("isin", "-")
                    company_data['source'] = "ISS"
                    
                    return company_data
            else:
                return "No company data found in the response."
        except json.JSONDecodeError:
            return "Failed to parse JSON response."
    else:
        return f"Failed to fetch data. HTTP Status Code: {response.status_code}"

def company_data(company_id):
    url = f"https://marketingwidget.iss-corporate.com/api/getCompanyDetails/{company_id}"
    payload = json.dumps({})
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            company_data = data.get("companyData", [])
            
            if company_data:
                return company_data
            else:
                return "No company data found."
        except json.JSONDecodeError:
            return "Failed to parse JSON response."
    else:
        return f"Failed to fetch data. HTTP Status Code: {response.status_code}"

def iss_score(company_name):
    company = company_id(company_name)
    if isinstance(company, dict):
        company_details = company_data(company.get("entity_id"))
        if company_details:
            # Make sure it's a list as expected
            if isinstance(company_details, list):
                # Add source information to each item
                for item in company_details:
                    if isinstance(item, dict):
                        item["source"] = "ISS"
                return company_details
            elif isinstance(company_details, dict):
                company_details["source"] = "ISS"
                # Wrap in a list to maintain expected format
                return [company_details]
            else:
                return [{"error": "Unexpected data format from ISS", "source": "ISS", "oekomRating": "-"}]
    return [{"error": "Company not found in ISS database", "source": "ISS", "oekomRating": "-"}]