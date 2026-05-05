import json

from google import genai

def init_gemini_embed_pipeline(api_key: str, model_name: str):
    client = genai.Client(api_key=api_key)

    def f(text: str) -> list[float] | None:
        response = client.models.embed_content(
            model=model_name, 
            contents=text
        )
        embeddings = response.embeddings
        if embeddings is None or embeddings[0].values is None:
            return None
        else:
            return embeddings[0].values

    return f

def init_gemini_skill_extraction_pipeline(
        api_key: str,
        model_name: str,
        skills: list[str],
        verbose: bool = False
):
    client = genai.Client(api_key=api_key)

    prompt = """
You're an assistant who extract skills for each job description. The valid skills are predefined. Here is the list of valid skills (with the IDs):
$SKILLS
    
Analyze the required skills given the job description. Give a response in JSON with this format:
[
  {
    id: int,
    skill_ids: int[]
  }
]
If there any skill with similar names and all relevant, choose all of the IDs.
""".strip()
    
    skill_text_lines = []
    for i, s in enumerate(skills):
        skill_text_lines.append(f"({i}) {s}")
    prompt = prompt.replace("$SKILLS", "\n".join(skill_text_lines))
    if verbose:
        print("System prompt:")
        print(prompt)

    def f(descriptions: list[str]) -> list[list[str]] | None:
        user_prompt_lines = []
        for i, d in enumerate(descriptions):
            user_prompt_lines.append(f"ID: {i}")
            user_prompt_lines.append(f"Description:\n{d}")
            user_prompt_lines.append("")
        user_prompt = "\n".join(user_prompt_lines).strip()
        if verbose:
            print("User prompt: ")
            print(user_prompt)

        response = client.models.generate_content(
            model=model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=prompt, # System Prompt
                thinking_config=genai.types.ThinkingConfig(thinking_level=genai.types.ThinkingLevel.MEDIUM),
                temperature=0.0
            ),
            contents=user_prompt
        )
        x = response.text
        if x is None:
            return None
        
        start_index = x.find("[")
        if start_index == -1:
            return None
        
        end_index = x.rfind("]")
        if end_index == -1:
            return None
        
        raw_result = json.loads(x[start_index:end_index + 1])
        result: list[list[str]] = []
        for x in raw_result:
            selected_skills = [skills[i] for i in x["skill_ids"]]
            result.append(selected_skills)

        return result
    
    return f
