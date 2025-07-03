import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

def sustainalytics_company_link(company_name):
    try:
        query = urlencode({"filter": company_name})

        url = "https://www.sustainalytics.com/sustapi/companyratings/GetCompanyDropdown"
        payload = f"industry=&rating=&{query}&page=1&pageSize=10&resourcePackage=Sustainalytics"
        headers = {
          'accept': '*/*',
          'accept-language': 'en-US,en;q=0.9',
          'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'cookie': 'sf-data-intell-subject=1727087948762-4ef5e27a-d25e-4637-ac8e-787512e68589; sf-prs-ss=638626847488270000; sf-prs-lu=https://www.sustainalytics.com/; messagesUtk=9e77a6dbc2a84b39b0adfd1d8f6d7d7d; _cfuvid=xvaq7D5q5aJrTqKRCgQUTqFKb_JD920h1g2_BjtlqrY-1731930389083-0.0.1.1-604800000; sf_abtests=46ad2ba7-8713-472b-bc2e-2402ac50779f,6d9de14d-d722-452d-99af-702de9dbebc1; sf-ins-ssid=1732024410056-7830023b-ebb5-49dd-8217-e081ab29d6b7; sf-ins-pv-id=33777a3e-8928-477e-a1a7-1892e62dcd45',
          'origin': 'https://www.sustainalytics.com',
          'priority': 'u=1, i',
          'referer': 'https://www.sustainalytics.com/esg-ratings',
          'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'sec-fetch-dest': 'empty',
          'sec-fetch-mode': 'cors',
          'sec-fetch-site': 'same-origin',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
          'x-requested-with': 'XMLHttpRequest'
        }

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            companies = soup.find_all('div', class_='list-group-item')
            base_url = "https://www.sustainalytics.com/esg-rating"
            company_details = []
            for company in companies:
                link_tag = company.find('a', class_='search-link')
                company_name_tag = company.find('div', class_='companyName')
                ticker_tag = company.find('span', class_='companyTicker')
                relative_link = link_tag['data-href'] if link_tag else None
                full_link = f"{base_url}{relative_link}" if relative_link else None
                name = company_name_tag.text.strip() if company_name_tag else None
                ticker = ticker_tag.text.strip() if ticker_tag else None
                company_details.append({
                    "name": name,
                    "link": full_link,
                    "ticker": ticker
                })
                return full_link
        else:
            print(f"Failed to fetch company link. HTTP Status Code: {response.status_code}")
            # For company link, just return None for all HTTP errors (will be handled as "not found")
            return None
    except Exception as e:
        print(f"Error fetching Sustainalytics company link: {e}")
        return None

def sustainalytics_company_data(url):
    try:
        headers = {
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
          'accept-language': 'en-US,en;q=0.9',
          'cookie': 'sf-data-intell-subject=1727087948762-4ef5e27a-d25e-4637-ac8e-787512e68589; sf-prs-ss=638626847488270000; sf-prs-lu=https://www.sustainalytics.com/; messagesUtk=9e77a6dbc2a84b39b0adfd1d8f6d7d7d; _cfuvid=xvaq7D5q5aJrTqKRCgQUTqFKb_JD920h1g2_BjtlqrY-1731930389083-0.0.1.1-604800000; sf_abtests=46ad2ba7-8713-472b-bc2e-2402ac50779f,6d9de14d-d722-452d-99af-702de9dbebc1; sf-ins-ssid=1732024410056-7830023b-ebb5-49dd-8217-e081ab29d6b7; sf-ins-pv-id=33777a3e-8928-477e-a1a7-1892e62dcd45',
          'priority': 'u=0, i',
          'referer': 'https://www.sustainalytics.com/esg-ratings',
          'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'sec-fetch-dest': 'document',
          'sec-fetch-mode': 'navigate',
          'sec-fetch-site': 'same-origin',
          'sec-fetch-user': '?1',
          'upgrade-insecure-requests': '1',
          'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:

            soup = BeautifulSoup(response.text, 'html.parser')

            company_data = {}

            name_tag = soup.select_one('.company-name h2')
            company_data['company_name'] = name_tag.text.strip() if name_tag else None

            industry_group_tag = soup.select_one('.industry-group')
            company_data['industry_group'] = industry_group_tag.text.strip() if industry_group_tag else None

            country_tag = soup.select_one('.country')
            company_data['country'] = country_tag.text.strip() if country_tag else None

            identifier_tag = soup.select_one('.identifier')
            company_data['identifier'] = identifier_tag.text.strip() if identifier_tag else None

            description_tag = soup.select_one('.company-description-text .collapse')
            company_data['description'] = description_tag.text.strip() if description_tag else None

            risk_rating_score_tag = soup.select_one('.risk-rating-score span')
            company_data['esg_score'] = risk_rating_score_tag.text.strip() if risk_rating_score_tag else None
            
            risk_rating_assessment_tag = soup.select_one('.risk-rating-assessment span')
            company_data['esg_risk_rating_assessment'] = risk_rating_assessment_tag.text.strip() if risk_rating_assessment_tag else None

            last_full_update_tag = soup.select_one('.update-date strong')
            company_data['last_full_update'] = last_full_update_tag.text.strip() if last_full_update_tag else None

            industry_position_tag = soup.select_one('.industry-group-position')
            industry_total_tag = soup.select_one('.industry-group-positions-total')

            if industry_position_tag and industry_total_tag:
                company_data['industry_ranking'] = f"{industry_position_tag.text.strip()} out of {industry_total_tag.text.strip()}"
            
            company_data['url'] = url
            company_data['source'] = "Sustainalytics"

            universe_position_tag = soup.select_one('.universe-position')
            universe_total_tag = soup.select_one('.universe-positions-total')
            if universe_position_tag and universe_total_tag:
                company_data['universe_ranking'] = f"{universe_position_tag.text.strip()} out of {universe_total_tag.text.strip()}"
            return company_data
        else:
            print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")
            # Only show serious HTTP errors (500+), treat others as "not found"
            if response.status_code >= 500:
                return {"error": f"HTTP error: {response.status_code}", "source": "Sustainalytics"}
            else:
                return {"esg_score": "-", "source": "Sustainalytics"}
    except Exception as e:
        print(f"Error fetching Sustainalytics company data: {e}")
        return {"error": f"Exception: {str(e)}", "source": "Sustainalytics"}

def sustainalytics_score(company_name):
    link = sustainalytics_company_link(company_name)
    if link is None:
        return {"esg_score": "-", "source": "Sustainalytics"}
    else:
        data = sustainalytics_company_data(link)
        if data is None:
            return {"esg_score": "-", "source": "Sustainalytics"}
        # If it's an error response, check if it's a real error or just "not found"
        if isinstance(data, dict) and "error" in data:
            error_msg = data.get("error", "")
            if "HTTP error: 5" in error_msg or "network" in error_msg.lower() or "timeout" in error_msg.lower():
                return data  # Return only serious system errors
            else:
                return {"esg_score": "-", "source": "Sustainalytics"}  # All other cases = "-"
        return data
