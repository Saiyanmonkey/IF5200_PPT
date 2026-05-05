import os

from dotenv import load_dotenv
import neo4j

from backend.app.recommendation.llm import init_gemini_skill_extraction_pipeline
from backend.app.repositories import SkillRepository

def prepare_llm_pipeline(repo: SkillRepository):
    load_dotenv()

    API_KEY = os.getenv("GEMINI_API_KEY", "???")
    MODEL_NAME = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3-flash-preview")
    skills = repo.get_all_skills()
    skills = {name for _, name in skills}
    skills = list(skills)

    return init_gemini_skill_extraction_pipeline(
        api_key=API_KEY,
        model_name=MODEL_NAME,
        skills=skills,
        verbose=True
    )

def prepare_neo4j_driver_and_database_name():
    load_dotenv()

    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://xxxxx.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your-password-here")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return driver, NEO4J_DATABASE


sample_input = """
You’ll join the GoTo Data Science team—a group dedicated to building machine learning solutions that keep GoTo’s digital payment ecosystem safe and reliable. Our team combines expertise in math, statistics, and machine learning to solve real business challenges for GoPay. We work collaboratively, learn from each other, and share ideas through team discussions, internal forums, and regular knowledge-sharing sessions.

About GoTo Group
GoTo is the largest digital ecosystem in Indonesia. GoTo's mission is to 'empower progress' by offering technology infrastructure and solutions that help everyone to access and thrive in the digital economy.
The GoTo ecosystem provides a wide range of services, including mobility, delivery, payments, financial services, and technology solutions for merchants. The ecosystem also provides e-commerce services through Tokopedia and banking services through its partnership with Bank Jago.
About Gojek 
Gojek is Southeast Asia’s leading on-demand platform and pioneer of the multi-service ecosystem with over 2.5 million driver partners across the regions offering a wide range of services such as transportation, food delivery, logistics and more. With its mission to create impact at scale, Gojek is committed to resolving consumer problems and raising standards of living by connecting consumers to the best providers of goods and services in the market.
About GoTo Financial
GoTo Financial accelerates financial inclusion through its leading financial services and merchants solutions. Its consumer services include GoPay and GoPayLater and serve businesses of all sizes through Midtrans, Moka, GoBiz Plus, GoBiz, and Selly. With its trusted and inclusive ecosystem of products, GoTo Financial is open to new growth opportunities and aims to empower everyone to Make It Happen, Make It Together, Make It Last.
GoTo and its business units, including Gojek and GoToFinancial ("GoTo") only post job opportunities on our official channels on our respective company websites and on LinkedIn. GoTo is not liable for any job postings or job offers that did not originate from us. You should conduct your own due diligence to prevent being victims of any fake job scams, if they did not originate from GoTo's official recruitment channels.
#LI-ONSITE

We may use artificial intelligence (AI) tools to support parts of the hiring process, such as reviewing applications, analyzing resumes, or assessing responses. These tools assist our recruitment team but do not replace human judgment. Final hiring decisions are ultimately made by humans. If you would like more information about how your data is processed, please contact us.
""".strip()

if __name__ == "__main__":
    driver, NEO4J_DATABASE = prepare_neo4j_driver_and_database_name()
    repo = SkillRepository(driver, database=NEO4J_DATABASE)
    pipeline = prepare_llm_pipeline(repo)
    print("Pipeline prepared.")
    result = pipeline([sample_input])
    print(type(result))
    print(result)
