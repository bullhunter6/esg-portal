"""
ESG Score search functionality
"""
import importlib
import concurrent.futures
from flask import current_app, Response, stream_with_context
from esg_portal.utils.cache_utils import cached_api_response
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Define available score extractors
SCORE_EXTRACTORS = {
    "S&P": "esg_portal.search_tool.score_extractors.snp",
    "Sustainalytics": "esg_portal.search_tool.score_extractors.sustainalytics",
    "ISS": "esg_portal.search_tool.score_extractors.iss",
    "LSEG": "esg_portal.search_tool.score_extractors.lseg",
    "MSCI": "esg_portal.search_tool.score_extractors.msci",
    "CDP": "esg_portal.search_tool.score_extractors.cdp"
}

@cached_api_response(timeout=300)  # Cache for 5 minutes
def fetch_score(source, company_name, year=None):
    """
    Fetch ESG score for a specific source
    
    Args:
        source: The rating agency (S&P, Sustainalytics, etc.)
        company_name: The name of the company
        year: The year for the score (optional)
        
    Returns:
        dict: Score details
    """
    # Log the search attempt
    logger.info(f"Fetching ESG score for {company_name} from {source} for year {year}")
    
    try:
        # Import the appropriate module
        module_path = SCORE_EXTRACTORS.get(source)
        if not module_path:
            return {"error": f"Unsupported source: {source}"}
            
        module = importlib.import_module(module_path)
        
        # Get the appropriate function
        if source == "CDP":
            score_func = lambda name: module.cdp_score(name, year)
        elif source == "S&P":
            score_func = module.snp_score
        elif source == "Sustainalytics":
            score_func = module.sustainalytics_score
        elif source == "ISS":
            score_func = module.iss_score
        elif source == "LSEG":
            score_func = module.lseg_score
        elif source == "MSCI":
            score_func = module.msci_score
        else:
            return {"error": f"Unsupported source: {source}"}
        
        # Fetch the score
        result = score_func(company_name)
        
        # Process the result based on the source
        if source == "CDP":
            if not isinstance(result, list):
                return {"error": f"CDP response is not a list: {type(result)}"}
            return result
        elif source == "S&P":
            return {
                "Company Name": result.get("long_name", "-"),
                "Ticker": result.get("ticker", "-"),
                "Country": result.get("country", "-"),
                "Year": result.get("year", "-"),
                "ESG Score": result.get("esg_score", "-"),
                "Environmental Score": result.get("environmental_score", "-"),
                "Social Score": result.get("social_score", "-"),
                "Governance Score": result.get("governance_score", "-"),
                "Industry": result.get("industry", "-"),
                "Global Rank": f"{result.get('rank', '-')} out of {result.get('rank_out_of', '-')}",
                "URL": result.get("url", "-"),
                "YoY Change in ESG Score": f"{result.get('yoy_change', '-')}%",
                "Data Last Modified": result.get("datetime_modified", "-"),
            }
        elif source == "Sustainalytics":
            return {
                "Company Name": result.get("company_name", "-"),
                "Industry Group": result.get("industry_group", "-"),
                "Country": result.get("country", "-"),
                "ESG Score": result.get("esg_score", "-"),
                "Risk Level": result.get("esg_risk_rating_assessment", "-"),
                "Industry Ranking": result.get("industry_ranking", "-"),
                "Universe Ranking": result.get("universe_ranking", "-"),
                "URL": result.get("url", "-"),
                "Last Full Update": result.get("last_full_update", "-"),
            }
        elif source == "ISS":
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
        elif source == "LSEG":
            return {
                "Company Name": result.get("Company Name", "-"),
                "Ric Code": result.get("Ric Code", "-"),
                "Industry Type": result.get("Industry Type", "-"),
                "Score Year": result.get("Score Year", "-"),
                "ESG Score": result.get("TR.TRESG", "-"),
                "Governance Pillar": result.get("TR.GovernancePillar", "-"),
                "Environment Pillar": result.get("TR.EnvironmentPillar", "-"),
                "Social Pillar": result.get("TR.SocialPillar", "-"),
            }
        elif source == "MSCI":
            return {
                "Company Name": result.get("Company Name", "-"),
                "Ticker": result.get("Ticker", "-"),
                "Industry": result.get("Industry", "-"),
                "Country/Region": result.get("Country/Region", "-"),
                "ESG Rating": result.get("ESG Rating", "-"),
            }
        else:
            return {"error": f"Unknown source: {source}"}
    except Exception as e:
        error_msg = str(e)
        try:
            app = current_app._get_current_object()
            app.logger.error(f"Error fetching {source} score for {company_name}: {e}")
        except RuntimeError:
            # Outside of application context, just continue
            print(f"Error fetching {source} score for {company_name}: {e}")
        
        # Check if this is an application context error
        if "application context" in error_msg:
            return {"error": "Application context error. Please try again."}
        return {"error": f"Error fetching {source} score: {str(e)}"}

def _fetch_single_score(args):
    """Helper function for parallel processing that doesn't rely on request context"""
    source, company_name, year = args if len(args) > 2 else (*args, None)
    try:
        if current_app:
            logger.info(f"Fetching {source} score for: {company_name}")
        else:
            print(f"Fetching {source} score for: {company_name}")
        
        result = fetch_score(source, company_name)
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Error fetching {source} score: {result['error']}")
            return source, "-"
        
        score_value = None
        if isinstance(result, dict):
            if source == "S&P" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "Sustainalytics" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "MSCI" and "ESG Rating" in result:
                score_value = result["ESG Rating"]
            elif source == "LSEG" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "ISS" and "score" in result:
                score_value = result["score"]
            elif "score" in result:
                score_value = result["score"]
            elif "value" in result:
                score_value = result["value"]
            elif "rating" in result:
                score_value = result["rating"]
        
        if not score_value and isinstance(result, (str, int, float)):
            score_value = result
            
        if not score_value:
            score_value = "-"
        
        return source, score_value
    except Exception as e:
        if current_app:
            logger.error(f"Error processing {source} score: {e}")
        else:
            print(f"Error processing {source} score: {e}")
        
        return source, "-"

def fetch_all_scores(company_name, year=None):
    """
    Fetch ESG scores from all sources using concurrent processing
    
    Args:
        company_name: The name of the company
        year: The year for the score (optional)
        
    Returns:
        dict: Scores from all sources
    """
    results = {}
    sources = ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
    
    # Use concurrent futures to fetch scores in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
        # Submit all tasks
        future_to_source = {
            executor.submit(_fetch_single_score, (source, company_name, year)): source 
            for source in sources
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_source):
            source = future_to_source[future]
            try:
                source, score = future.result()
                results[source] = score
            except Exception as e:
                logger.error(f"Error in concurrent fetch for {source}: {e}")
                results[source] = "-"
    
    return results

def _fetch_single_score_sse(args):
    """Helper function for parallel processing that emits SSE events"""
    source, company_name, year = args if len(args) > 2 else (*args, None)
    try:
        if current_app:
            logger.info(f"Fetching {source} score for: {company_name}")
        else:
            print(f"Fetching {source} score for: {company_name}")
        
        # Emit starting event
        yield f"data: {json.dumps({'company': company_name, 'source': source, 'status': 'fetching', 'message': f'Fetching {source} score...', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        result = fetch_score(source, company_name)
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Error fetching {source} score: {result['error']}")
            # Emit error event
            yield f"data: {json.dumps({'company': company_name, 'source': source, 'status': 'error', 'message': result['error'], 'timestamp': datetime.now().isoformat()})}\n\n"
            return source, "-"
        
        score_value = None
        if isinstance(result, dict):
            if source == "S&P" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "Sustainalytics" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "MSCI" and "ESG Rating" in result:
                score_value = result["ESG Rating"]
            elif source == "LSEG" and "ESG Score" in result:
                score_value = result["ESG Score"]
            elif source == "ISS" and "score" in result:
                score_value = result["score"]
            elif "score" in result:
                score_value = result["score"]
            elif "value" in result:
                score_value = result["value"]
            elif "rating" in result:
                score_value = result["rating"]
        
        if not score_value and isinstance(result, (str, int, float)):
            score_value = result
            
        if not score_value:
            score_value = "-"
        
        # Emit success event
        yield f"data: {json.dumps({'company': company_name, 'source': source, 'status': 'success', 'score': score_value, 'timestamp': datetime.now().isoformat()})}\n\n"
        
        return source, score_value
    except Exception as e:
        if current_app:
            logger.error(f"Error processing {source} score: {e}")
        else:
            print(f"Error processing {source} score: {e}")
            
        # Emit error event
        yield f"data: {json.dumps({'company': company_name, 'source': source, 'status': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
        
        return source, "-"

def stream_all_scores(company_name, year=None):
    """
    Stream ESG scores from all sources using Server-Sent Events
    
    Args:
        company_name: The name of the company
        year: The year for the score (optional)
        
    Returns:
        Response: A Flask Response object with SSE stream
    """
    def generate():
        sources = ["S&P", "Sustainalytics", "ISS", "LSEG", "MSCI"]
        
        # Use concurrent futures to fetch scores in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
            # Submit all tasks
            future_to_source = {
                executor.submit(_fetch_single_score_sse, (source, company_name, year)): source 
                for source in sources
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    for event in future.result():
                        yield event
                except Exception as e:
                    logger.error(f"Error in concurrent fetch for {source}: {e}")
                    yield f"data: {json.dumps({'company': company_name, 'source': source, 'status': 'error', 'message': str(e), 'timestamp': datetime.now().isoformat()})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')