# quality_agent.py
# 并行处理的Quality Check Agent

from app.state import ChunkProcessState


def quality_single_chunk(state: ChunkProcessState) -> dict:
    """质量评估单个Chunk（并行版本）"""
    chunk_id = state.get("chunk_id", 0)
    task_id = state.get("task_id")
    total_chunks = state.get("total_chunks", 1)
    validated = state.get("validated_shadow")

    print(f"[Pipeline {chunk_id}] Quality Check...")

    if not validated:
        return {"quality_passed": False, "quality_score": 0.0}

    try:
        # 使用 LLM Service 获取 LLM
        from app.services.llm import get_llm_service
        llm_service = get_llm_service()
        llm = llm_service.create_quality_llm()

        # 获取验证通过的Shadow数据
        original = validated.original
        imitation = validated.imitation
        word_map = validated.map
        paragraph = validated.paragraph

        # 基于Sub-CoT的TED迁移质量评估prompt（强化逻辑检查）
        quality_prompt = f"""
You are a Shadow Writing Quality Evaluator. You understand that Shadow Writing is NOT template filling, but learning sentence craftsmanship by "standing in the author's shadow."

ORIGINAL SENTENCE: "{original}"
MIGRATED SENTENCE: "{imitation}"
WORD MAPPING: {word_map}
SOURCE PARAGRAPH: "{paragraph[:200]}..."

Evaluate this Shadow Writing attempt with DETAILED step-by-step analysis:

<thinking>
STEP 1: Grammar Structure Preservation (0-3 points) 【骨架保持】

Sub-step 1.1 - Identify Original Structure:
- Sentence pattern: [describe: SVO / clauses / complex structure]
- Main clause(s): [identify]
- Subordinate clause(s): [identify if any]
- Key conjunctions/connectors: [list]

Sub-step 1.2 - Identify Migrated Structure:
- Sentence pattern: [describe: SVO / clauses / complex structure]
- Main clause(s): [identify]
- Subordinate clause(s): [identify if any]
- Key conjunctions/connectors: [list]

Sub-step 1.3 - Structure Comparison:
- Are they IDENTICAL? [yes/no]
- If no, list differences: [describe each structural deviation]
- Number of deviations: [0 / 1-2 / 3+]

Sub-step 1.4 - Calculate Score:
- 0 deviations → 3 points (Perfect match)
- 1-2 minor deviations → 2 points
- 3+ or significant changes → 1 point
- Completely different → 0 points
Step 1 Score: [0-3]

STEP 2: Content Word/Phrase Replacement Quality (0-2 points) 【内容替换】

Sub-step 2.1 - List All Replacements:
- Replacement 1: [original word/phrase] → [migrated word/phrase]
- Replacement 2: [original word/phrase] → [migrated word/phrase]
- ... (list all content word changes)

Sub-step 2.2 - Check Each Replacement:
For EACH replacement above, answer:
- Is it a natural English collocation? [yes/no]
- Does it maintain the same grammatical function? [yes/no]
- Example: noun→noun, verb phrase→verb phrase, adjective→adjective

Sub-step 2.3 - Function Words Check:
- Were function words (prepositions, articles, verb forms) properly adjusted? [yes/no]
- Examples of adjustments: [list if any]

Sub-step 2.4 - Calculate Score:
- ALL replacements natural + function words adjusted → 2 points
- Most replacements work, 1-2 minor issues → 1 point
- Unnatural/grammatically incorrect → 0 points
Step 2 Score: [0-2]

STEP 3: Semantic Plausibility & Logic (0-3 points) 【语义合理性 - CRITICAL】

[WARNING] CRITICAL CHECK - Examine CAREFULLY for logical contradictions

Sub-step 3.1 - Time Sequence Logic (时间序列逻辑):
Question: Does the timeline make sense?
- Original time elements: [identify: when, how long, sequence]
- Migrated time elements: [identify: when, how long, sequence]
- Analysis: [Describe the time flow in both sentences]
- Check for timing conflicts:
  * Are there "already X" → "will be Y" contradictions? [yes/no + explain]
  * Are there improper tense uses? [yes/no + explain]
  * Example issue: "infected" (already) → "will be hospitalized" (future) [ERROR]
  * Example correct: "in critical condition" → "will die" [OK]
- Sub-result: [OK / ISSUE + explain]

Sub-step 3.2 - Cause-Effect Logic (因果关系):
Question: Do the cause-effect relationships make sense?
- Original: IF [cause] THEN [effect] → [identify both]
- Migrated: IF [cause] THEN [effect] → [identify both]
- Are they logically parallel?
- Check for illogical relationships:
  * Does "no treatment" lead to logical consequence? [yes/no + explain]
  * Example issue: "no treatment" → "will be hospitalized" [ERROR] (illogical)
  * Example correct: "no treatment" → "will die/deteriorate" [OK] (logical)
- Sub-result: [OK / ISSUE + explain]

Sub-step 3.3 - Severity Matching (严重性匹配):
Question: Do the consequences match in severity?
- Original consequence: [identify] → Severity level: [low/medium/high/death]
- Migrated consequence: [identify] → Severity level: [low/medium/high/death]
- Are they comparable in severity? [yes/no + explain]
- Check for severity mismatches:
  * Example issue: "executed" (death) → "hospitalized" (treatment) [ERROR]
  * Example correct: "executed" → "die/killed" [OK]
  * Example correct: "injured" → "wounded" [OK]
- Sub-result: [OK / ISSUE + explain]

Sub-step 3.4 - Real-World Believability (现实可信度):
Question: Is the migrated sentence believable in the real world?
- Does the scenario make practical sense? [yes/no + explain]
- Are there any absurd or nonsensical elements? [yes/no + list]
- Would this happen in reality? [yes/no + reason]
- Sub-result: [OK / ISSUE + explain]

Sub-step 3.5 - Overall Logic Summary:
- Total issues found: [count from 3.1-3.4]
- Critical issues (major contradictions): [list]
- Minor issues (acceptable): [list]

Sub-step 3.6 - Calculate Score:
- 0 issues found → 3 points (Perfectly logical)
- 1 minor issue only → 2 points (Mostly logical)
- 1 critical issue OR 2+ minor issues → 1 point (Problematic)
- 2+ critical issues → 0 points (Illogical)
Step 3 Score: [0-3]

STEP 4: Topic Migration Success (0-2 points) 【话题迁移】

Sub-step 4.1 - Topic Identification:
- Original topic/domain: [identify clearly]
- Migrated topic/domain: [identify clearly]
- Topic change: [original] → [migrated]

Sub-step 4.2 - Migration Quality:
- Is the topic change clear and obvious? [yes/no]
- Is the new topic coherent and meaningful? [yes/no]
- Does it feel like Shadow Writing or just template filling? [Shadow/Template + reason]

Sub-step 4.3 - Calculate Score:
- Clear, meaningful migration + Shadow Writing feel → 2 points
- Weak or unclear topic change → 1 point
- No real migration or template filling → 0 points
Step 4 Score: [0-2]

STEP 5: Learning Value (0-1 points) 【学习价值】

- Can English learners benefit from this migration? [yes/no + explain]
- Does it demonstrate a useful, reusable sentence pattern? [yes/no]
- Is it practical and applicable to real communication? [yes/no]
Step 5 Score: [0-1]

STEP 6: FINAL ASSESSMENT

Total Score Calculation:
- Step 1 (Grammar): [score]/3
- Step 2 (Content): [score]/2
- Step 3 (Logic): [score]/3
- Step 4 (Topic): [score]/2
- Step 5 (Learning): [score]/1
- TOTAL: [sum]/11

Pass Threshold: ≥9 points (AND Logic must be ≥2/3)

Final Judgment:
- Does this PASS quality standards? [yes/no]
- Key Strengths: [list what was done well]
- Key Issues: [list problems, especially from Step 3]
- Overall Assessment: [Shadow Writing OR Template Filling]
</thinking>

Based on the detailed analysis above, provide your evaluation in JSON format:

{{
  "step1_grammar": <0-3>,
  "step2_content": <0-2>,
  "step3_logic": <0-3>,
  "step3_issues": ["list of critical logical issues found, or empty array if none"],
  "step4_topic": <0-2>,
  "step5_learning": <0-1>,
  "total_score": <0-11>,
  "pass": <true/false>,
  "reasoning": "<brief summary focusing on Step 3 logic check>"
}}

JSON:"""

        evaluation_format = {
            "step1_grammar": "Grammar structure score 0-3, int",
            "step2_content": "Content replacement score 0-2, int",
            "step3_logic": "Logic & plausibility score 0-3, int",
            "step3_issues": "Array of critical logical issues, list of str",
            "step4_topic": "Topic migration score 0-2, int",
            "step5_learning": "Learning value score 0-1, int",
            "total_score": "Sum of all scores 0-11, int",
            "pass": "true if score >= 9 AND step3_logic >= 2, bool",
            "reasoning": "Summary of evaluation, str"
        }

        result = llm(quality_prompt, evaluation_format)

        if result and isinstance(result, dict):
            # 处理基于Sub-CoT的TED迁移质量评估结果
            total_score = float(result.get('total_score', 0))
            step3_logic = result.get('step3_logic', 0)
            step3_issues = result.get('step3_issues', [])
            reasoning = result.get('reasoning', '')
            is_pass = result.get('pass', False)

            # 通过标准：总分≥9 且 pass=true
            is_valid = total_score >= 9.0 and is_pass

            # ⛔ 逻辑硬性否决规则：Logic < 2/3 强制不通过
            if step3_logic < 2:
                is_valid = False
                logic_veto = True
            else:
                logic_veto = False

            if is_valid:
                print(f"[PASS] [QUALITY] 通过 (分数: {total_score}/11):")
                print(f"   原句: {original}")
                print(f"   迁移: {imitation}")
                print(f"   评分细节: Grammar={result.get('step1_grammar')}/3, Content={result.get('step2_content')}/2, Logic={step3_logic}/3, Topic={result.get('step4_topic')}/2, Learning={result.get('step5_learning')}/1")
                if step3_issues:
                    print(f"   [WARNING] 逻辑问题: {', '.join(step3_issues)}")
                print(f"   推理: {reasoning}")
                # 保存详细的质量分数
                quality_details = {
                    'step1_grammar': result.get('step1_grammar'),
                    'step2_content': result.get('step2_content'),
                    'step3_logic': step3_logic,
                    'step3_issues': step3_issues,
                    'step4_topic': result.get('step4_topic'),
                    'step5_learning': result.get('step5_learning')
                }
                status = "[OK]"
            else:
                print(f"[FAIL] [QUALITY] 不通过 (分数: {total_score}/11):")
                print(f"   原句: {original}")
                print(f"   迁移: {imitation}")
                print(f"   评分细节: Grammar={result.get('step1_grammar')}/3, Content={result.get('step2_content')}/2, Logic={step3_logic}/3, Topic={result.get('step4_topic')}/2, Learning={result.get('step5_learning')}/1")
                if logic_veto:
                    print(f"    逻辑硬性否决: Logic={step3_logic}/3 < 2 (有严重逻辑问题)")
                if step3_issues:
                    print(f"    逻辑问题: {', '.join(step3_issues)}")
                print(f"   推理: {reasoning}")
                # 保存详细的质量分数
                quality_details = {
                    'step1_grammar': result.get('step1_grammar'),
                    'step2_content': result.get('step2_content'),
                    'step3_logic': step3_logic,
                    'step3_issues': step3_issues,
                    'step4_topic': result.get('step4_topic'),
                    'step5_learning': result.get('step5_learning')
                }
                status = "[ERROR]"

            print(f"[Pipeline {chunk_id}] {status} Quality: {total_score}/11")

            return {
                "quality_passed": is_valid,
                "quality_score": total_score,
                "quality_detail": quality_details,
                "quality_reasoning": reasoning,
                "logic_veto": logic_veto if not is_valid else False
            }

        else:
            print(f"[Pipeline {chunk_id}] [ERROR] Quality评估失败: 无效的LLM响应")
            return {"quality_passed": False, "quality_score": 0.0, "error": "无效的LLM响应"}

    except Exception as e:
        print(f"[Pipeline {chunk_id}] [ERROR] Quality失败: {e}")
        return {"quality_passed": False, "quality_score": 0.0, "error": str(e)}
