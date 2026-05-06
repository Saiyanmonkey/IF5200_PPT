import os
import random
import sys
import time

from dotenv import load_dotenv
import neo4j

from backend.app.recommendation.fetchers import JobstreetFetcher
from backend.app.recommendation.llm import init_gemini_skill_extraction_pipeline
from backend.app.recommendation.optimizers import FangCollaborativeOptimizer
from backend.app.recommendation.scorers import FangCollaborativeScorer, FangContentBasedScorer, FangScorer, FangVacancyScorer
from backend.app.recommendation.service import RecommendationService
from backend.app.recommendation.updaters import FangCollaborativeOptimizerUpdater, FangVacancyScorerUpdater, JobstreetVacancyUpdater
from backend.app.repositories import CompanyRepository, ConfigRepository, FangCollaborativeParameterRepository, SkillRepository, UserRepository, VacancyRepository

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
        skills=skills
    )

def init():
    load_dotenv()
    CONFIG_ID = 120

    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://xxxxx.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your-password-here")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

    driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    user_repo = UserRepository(driver=driver, database=NEO4J_DATABASE)
    vacancy_repo = VacancyRepository(driver=driver, database=NEO4J_DATABASE)
    fang_repo = FangCollaborativeParameterRepository(driver=driver, config_id=CONFIG_ID, database=NEO4J_DATABASE)
    config_repo = ConfigRepository(driver=driver, config_id=CONFIG_ID, database=NEO4J_DATABASE)
    company_repo = CompanyRepository(driver=driver, database=NEO4J_DATABASE)
    skill_repo = SkillRepository(driver=driver, database=NEO4J_DATABASE)

    service = RecommendationService(user_repository=user_repo, vacancy_repository=vacancy_repo)

    collaborative_scorer = FangCollaborativeScorer(fang_repo)
    content_based_scorer = FangContentBasedScorer(user_repo, config_repo)
    scorer = FangScorer(collaborative_scorer, content_based_scorer)
    vacancy_scorer = FangVacancyScorer(scorer, vacancy_repo)
    scorer_updater = FangVacancyScorerUpdater(vacancy_scorer, user_repo, vacancy_repo)

    optimizer = FangCollaborativeOptimizer(fang_repo, user_repo, config_repo)
    optimizer_updater = FangCollaborativeOptimizerUpdater(user_repo, config_repo, optimizer, shuffle=True)

    jobstreet_fetcher = JobstreetFetcher()
    skill_pipeline = prepare_llm_pipeline(skill_repo)
    def skill_fn(x) -> list[str]:
        print(f"Prompt: {x}")
        print("Wait 10 seconds .... (to avoid rate limit)")
        time.sleep(5)
        print("Let's go.")
        y_list = skill_pipeline([x])
        if y_list is None or len(y_list) == 0:
            print(f"No result.")
            return []
        else:
            print(f"Result: {y_list[0]}")
            return y_list[0]

    vacancy_updater = JobstreetVacancyUpdater(company_repo, jobstreet_fetcher, skill_fn, verbose = True)


    return (
        service,           # Ini hubungkan ke API
        scorer_updater,    # Ini jalankan di background untuk interval fixed (misalkan per 1 menit)
        optimizer_updater, # Ini juga jalankan di background untuk interval fixed
        vacancy_updater,   # Jalankan hanya sekali (atau 1 kali per hari)
    )

if __name__ == "__main__":
    print("Initializing ....")
    random.seed(120)
    _, scorer_updater, optimizer_updater, vacancy_updater = init()
    print("Initialized! (Ctrl+C to exit)")

    if "vacancy_only" in sys.argv:
        vacancy_updater.update()
        exit()

    optimizer_only = "optimizer_only" in sys.argv
    scorer_only = "scorer_only" in sys.argv
    
    stop = False
    while not stop:
        try:
            if not optimizer_only:
                print("Score update ....")
                start_time = time.time()
                scorer_updater.update()
                print(f"(Duration: {time.time() - start_time} s)")
                print("Wait 10 seconds ....")
                time.sleep(10)

            if not scorer_only:
                print("Optimization update ....")
                start_time = time.time()
                optimizer_updater.update()
                print(f"(Duration: {time.time() - start_time} s)")
                print("Wait 10 seconds ....")
                time.sleep(10)
            
            print("---")
        except KeyboardInterrupt:
            print("Interruption detected.")
            stop = True
