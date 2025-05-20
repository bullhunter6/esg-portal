from search_tool.score_extractors.snp import snp_score
from search_tool.score_extractors.sustainalytics import sustainalytics_score
from search_tool.score_extractors.iss import iss_score
from search_tool.score_extractors.lseg import lseg_score
from search_tool.score_extractors.msci import msci_score
from search_tool.score_extractors.cdp import cdp_score


def fetch_all_scores(company_name):
    """Fetch ESG scores from all sources for the given company."""
    scores = {}

    try:
        snp_data = snp_score(company_name)
        scores["S&P"] = snp_data.get("esg_score", "-") if isinstance(snp_data, dict) else "-"

        sustainalytics_data = sustainalytics_score(company_name)
        if isinstance(sustainalytics_data, dict) and "error" not in sustainalytics_data:
            scores["Sustainalytics"] = sustainalytics_data.get("esg_score", "-")
        else:
            error_msg = sustainalytics_data.get("error", "Unknown error") if isinstance(sustainalytics_data, dict) else "Invalid data format"
            scores["Sustainalytics"] = f"-"
            print(f"Sustainalytics error: {error_msg}")

        iss_data = iss_score(company_name)
        if isinstance(iss_data, list) and len(iss_data) > 0:
            iss_data = iss_data[0]
        scores["ISS"] = iss_data.get("oekomRating", "-") if isinstance(iss_data, dict) else "-"

        lseg_data = lseg_score(company_name)
        scores["LSEG"] = lseg_data.get("TR.TRESG", "-") if isinstance(lseg_data, dict) else "-"

        msci_data = msci_score(company_name)
        scores["MSCI"] = msci_data.get("ESG Rating", "-") if isinstance(msci_data, dict) else "-"

    except Exception as e:
        print(f"Error fetching scores for {company_name}: {e}")
        scores["Error"] = str(e)

    return scores


def fetch_source_details(source, company_name, year):
    """Fetch detailed ESG information for a company from a specific source."""
    print(f"Fetching details for source: {source}, company: {company_name}")
    if year is not None:
        year = str(year)
    source_fetchers = {
        "SNP": snp_score,
        "Sustainalytics": sustainalytics_score,
        "ISS": iss_score,
        "LSEG": lseg_score,
        "MSCI": msci_score,
        "CDP": lambda name: cdp_score(name, year)
    }

    try:
        fetch_function = source_fetchers.get(source)
        if not fetch_function:
            return {"error": f"Unsupported source: {source}"}

        raw_details = fetch_function(company_name)
        print(raw_details)

        if source == "CDP":
            if not isinstance(raw_details, list):
                details = {"error": f"CDP response is not a list: {type(raw_details)}"}
            else:
                details = raw_details
        elif source == "SNP":
            details = {
                "Company Name": raw_details.get("long_name", "-"),
                "Ticker": raw_details.get("ticker", "-"),
                "Country": raw_details.get("country", "-"),
                "Year": raw_details.get("year", "-"),
                "ESG Score": raw_details.get("esg_score", "-"),
                "Environmental Score": raw_details.get("environmental_score", "-"),
                "Social Score": raw_details.get("social_score", "-"),
                "Governance Score": raw_details.get("governance_score", "-"),
                "Industry": raw_details.get("industry", "-"),
                "Global Rank": f"{raw_details.get('rank', '-')} out of {raw_details.get('rank_out_of', '-')}",
                "URL": raw_details.get("url", "-"),
                "YoY Change in ESG Score": f"{raw_details.get('yoy_change', '-')}%",
                "Data Last Modified": raw_details.get("datetime_modified", "-"),
            }
        elif source == "Sustainalytics":
            if isinstance(raw_details, dict) and "error" in raw_details:
                details = {"error": raw_details["error"]}
            else:
                details = {
                    "Company Name": raw_details.get("company_name", "-"),
                    "Industry Group": raw_details.get("industry_group", "-"),
                    "Country": raw_details.get("country", "-"),
                    "ESG Score": raw_details.get("esg_score", "-"),
                    "Risk Level": raw_details.get("esg_risk_rating_assessment", "-"),
                    "Industry Ranking": raw_details.get("industry_ranking", "-"),
                    "Universe Ranking": raw_details.get("universe_ranking", "-"),
                    "URL": raw_details.get("url", "-"),
                    "Last Full Update": raw_details.get("last_full_update", "-"),
                }
        elif source == "ISS":
            iss_data = iss_score(company_name)
            if isinstance(iss_data, list) and len(iss_data) > 0:
                iss_data = iss_data[0]
            details = iss_data
        elif source == "LSEG":
            details = {
                "Company Name": raw_details.get("Company Name", "-"),
                "Ric Code": raw_details.get("Ric Code", "-"),
                "Industry Type": raw_details.get("Industry Type", "-"),
                "Score Year": raw_details.get("Score Year", "-"),
                "ESG Score": raw_details.get("TR.TRESG", "-"),
                "Governance Pillar": raw_details.get("TR.GovernancePillar", "-"),
                "Environment Pillar": raw_details.get("TR.EnvironmentPillar", "-"),
                "Social Pillar": raw_details.get("TR.SocialPillar", "-"),
            }
        elif source == "MSCI":
            details = {
                "Company Name": raw_details.get("Company Name", "-"),
                "Ticker": raw_details.get("Ticker", "-"),
                "Industry": raw_details.get("Industry", "-"),
                "Country/Region": raw_details.get("Country/Region", "-"),
                "ESG Rating": raw_details.get("ESG Rating", "-"),
            }
        else:
            details = {"error": f"Unknown source: {source}"}

    except Exception as e:
        details = {"error": f"Error fetching details for {source} - {company_name}: {str(e)}"}

    if not isinstance(details, (dict, list)):
        details = {"error": f"Unexpected data format for {source} - {company_name}"}

    return details