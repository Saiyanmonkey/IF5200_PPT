from itertools import product
import random
import time
from typing import Callable

from tqdm import tqdm

from backend.app.recommendation.fetchers import JobstreetFetcher
from backend.app.recommendation.optimizers import FangCollaborativeOptimizer
from backend.app.recommendation.scorers import FangVacancyScorer
from backend.app.repositories import CompanyRepository, ConfigRepository, UserRepository, VacancyRepository

class FangCollaborativeOptimizerUpdater:
    def __init__(
            self,
            user_repository: UserRepository,
            config_repository: ConfigRepository,
            collaborative_optimizer: FangCollaborativeOptimizer,
            verbose: bool = True,
            shuffle: bool = False
    ):
        self.user_repository = user_repository
        self.config_repository = config_repository
        self.collaborative_optimizer = collaborative_optimizer
        self.verbose = verbose
        self.shuffle = shuffle

    def update(self) -> None:
        user_ids = self.user_repository.get_all_user_ids()
        if len(user_ids) == 0:
            return
        
        max_train_error = self.config_repository.get_fang_max_train_error()
        max_train_steps = self.config_repository.get_fang_max_train_steps()

        user_count = len(user_ids)
        MAX_USER = 5
        if user_count > min(max_train_steps, MAX_USER):
            print(f"Warning: sampling is used because there are {user_count} user(s)")
            user_ids = random.sample(user_ids, k=min(max_train_steps, MAX_USER))
        elif self.shuffle:
            random.shuffle(user_ids)

        stop = False
        target_streak = len(user_ids)
        current_streak = 0
        step = 0

        pbar = tqdm(total=max_train_steps)

        if self.verbose:
            print("Start")
        start_time = time.time()
        while not stop:
            step += 1
            id = user_ids.pop(0)
            self.collaborative_optimizer.optimize(id)
            last_error = self.collaborative_optimizer.get_last_error()
            if last_error <= max_train_error:
                current_streak += 1
            else:
                current_streak = 0

            if self.verbose:
                current_time = time.time() - start_time
                print(id, f"{last_error=}", f"{current_streak=}", f"{current_time=}", sep="\t")

            pbar.update()

            if target_streak == current_streak or step == max_train_steps:
                pbar.close()
                stop = True
            else:
                user_ids.append(id)

        if self.verbose:
            current_time = time.time() - start_time
            print("Stop", f"{current_time=}", sep="\t")

class FangVacancyScorerUpdater:
    def __init__(
            self,
            scorer: FangVacancyScorer,
            user_repository: UserRepository,
            vacancy_repository: VacancyRepository,
            verbose=True,
    ):
        self.scorer = scorer
        self.user_repo = user_repository
        self.vacancy_repo = vacancy_repository
        self.verbose = verbose

    def update(self):
        user_id_list = self.user_repo.get_all_user_ids()
        vacancy_id_list = self.vacancy_repo.get_all_vacancy_ids()

        # Filter for the sake of easiness
        user_count = len(user_id_list)
        vacancy_count = len(vacancy_id_list)
        if user_count >= 10:
            if self.verbose:
                print(f"Warning: User is sampled because it's too many ({user_count})")
            user_id_list = random.sample(user_id_list, k=10)

        if vacancy_count >= 10:
            if self.verbose:
                print(f"Warning: Vacancy is sampled because it's too many ({vacancy_count})")
            vacancy_id_list = random.sample(vacancy_id_list, k=10)

        for user_id, vacancy_id in tqdm(product(user_id_list, vacancy_id_list), total=len(user_id_list) * len(vacancy_id_list)):
            score = self.scorer.get_score(user_id, vacancy_id)
            self.user_repo.set_vacancy_score(user_id, vacancy_id, score)

class JobstreetVacancyUpdater:
    def __init__(
            self,
            company_repository: CompanyRepository,
            jobstreet_fetcher: JobstreetFetcher,
            skill_fn: Callable[[str], list[str]],
            verbose: bool = False
    ):
        self.company_repo = company_repository
        self.fetcher = jobstreet_fetcher
        self.skill_fn = skill_fn
        self.verbose = verbose

    def update(self):
        # skipping = True
        for x in tqdm(self.company_repo.get_all()):
            if self.verbose:
                print("Company:", x)
            
            company_id = x["id"]
            company_name = x["name"]
            jobstreet_id = x["jobstreet_id"]
            
            # if company_name != "Blibli" and skipping:
            #     print(f"Skipping {company_name}")
            #     continue

            if jobstreet_id is None:
                if self.verbose:
                    print("Jobstreet ID not found. Finding ....")

                jobstreet_id = self.fetcher.find_company_id(company_name)
                if self.verbose:
                    print(f"Found: {jobstreet_id}")

                if jobstreet_id is None:
                    continue

                self.company_repo.set_jobstreet_id(company_id, jobstreet_id)
                if self.verbose:
                    print(f"Jobstreet ID saved.")
            
            if self.verbose:
                print(f"Find vacancies ....")
            vacancies = self.fetcher.get_vacancies_from_company_id(jobstreet_id)
            # Should be merged to make LLM efficient, but ... never mind.
            new_vacancies = []
            for v in vacancies:
                if self.verbose:
                    print(f"Vacancy: {v}")
                url = v["url"]
                if self.verbose:
                    print(f"Find description ....")
                description = self.fetcher.get_vacancy_description(url)
                if self.verbose:
                    print(f"Description: {description}")
                if description is None:
                    print("Warning: no description detected")
                    description = v["name"]
                else:
                    description = v["name"] + "\n\n" + description

                if self.verbose:
                    print(f"Find skills ....")
                skills = self.skill_fn(description)
                if self.verbose:
                    print(f"Skills: {skills}")
                new_vacancies.append({
                    "description": description,
                    "source_url": url,
                    "skills": skills
                })

            self.company_repo.set_vacancies(company_id, new_vacancies)
