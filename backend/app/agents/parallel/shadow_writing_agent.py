# shadow_writing_agent.py
# 并行处理的Shadow Writing Agent

from app.state import ChunkProcessState


def shadow_writing_single_chunk(state: ChunkProcessState) -> dict:
    """
    处理单个语义块的Shadow Writing（并行版本）

    【重要】：移除 time.sleep(15) 强制等待
    LangGraph的并发控制 + API Key轮换机制已足够

    【Prompt保持不变】：使用与原版完全相同的Shadow Writing prompt
    """
    chunk_text = state.get("chunk_text", "")
    chunk_id = state.get("chunk_id", 0)
    task_id = state.get("task_id")
    total_chunks = state.get("total_chunks", 1)

    print(f"\n[Pipeline {chunk_id}] Shadow Writing...")
    print(f"[Pipeline {chunk_id}] task_id: {task_id}, chunk_length: {len(chunk_text)}, total_chunks: {total_chunks}")

    if not chunk_text:
        return {"raw_shadow": None, "error": "Empty chunk"}
    
    try:
        # 使用 LLM Service 获取 LLM
        from app.services.llm import get_llm_service
        llm_service = get_llm_service()
        llm = llm_service.create_shadow_writing_llm()
        
        output_format = {
            "original": "完整原句, str",
            "imitation": "把原句话题换成任意话题的完整新句（≥12词）, str", 
            "map": "词汇映射字典，键为原词，值为同义词列表, dict"
        }
        
        # 【完全相同的Shadow Writing prompt - 不做任何修改】
        shadow_prompt = f"""

You are a Shadow Writing Coach, an expert in teaching authentic English expression through structural imitation.

# What is Shadow Writing?
Shadow Writing is a Western linguistic teaching method where learners find authentic English texts, imitate their sentence structures and logic while changing the content, then compare with the original. Unlike template filling (套模板), which mechanically reuses fixed phrases, Shadow Writing helps you internalize language patterns by "standing in the author's shadow" - experiencing how native speakers build sentences and organize logic.

# Why It Works
This method combines three key SLA theories:
1. **Krashen's Input Hypothesis**: Comprehensible input from authentic texts
2. **Swain's Output Hypothesis**: Active production forces you to notice gaps
3. **Schmidt's Noticing Hypothesis**: Comparison makes you aware of language forms

# Shadow Writing vs Template Filling (影子写作 vs 套模板)
**Template Filling (套模板)** - Mechanical substitution:
- "There are many reasons for this phenomenon..."
- Same fixed phrases for ANY topic
- Feels awkward and unnatural

**Shadow Writing (影子写作)** - Standing in the author's shadow:
- Learn HOW authors build sentences
- Internalize logical frameworks
- Migrate structure to NEW contexts naturally

You are NOT copying templates. You are learning to "tailor language" by experiencing the author's craftsmanship.

# Two Complete Examples

## Example 1: Daily Life Scene
**Original:**
"Every morning, I take a short walk around my neighborhood. The air feels fresh, and the quiet streets give me time to clear my mind."

**Shadow Writing (话题迁移):**
"Every evening, I spend half an hour reading in my living room. The warm light makes the space calm, and the silence helps me forget the noise of the day."

**What Changed (迁移点):**
- Time: morning → evening
- Action: take a short walk → spend half an hour reading
- Place: neighborhood → living room
- Atmosphere: air feels fresh / quiet streets → warm light / silence
- Mental_State: clear my mind → forget the noise of the day

**What Stayed (骨架):**
- Grammar: "Every [time], I [action] [location]. The [description], and the [description] [mental effect]."
- Logic: Time → Action → Setting → Atmosphere → Reflection

**JSON Output:**
{{{{
  "original": "Every morning, I take a short walk around my neighborhood. The air feels fresh, and the quiet streets give me time to clear my mind.",
  "imitation": "Every evening, I spend half an hour reading in my living room. The warm light makes the space calm, and the silence helps me forget the noise of the day.",
  "map": {{{{
    "Time": ["morning", "evening"],
    "Action": ["take a short walk", "spend half an hour reading"],
    "Place": ["neighborhood", "living room"],
    "Atmosphere": ["air feels fresh / quiet streets", "warm light / silence"],
    "Mental_State": ["clear my mind", "forget the noise of the day"]
  }}}}
}}}}

---

## Example 2: News Report
**Original:**
"The city opened a new public library this week. The modern building offers more than just books—it has study rooms, a café, and free internet access. Officials say the library will give residents more opportunities to learn and connect with each other."

**Shadow Writing (话题迁移):**
"The town opened a new sports center this month. The bright facility offers more than just courts—it has a gym, a swimming pool, and free fitness classes. Coaches say the center will give young people more chances to train and build friendships."

**What Changed (迁移点):**
- Location: city → town
- Facility: public library → sports center
- Time: this week → this month
- Description: modern building → bright facility
- Main_Feature: books → courts
- Additional_Features: study rooms / café / internet → gym / pool / fitness classes
- Authority_Figure: officials → coaches
- Target_Audience: residents → young people
- Purpose: learn and connect → train and build friendships

**What Stayed (骨架):**
- Grammar: "[Place] opened [facility] [time]. The [adjective] [noun] offers more than just [X]—it has [A], [B], and [C]. [Authority] say [it] will give [audience] more [opportunities/chances] to [verb] and [verb]."
- Logic: Announcement → Description → Features → Official Statement → Benefits

**JSON Output:**
{{{{
  "original": "The city opened a new public library this week. The modern building offers more than just books—it has study rooms, a café, and free internet access. Officials say the library will give residents more opportunities to learn and connect with each other.",
  "imitation": "The town opened a new sports center this month. The bright facility offers more than just courts—it has a gym, a swimming pool, and free fitness classes. Coaches say the center will give young people more chances to train and build friendships.",
  "map": {{{{
    "Location": ["city", "town"],
    "Facility": ["public library", "sports center"],
    "Time": ["this week", "this month"],
    "Description": ["modern building", "bright facility"],
    "Main_Feature": ["books", "courts"],
    "Additional_Features": ["study rooms / café / internet", "gym / pool / fitness classes"],
    "Authority_Figure": ["officials", "coaches"],
    "Target_Audience": ["residents", "young people"],
    "Purpose": ["learn and connect", "train and build friendships"]
  }}}}
}}}}

---

**IMPORTANT: Notice the Categories are DIFFERENT!**
- Example 1 (Daily Life) has: Time, Action, Place, Atmosphere, Mental_State
- Example 2 (News Report) has: Location, Facility, Time, Description, Main_Feature, Additional_Features, Authority_Figure, Target_Audience, Purpose

👉 **Your Task: Create YOUR OWN categories based on YOUR extracted sentence!**
- Do NOT copy the categories from these examples
- Analyze what content words changed in YOUR sentence
- Create category names that fit YOUR specific migration
- Different sentence types need different categories

---

# Your Task: Apply Shadow Writing

Text:
{chunk_text}

**Step 1: Find the Skeleton (找骨架)**
- Migrate the entire text chunk while preserving its structure
- Identify its grammar structure and logical flow
- Notice how words are organized

**Step 2: Stand in the Author's Shadow (站在作者影子里)**
- Feel HOW the author builds the sentence
- What logical framework are they using?
- What content words carry the meaning?

**Step 3: Migrate Topic (话题迁移)**
- Keep the EXACT same sentence structure
- Replace ONLY content words with a NEW topic
- Maintain grammar, logic, and flow

**Step 4: Create Word Map (词汇映射)**
- **Analyze YOUR sentence** to identify what types of content changed
- **Create YOUR OWN category labels** that fit YOUR specific sentence
- Each category shows: [original word/phrase, migrated word/phrase]

# Output (JSON only)
{{{{
  "original": "your extracted sentence (≥12 words)",
  "imitation": "your topic-migrated sentence with IDENTICAL structure (≥12 words)",
  "map": {{{{
    "Your_Category_1": ["original_element", "migrated_element"],
    "Your_Category_2": ["original_element", "migrated_element"],
    "Your_Category_3": ["original_element", "migrated_element"]
  }}}}
}}}}

**Key Principles:**
1. You are NOT filling a template—you are learning sentence craftsmanship
2. Stand in the author's shadow: feel their logic, then migrate to new context
3. Grammar structure must be 100% identical
4. Replace content elements (words or phrases):
   - **Single words**: nouns, verbs, adjectives, adverbs
   - **Phrases**: noun phrases, verb phrases, prepositional phrases
   - Examples from above:
     - "public library" → "sports center" (noun phrase)
     - "learn and connect" → "train and build friendships" (verb phrase)
     - "air feels fresh" → "warm light" (descriptive phrase)
   - [WARNING] **Important**: Replacements must be natural English collocations (符合英语表达习惯)
5. Maintain grammatical correctness while keeping sentence structure:
   - Function words (articles, conjunctions) generally stay the same: the, a, and, but
   - BUT make necessary grammar adjustments:
     - **Prepositions**: Must match verb collocations
       Example: "walk around" → "read in" (around→in is necessary)
     - **Verb forms**: Must agree with subject
       Example: "city opens" → "cities open" (singular→plural)
     - **Articles**: May change for grammar
       Example: "a library" → "an auditorium" (a→an before vowel)
   - Core principle: Keep the LOGICAL STRUCTURE, adjust grammar for correctness
   - [WARNING] Don't change structure-defining words like: not...but, either...or, not only...but also
6. **Create categories dynamically based on YOUR sentence—don't copy from examples**
7. Map at least 4-8 key content transformations

Now extract ONE sentence and perform Shadow Writing migration.

"""
        
        # 直接调用LLM，不再强制等待
        print(f"[Pipeline {chunk_id}] 调用 llm()...")
        result = llm(shadow_prompt, output_format)
        print(f"[Pipeline {chunk_id}] LLM返回类型: {type(result)}")
        print(f"[Pipeline {chunk_id}] LLM返回内容: {result}")
        
        if result and isinstance(result, dict):
            # 标准化结果（添加paragraph字段）
            standardized_result = {
                'original': str(result.get('original', '')).strip(),
                'imitation': str(result.get('imitation', '')).strip(),
                'map': result.get('map', {}),
                'paragraph': chunk_text
            }

            # 成功后更新数据库进度
            if task_id and total_chunks > 0:
                try:
                    from app.db import task_db
                    task_db.increment_completed_chunk(task_id)
                    print(f"[Pipeline {chunk_id}] 更新完成数: {chunk_id + 1}/{total_chunks}")
                except Exception as e:
                    print(f"[Pipeline {chunk_id}] 更新数据库失败: {e}")

            print(f"[Pipeline {chunk_id}] [OK] Shadow Writing完成")
            print(f"   原句: {standardized_result['original'][:60]}...")

            return {"raw_shadow": standardized_result}
        else:
            print(f"[Pipeline {chunk_id}] [ERROR] LLM返回无效结果")
            return {"raw_shadow": None, "error": "Invalid LLM response"}
        
    except Exception as e:
        print(f"[Pipeline {chunk_id}] [ERROR] Shadow Writing失败: {e}")
        return {"raw_shadow": None, "error": str(e)}
