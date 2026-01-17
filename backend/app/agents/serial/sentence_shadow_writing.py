from app.state import Shadow_Writing_State
from app.utils import ensure_dependencies, create_llm_function_native
import time

def TED_shadow_writing_agent(state: Shadow_Writing_State) -> Shadow_Writing_State:
    """TED句子迁移节点"""
    # 从 state 获取语义块
    semantic_chunks = state.get("semantic_chunks", [])
    
    # 处理所有语义块（已启用多API Key轮换，可安全处理大量数据）
    chunks_to_process = semantic_chunks
    
    print(f"\n [SHADOW WRITING NODE] 开始处理 {len(chunks_to_process)} 个语义块")
    print("   多API Key轮换已启用，可处理完整文本")
      
    if not chunks_to_process:
        return {
            "raw_shadows_chunks": [],
            "errors": ["Shadow Writing节点: 无语义块可处理"]
        }
    
    try:
        ensure_dependencies()
        llm_function = create_llm_function_native()
        
        all_results = []
        
        output_format = {
            "original": "完整原句, str",
            "imitation": "把原句话题换成任意话题的完整新句（≥12词）, str", 
            "map": "词汇映射字典，键为原词，值为同义词列表, dict"
        }
        
        # 遍历每个语义块（带速率限制处理）
        for i, chunk_text in enumerate(chunks_to_process, 1):
            print(f"\n处理语义块 [{i}/{len(chunks_to_process)}]...")
            
            # 添加延迟以避免速率限制（除了第一个块）
            if i > 1:
                delay = 15  # 等待15秒让速率限制重置
                print(f"   等待 {delay} 秒以避免速率限制...")
                time.sleep(delay)
            
            try:
                # Shadow Writing prompt
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
{{
  "original": "Every morning, I take a short walk around my neighborhood. The air feels fresh, and the quiet streets give me time to clear my mind.",
  "imitation": "Every evening, I spend half an hour reading in my living room. The warm light makes the space calm, and the silence helps me forget the noise of the day.",
  "map": {{
    "Time": ["morning", "evening"],
    "Action": ["take a short walk", "spend half an hour reading"],
    "Place": ["neighborhood", "living room"],
    "Atmosphere": ["air feels fresh / quiet streets", "warm light / silence"],
    "Mental_State": ["clear my mind", "forget the noise of the day"]
  }}
}}

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
{{
  "original": "The city opened a new public library this week. The modern building offers more than just books—it has study rooms, a café, and free internet access. Officials say the library will give residents more opportunities to learn and connect with each other.",
  "imitation": "The town opened a new sports center this month. The bright facility offers more than just courts—it has a gym, a swimming pool, and free fitness classes. Coaches say the center will give young people more chances to train and build friendships.",
  "map": {{
    "Location": ["city", "town"],
    "Facility": ["public library", "sports center"],
    "Time": ["this week", "this month"],
    "Description": ["modern building", "bright facility"],
    "Main_Feature": ["books", "courts"],
    "Additional_Features": ["study rooms / café / internet", "gym / pool / fitness classes"],
    "Authority_Figure": ["officials", "coaches"],
    "Target_Audience": ["residents", "young people"],
    "Purpose": ["learn and connect", "train and build friendships"]
  }}
}}

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
{{
  "original": "your extracted sentence (≥12 words)",
  "imitation": "your topic-migrated sentence with IDENTICAL structure (≥12 words)",
  "map": {{
    "Your_Category_1": ["original_element", "migrated_element"],
    "Your_Category_2": ["original_element", "migrated_element"],
    "Your_Category_3": ["original_element", "migrated_element"]
  }}
}}

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
        
                result = llm_function(shadow_prompt, output_format)
                
                if result and isinstance(result, dict):
                    # 标准化结果
                    standardized_result = {
                        'original': str(result.get('original', '')).strip(),
                        'imitation': str(result.get('imitation', '')).strip(),
                        'map': result.get('map', {}),
                        'paragraph': chunk_text
                    }
                    
                    # 格式化显示提取结果
                    print("[SUCCESS] [TEDTAILOR] 成功迁移:")
                    print(f"   原句: {standardized_result['original']}")
                    print(f"   迁移: {standardized_result['imitation']}")
                    print(f"   映射: {len(standardized_result['map'])} 个词汇")
                    print(f"   详细映射: {standardized_result['map']}")
                    
                    all_results.append(standardized_result)
                else:
                    print(f"[SKIP] 语义块 {i}: LLM返回无效结果")
                    
            except Exception as e:
                print(f"[ERROR] 语义块 {i} 处理失败: {e}")
                continue
        
        print(f"\n[SHADOW WRITING] 完成处理，成功生成 {len(all_results)}/{len(semantic_chunks)} 个结果")
        
        return {
            "raw_shadows_chunks": all_results,
            "processing_logs": [f"TED迁移节点: 成功迁移 {len(all_results)} 个句子"]
        }
            
    except Exception as e:
        return {
            "raw_shadows_chunks": [],
            "errors": [f"Shadow Writing节点出错: {e}"]
        }