import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

def snp_company_id(company_name):
    query = urlencode({"comp-name": company_name})
    url = f"https://www.spglobal.com/esg/csa/esg-proxy?{query}"
    headers = {
      'accept': 'application/json, text/javascript, */*; q=0.01',
      'accept-language': 'en-US,en;q=0.9',
      'cookie': 'captcha-image-209796=NUxnpTyRD2iNNV7FUAFaDQ==; bc_tstgrp=17; s_inv=0; opvc=eb35eb32-34c7-4ec3-94f8-9f2bfb5cfd5e; sitevisitscookie=1; dmid=f463d617-41b8-4adf-a9f0-ae975390d299; AMCVS_92221CFE533057500A490D45%40AdobeOrg=1; AMCV_92221CFE533057500A490D45%40AdobeOrg=179643557%7CMCIDTS%7C19843%7CMCMID%7C03701438445244117284460734832984461550%7CMCOPTOUT-1714376610s%7CNONE%7CvVersion%7C5.5.0; last_visit_bc=1714631808947; _zitok=377c35becc1c6bc525d91715583012; captcha-image-857636=ImPI00Ig+axXBLyVQ9WPIg==; marketintelligence-brand-campaign=Ad_Type_Medium__c=cpc&Ad_Source__c=&Ad_Campaign__c=Brand_ESG_Search&Ad_Content__c=534418150272&Ad_Term_s__c=&AdWords_Campaign_Name__c=&AdWords_ID__c=&AdWords_Keyword__c=&full_ref_url=unknown; _cq_duid=1.1719386881.yBiFbzwf2ogTjPBg; _cq_suid=1.1719386881.HZZFI0qVNdBB2CDv; ASP.NET_SessionId=jxnvupu24yl4bq3fxztuh0me; OptanonAlertBoxClosed=2024-10-23T13:41:57.730Z; driftt_aid=7ce0118a-b0a0-4202-bbd5-a9a67ae08d9f; JSESSIONID=49E035223C3519F3719F09618DAD844C.10.58.72.146; drift_aid=7ce0118a-b0a0-4202-bbd5-a9a67ae08d9f; session_start_timestamp=1732011575; s_gpv=www.spglobal.com:esg:scores:results; s_dur=1732011575870; s_nr365=1732011582175-Repeat; s_tslv=1732011582176; OptanonConsent=isGpcEnabled=0&datestamp=Tue+Nov+19+2024+14%3A19%3A42+GMT%2B0400+(Gulf+Standard+Time)&version=202409.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=179079f1-0b8b-4e78-bf3a-96b645d6fbd8&interactionCount=3&isAnonUser=1&landingPath=NotLandingPage&groups=C0003%3A0%2CC0004%3A0%2CC0002%3A0%2CC0001%3A1&AwaitingReconsent=false&geolocation=AE%3BDU&intType=2; ASP.NET_SessionId=y4c3zhlb35vx23p0f3th1ve4',
      'priority': 'u=1, i',
      'referer': 'https://www.spglobal.com/esg/scores/results?cid=6451646',
      'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'empty',
      'sec-fetch-mode': 'cors',
      'sec-fetch-site': 'same-origin',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
      'x-newrelic-id': 'VQ4AVldVDRABVVNXBgMPX1Y=',
      'x-requested-with': 'XMLHttpRequest'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list):
            return data[0].get("id")
    return None


def snp_company_details(company_id):
    url = f"https://www.spglobal.com/esg/scores/results?cid={company_id}"
    headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'Cookie': 'ASP.NET_SessionId=n0paabwonecxojzmr0vq4f4v'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        company_data = soup.find('div', id='company-data')
        if company_data:
            raw_ticker = company_data.get('data-company-ticker', '')
            clean_ticker = raw_ticker.replace('<b>Ticker:</b>', '').strip()
            details = {
                "company_id": company_data.get('data-company-id'),
                "long_name": company_data.get('data-long-name'),
                "short_name": company_data.get('data-short-name'),
                "country": company_data.get('data-country'),
                "rank": company_data.get('data-company-rank'),
                "rank_out_of": company_data.get('data-company-rank-out-of'),
                "datetime_modified": company_data.get('data-datetime-modified'),
                "yoy_change": company_data.get('data-yoy-change'),
                "esg_score": company_data.get('data-yoy-score'),
                "industry": company_data.get('data-industry'),
                "year": company_data.get('data-year'),
                "ticker": clean_ticker,
                "availability_level": company_data.get('data-availabilitylevel'),
                "url": url,
                "source": "S&P Global"
            }
            esg_score = company_data.get('data-yoy-score')
            details["esg_score"] = esg_score
            scores = {
                "environmental": soup.find('div', id='dimentions-score-env'),
                "social": soup.find('div', id='dimentions-score-social'),
                "governance": soup.find('div', id='dimentions-score-govecon')
            }
            for key, tag in scores.items():
                if tag:
                    details[f"{key}_score"] = tag.get('data-score')
                    details[f"{key}_avg"] = tag.get('data-avg')
                    details[f"{key}_max"] = tag.get('data-max')
                    details[f"{key}_rank"] = tag.get('data-rank')
                    details[f"{key}_rank_out_of"] = tag.get('data-rank-out-of')

            return details
    return None

def snp_score(company_name):
    print(f"Fetching S&P score for: {company_name}")
    company_id = snp_company_id(company_name)
    if company_id is None:
        return {"esg_score": "-", "source": "S&P"}
    else:
        if company_id:
            result = snp_company_details(company_id)
            if result:
                # Ensure the result has the expected fields
                if "esg_score" not in result:
                    result["esg_score"] = "-"
                result["source"] = "S&P"
                return result
        return {"esg_score": "-", "source": "S&P"}