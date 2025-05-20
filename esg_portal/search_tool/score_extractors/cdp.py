import requests
from bs4 import BeautifulSoup

def get_cdp_table_data(company_name, year):
    encoded_company_name = requests.utils.quote(company_name)
    url = f"https://www.cdp.net/en/responses?page=1&per_page=20&sort_by=project_year&sort_dir=desc&queries%5Bname%5D={encoded_company_name}"
    headers = {
      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'accept-language': 'en-US,en;q=0.9',
      'cookie': 'locale=en; OptanonConsentFixClearedValues=true; OptanonConsentFixTriggered=true; OptanonAlertBoxClosed=2024-06-11T05:20:28.948Z; regional_selection_modal_choice_made=true; default_site_id=1; location=GLOB; detected_geographical_data_confirmed=true; cf_clearance=xUmWCvk_wzJEsYxlLceBYQZucLBm_.8fTk3_HFB7dGk-1727334161-1.2.1.1-3M6JKarmiWJv1dGR_1gKaZHKOT7e5eJundIxfVyu9.rg.N5sEGrCUPafE5EZ065fTrHQDlRMUnYmn1Dy313hzwCQjKE0C7Wi8zRbFfRGLhNvY8_uqPniWjoJ9_RV1mhBcSmO58Jeu3NV8_6CY46GkYdG81_IZBrC6nyy4p0zt1IS0_fgAy1csX3OW.6o7czzK.hV6GcPy0Wz0KZAQfTFMwGOrL92PFDB98LR_l63Po_Sjku1o078VxzyeOL28CfPzQ39vo2rwMNrcBpHvsH4U7H6.sozdh5ohaIj33_.HJnilWSAyOKINXuKzgcFQwvP1WOSoYRNTolSuM7GJQ9vdpRoralxjC73DXcw.qxuZlMUGaRiXWhqRA4bolNyYWcJt0d.aNmt1f6kzfCgr8b67w5l7M71XYWR.ok4psDW8Pk; session=ca6d1719755464f68afeb9abe1f51ea2; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Nov+20+2024+18%3A11%3A54+GMT%2B0400+(Gulf+Standard+Time)&version=202409.2.0&isIABGlobal=false&hosts=H5%3A1%2CH6%3A1%2CH9%3A1%2CH16%3A0%2CH4%3A0%2CH15%3A0%2CH11%3A0%2CH14%3A0%2CH13%3A0%2CH12%3A0%2CH7%3A0%2CH8%3A0%2CH20%3A0%2CH21%3A0%2CH24%3A0%2CH26%3A0%2CH10%3A0&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=AE%3BDU&AwaitingReconsent=false&browserGpcFlag=0&genVendors=; locale=en; session=ca6d1719755464f68afeb9abe1f51ea2',
      'priority': 'u=0, i',
      'referer': 'https://www.cdp.net/en/responses?queries%5Bname%5D=',
      'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
      'sec-ch-ua-arch': '"x86"',
      'sec-ch-ua-bitness': '"64"',
      'sec-ch-ua-full-version': '"131.0.6778.70"',
      'sec-ch-ua-full-version-list': '"Google Chrome";v="131.0.6778.70", "Chromium";v="131.0.6778.70", "Not_A Brand";v="24.0.0.0"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-model': '""',
      'sec-ch-ua-platform': '"Windows"',
      'sec-ch-ua-platform-version': '"19.0.0"',
      'sec-fetch-dest': 'document',
      'sec-fetch-mode': 'navigate',
      'sec-fetch-site': 'same-origin',
      'sec-fetch-user': '?1',
      'upgrade-insecure-requests': '1',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
          soup = BeautifulSoup(response.text, 'html.parser')
          table = soup.find('table', class_='sortable_table')

          data = []

          if table:
              for row in table.find_all('tr')[1:]:
                  columns = row.find_all('td')
                  if columns:
                      account_name = columns[0].get_text(strip=True)
                      response_name = columns[1].get_text(strip=True)
                      project_year = columns[2].get_text(strip=True)
                      response_status = columns[3].get_text(strip=True)
                      response_score_band = ''.join([score.get_text(strip=True) for score in columns[4].find_all('div', class_='investor-program__score_band_single')])

                      if project_year == year:
                          data.append({
                                    'Source':'CDP',
                                    'Company Name': account_name,
                                    'Response Name': response_name,
                                    'Project Year': project_year,
                                    'Response Status': response_status,
                                    'Response Score Band': response_score_band
                                })

          return data
    else:
        return f"Error: Failed to fetch data from CDP with status code {response.status_code}"
    
def cdp_score(company_name, year):
    data = get_cdp_table_data(company_name, year)
    if data:
        return data
    else:
        return "Company not found."