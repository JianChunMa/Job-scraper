import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

MAX_RESULTS = 10
ACTOR_ID = "blackfalcondata/jobstreet-scraper"

st.set_page_config(
    page_title="JobStreet Job Scraper",
    page_icon="💼",
    layout="wide"
)

# ============================================================
# APIFY CLIENT
# ============================================================

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

if not APIFY_API_TOKEN:
    st.error(
        "APIFY_API_TOKEN is not configured. "
        "Add it to your .env file."
    )
    st.stop()

client = ApifyClient(APIFY_API_TOKEN)


# ============================================================
# HELPERS
# ============================================================

def clean_value(value):
    """Convert empty values to None."""
    if value is None:
        return None

    if isinstance(value, str) and not value.strip():
        return None

    return value


def scrape_jobs(run_input):
    """Run JobStreet scraper and return results."""

    try:
        run = client.actor(ACTOR_ID).call(
            run_input=run_input
        )

        # Handle both dict and object return types
        dataset_id = (
            run.default_dataset_id 
            if hasattr(run, "default_dataset_id") 
            else run.get("defaultDatasetId")
        )

        if not dataset_id:
            st.error("Apify did not return a dataset.")
            return []

        results = []

        for item in client.dataset(dataset_id).iterate_items():
            results.append(item)

            # Extra safety: never return > 10
            if len(results) >= MAX_RESULTS:
                break

        return results

    except Exception as e:
        st.error(f"Scraping failed: {e}")
        return []

    
def get_job_url(job):
    """
    Try several common URL fields because scraper output
    can vary.
    """

    possible_fields = [
        "url",
        "jobUrl",
        "jobURL",
        "job_url",
        "link",
        "jobLink",
        "applyUrl",
        "applyURL"
    ]

    for field in possible_fields:
        value = job.get(field)

        if value:
            return value

    return None


def normalize_jobs(jobs):
    """Convert scraper output into a simple dataframe."""

    rows = []

    for job in jobs:

        row = {
            "Job Title": (
                job.get("title")
                or job.get("jobTitle")
                or job.get("position")
                or ""
            ),

            "Company": (
                job.get("company")
                or job.get("companyName")
                or ""
            ),

            "Location": (
                job.get("location")
                or job.get("jobLocation")
                or ""
            ),

            "Salary": (
                job.get("salary")
                or job.get("salaryText")
                or ""
            ),

            "Work Type": (
                job.get("workType")
                or job.get("employmentType")
                or ""
            ),

            "Work Arrangement": (
                job.get("workArrangement")
                or job.get("workMode")
                or ""
            ),

            "Date Posted": (
                job.get("datePosted")
                or job.get("postedDate")
                or ""
            ),

            "URL": get_job_url(job),

            "Description": (
                job.get("description")
                or ""
            )
        }

        rows.append(row)

    return pd.DataFrame(rows)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🔎 Job Search")

query = st.sidebar.text_input(
    "Job title / keyword",
    value="software engineer",
    placeholder="e.g. data analyst"
)


COUNTRIES = {
    "Malaysia": "MY",
    "Singapore": "SG",
    "Indonesia": "ID",
    "Philippines": "PH"
}


country_name = st.sidebar.selectbox(
    "Country",
    list(COUNTRIES.keys())
)

country_code = COUNTRIES[country_name]

location = st.sidebar.text_input(
    "Location",
    placeholder="e.g. Kuala Lumpur"
)

# ------------------------------------------------------------
# Work filters
# ------------------------------------------------------------

st.sidebar.subheader("Work Filters")

work_type = st.sidebar.selectbox(
    "Work type",
    [
        "Any",
        "Full time",
        "Part time",
        "Contract",
        "Casual",
        "Internship"
    ]
)

work_arrangement = st.sidebar.selectbox(
    "Work arrangement",
    [
        "Any",
        "On-site",
        "Hybrid",
        "Remote"
    ]
)

# ------------------------------------------------------------
# Salary
# ------------------------------------------------------------

st.sidebar.subheader("Salary")

salary_min = st.sidebar.number_input(
    "Minimum salary",
    min_value=0,
    value=0,
    step=100
)

salary_max = st.sidebar.number_input(
    "Maximum salary",
    min_value=0,
    value=0,
    step=100
)

# ------------------------------------------------------------
# Keywords
# ------------------------------------------------------------

st.sidebar.subheader("Keywords")

include_keywords = st.sidebar.text_input(
    "Include keywords",
    placeholder="e.g. Python, SQL"
)

exclude_keywords = st.sidebar.text_input(
    "Exclude keywords",
    placeholder="e.g. senior, manager"
)

# ------------------------------------------------------------
# Date
# ------------------------------------------------------------

st.sidebar.subheader("Date Posted")

date_range = st.sidebar.selectbox(
    "Date range",
    [
        "Any",
        "Last 24 hours",
        "Last 3 days",
        "Last 7 days",
        "Last 14 days",
        "Last 30 days"
    ]
)

# ============================================================
# MAIN PAGE
# ============================================================

st.title("💼 JobStreet Job Scraper")

st.markdown(
    """
    Search JobStreet jobs using Apify and view the results
    directly in this dashboard.
    """
)

# Limit is intentionally fixed to 10
st.info(
    f"Maximum results per search: **{MAX_RESULTS} jobs**"
)

# ============================================================
# SEARCH BUTTON
# ============================================================

search_clicked = st.button(
    "🔍 Search Jobs",
    type="primary",
    use_container_width=True
)

if search_clicked:

    if not query.strip():
        st.warning("Please enter a job title or keyword.")
        st.stop()

    # --------------------------------------------------------
    # Convert UI values
    # --------------------------------------------------------

    work_type_value = (
        None if work_type == "Any"
        else work_type
    )

    work_arrangement_value = (
        None if work_arrangement == "Any"
        else work_arrangement
    )

    date_range_value = (
        None if date_range == "Any"
        else date_range
    )

    # --------------------------------------------------------
    # Apify input
    # --------------------------------------------------------

    run_input = {
    "query": query.strip(),
    "country": country_code,
    "location": location.strip(),
    "startUrls": [],
    "maxResults": 10,
    "maxPages": 5,
    "sortMode": "relevance",

    "includeDetails": True,
    "includeApplicantInsights": True,

    "descriptionMaxLength": 0,
    "compact": False,
    "descriptionFormat": "all",
    "excludeEmptyFields": False,

    "incrementalMode": False,
    "emitUnchanged": False,
    "emitExpired": False,
    "skipReposts": False,

    "requireContact": "off",
    "notificationLimit": 5,
    "notifyOnlyChanges": False,
    "includeRunSummary": True
}

    # --------------------------------------------------------
    # Run scraper
    # --------------------------------------------------------

    with st.spinner("Scraping JobStreet..."):

        jobs = scrape_jobs(run_input)

    if not jobs:
        st.warning("No jobs found.")
        st.stop()

    # --------------------------------------------------------
    # Normalize results
    # --------------------------------------------------------

    df = normalize_jobs(jobs)

    # Extra safety
    df = df.head(MAX_RESULTS)

    st.session_state["jobs_df"] = df


# ============================================================
# DISPLAY RESULTS
# ============================================================

if "jobs_df" in st.session_state:

    df = st.session_state["jobs_df"]

    st.success(
        f"Found {len(df)} job(s)"
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Jobs",
            len(df)
        )

    with col2:
        companies = (
            df["Company"]
            .replace("", pd.NA)
            .dropna()
            .nunique()
        )

        st.metric(
            "Companies",
            companies
        )

    with col3:
        locations = (
            df["Location"]
            .replace("", pd.NA)
            .dropna()
            .nunique()
        )

        st.metric(
            "Locations",
            locations
        )

    # --------------------------------------------------------
    # Job cards
    # --------------------------------------------------------

    st.subheader("Job Results")

    for _, job in df.iterrows():

        with st.container(border=True):

            st.markdown(
                f"### {job['Job Title'] or 'Untitled Job'}"
            )

            col1, col2 = st.columns(2)

            with col1:

                if job["Company"]:
                    st.write(
                        f"🏢 **Company:** {job['Company']}"
                    )

                if job["Location"]:
                    st.write(
                        f"📍 **Location:** {job['Location']}"
                    )

                if job["Work Type"]:
                    st.write(
                        f"💼 **Work Type:** {job['Work Type']}"
                    )

            with col2:

                if job["Salary"]:
                    st.write(
                        f"💰 **Salary:** {job['Salary']}"
                    )

                if job["Work Arrangement"]:
                    st.write(
                        f"🏠 **Arrangement:** "
                        f"{job['Work Arrangement']}"
                    )

                if job["Date Posted"]:
                    st.write(
                        f"📅 **Posted:** "
                        f"{job['Date Posted']}"
                    )

            if job["URL"]:

                st.link_button(
                    "🔗 View JobStreet Listing",
                    job["URL"]
                )

            if job["Description"]:

                with st.expander("View Description"):

                    st.write(
                        job["Description"]
                    )

    # ========================================================
    # EXPORT
    # ========================================================

    st.subheader("Export")

    csv = df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="jobstreet_jobs.csv",
        mime="text/csv",
        use_container_width=True
    )