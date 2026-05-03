from jobspy import scrape_jobs
import pandas as pd

def search_jobs(search_term: str, location: str, is_remote: bool):
    """
    Search jobs using JobSpy library.
    """
    site_names = ["linkedin", "indeed", "glassdoor", "naukri"]
    
    jobs: pd.DataFrame = scrape_jobs(
        site_name=site_names,
        search_term=search_term,
        location=location,
        is_remote=is_remote,
        results_wanted=20, # keeping it reasonable for a quick search
        country_indeed='India' if 'india' in location.lower() else 'USA', # Glassdoor and Indeed require this
        hours_old=72,
    )
    
    if jobs is None or jobs.empty:
        return []
    
    # Convert dataframe to a list of dicts, replacing NaNs with None
    return jobs.replace({pd.NA: None, float('nan'): None}).to_dict(orient="records")
