import bs4
from bs4 import BeautifulSoup
import requests

URL_DOMAIN = "https://id.jobstreet.com"
GRAPHQL_QUERY_TEMPLATE = """{"operationName":"SearchCompanies","variables":{"name":"<company_name>","includeBranding":false,"limit":50,"published":true,"zone":"asia-4"},"query":"query SearchCompanies($name: String!, $includeBranding: Boolean!, $limit: Int, $zone: Zone, $published: Boolean) {\n  searchCompanyProfilesByName(\n    name: $name\n    includeBranding: $includeBranding\n    limit: $limit\n    zone: $zone\n    published: $published\n  ) {\n    companyId\n    data {\n      name\n      branding {\n        logo\n        __typename\n      }\n      reviewCount\n      reviewRating\n      slug\n      published\n      __typename\n    }\n    organisationId\n    zone\n    __typename\n  }\n}"}""".strip().replace("\n", "\\n")

def fetch_company_slug(company_name: str):
    graphql_query = GRAPHQL_QUERY_TEMPLATE.replace("<company_name>", company_name.replace("\\", "\\\\").replace("\"", "\\\""))
    res = requests.post(
        f"{URL_DOMAIN}/graphql",
        headers={"Content-Type": "application/json"},
        data=graphql_query
    )
    res = res.json()
    res = res["data"]
    res = res["searchCompanyProfilesByName"]
    if len(res) == 0:
        return None
    
    res = res[0]
    res = res["data"]
    res = res["slug"]
    return str(res)

def jobs_raw_html(slug: str):
    job_list_url = f"{URL_DOMAIN}/id/companies/{slug}/jobs"
    res = requests.get(job_list_url)
    raw_html = res.text
    return raw_html

def access_child(soup: bs4.Tag | None, name: str, index: int):
    if soup is None:
        return
    
    x = soup.find_all(name, recursive=False)
    if len(x) <= index:
        return
    
    return x[index]

def extract(raw_html: str):
    soup = BeautifulSoup(raw_html, features="html.parser")
    soup = soup.find(id="company-profile_3_panel")
    if soup is None:
        return
    
    soup = access_child(soup, "div", 0)
    soup = access_child(soup, "div", 1)
    soup = access_child(soup, "div", 0)
    soup = access_child(soup, "div", 0)
    soup = access_child(soup, "div", 0)
    soup = access_child(soup, "div", 1)
    if soup is None:
        return
    
    result = []
    for x in soup.find_all("div", recursive=False):
        x = access_child(x, "div", 0)
        x = access_child(x, "article", 0)
        x = access_child(x, "div", 2)
        x = access_child(x, "div", 0)
        x = access_child(x, "div", 1)
        x = access_child(x, "div", 0)
        x = access_child(x, "div", 0)
        x = access_child(x, "div", 0)
        x = access_child(x, "h3", 0)
        x = access_child(x, "div", 0)
        x = access_child(x, "a", 0)
        if x is None:
            print("Warning: None result detected")
        else:
            result.append({
                "name": x.text,
                "href": x.attrs["href"]
            })

    return result

def extract_description(href: str):
    job_url = URL_DOMAIN + href
    res = requests.get(job_url)
    raw_html = res.text

    soup = BeautifulSoup(raw_html, features="html.parser")
    soup = soup.find(attrs={"data-automation": "jobAdDetails"})
    if soup is None:
        return None
    
    soup = access_child(soup, "div", 0)
    if soup is None:
        return None

    result = []
    for x in soup.children:
        text = x.text.strip()
        if text:
            result.append(text)
    
    if len(result) == 0:
        return None

    return "\n".join(result)

href = "/job/91461974?cid=company-profile&ref=company-profile&origin=cardTitle"
print(extract_description(href))
