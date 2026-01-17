from app.state import Shadow_Writing_State
from app.utils import ensure_dependencies, create_llm_function_native

def correction_agent(state: Shadow_Writing_State) -> Shadow_Writing_State:
    """修正节点 - 重写低质量语块"""
    # 从 failed_quality_chunks 读取失败的语块（包含详细评分）
    failed_chunks = state.get("failed_quality_chunks", [])
    
    print("\n[CORRECTION NODE] 修正低质量语块")
    
    if not failed_chunks:
        print("   无需修正的语块")
        return {
            "processing_logs": ["修正节点: 无需修正的语块"]
        }
    
    print(f"   需要修正: {len(failed_chunks)} 个语块")
    rejected_chunks = failed_chunks
    
    corrected_chunks = []
    
    try:
        ensure_dependencies()
        llm_function = create_llm_function_native()
        
        for i, chunk_data in enumerate(rejected_chunks, 1):
            # 适配TED迁移结果格式
            original = chunk_data.get('original', '')
            imitation = chunk_data.get('imitation', '')
            word_map = chunk_data.get('map', {})
            paragraph = chunk_data.get('paragraph', '')
            quality_score = chunk_data.get('quality_score', 0)
            quality_details = chunk_data.get('quality_details', {})
            quality_reasoning = chunk_data.get('quality_reasoning', '')
            logic_veto = chunk_data.get('logic_veto', False)
            
            # 提取详细评分信息
            step1_grammar = quality_details.get('step1_grammar', 0)
            step2_content = quality_details.get('step2_content', 0)
            step3_logic = quality_details.get('step3_logic', 0)
            step3_issues = quality_details.get('step3_issues', [])
            step4_topic = quality_details.get('step4_topic', 0)
            step5_learning = quality_details.get('step5_learning', 0)
            
            # 基于CoT的TED迁移修正prompt
            correct_prompt = f"""
You are a TED sentence migration improvement specialist. Use step-by-step thinking to improve this failed migration.

ORIGINAL SENTENCE: "{original}"
FAILED MIGRATION: "{imitation}"
FAILED WORD MAPPING: {word_map}

QUALITY EVALUATION RESULTS:
- Total Score: {quality_score}/11 (Failed - needs ≥9)
- Detailed Scores:
  * Grammar Structure: {step1_grammar}/3
  * Content Replacement: {step2_content}/2
  * Logic & Plausibility: {step3_logic}/3 {'(CRITICAL FAILURE)' if logic_veto else ''}
  * Topic Migration: {step4_topic}/2
  * Learning Value: {step5_learning}/1

CRITICAL LOGICAL ISSUES:
{chr(10).join('- ' + issue for issue in step3_issues) if step3_issues else '- None'}

QUALITY FEEDBACK: "{quality_reasoning}"

Please think step by step to create an improved migration:

<thinking>
Step 1 - Analyze Quality Feedback:
- Grammar Score: {step1_grammar}/3 - {'GOOD' if step1_grammar >= 2 else 'NEEDS IMPROVEMENT'}
- Content Score: {step2_content}/2 - {'GOOD' if step2_content >= 1 else 'NEEDS IMPROVEMENT'}
- Logic Score: {step3_logic}/3 - {'CRITICAL ISSUE' if step3_logic < 2 else 'ACCEPTABLE'}
- Topic Score: {step4_topic}/2 - {'GOOD' if step4_topic >= 1 else 'NEEDS IMPROVEMENT'}
- Learning Score: {step5_learning}/1 - {'GOOD' if step5_learning >= 1 else 'NEEDS IMPROVEMENT'}

Focus on the LOWEST scoring dimensions, especially Logic if < 2/3

Step 2 - Identify Root Problems Based on Scores:
- Logic problems ({step3_logic}/3): {chr(10).join(step3_issues) if step3_issues else 'Check time sequence, cause-effect, severity matching'}
- Grammar problems ({step1_grammar}/3): [analyze if structure preservation failed]
- Content problems ({step2_content}/2): [check if word replacements were unnatural]
- Topic problems ({step4_topic}/2): [check if topic migration was unclear]
- Learning problems ({step5_learning}/1): [check if pattern is not useful]
  
Step 3 - Plan Improvements (Focus on Failed Dimensions):
PRIORITY: Fix Logic issues first if step3_logic < 2!
- If Logic failed: Fix time sequence, cause-effect, severity matching
  * Ensure consequences match severity (death→death, injury→injury)
  * Check "already X" doesn't lead to "will be Y"
  * Verify cause-effect is logical
- If Grammar failed: Preserve sentence structure better
- If Content failed: Use more natural collocations
- If Topic failed: Choose clearer domain migration
- If Learning failed: Make pattern more useful/reusable

Step 4 - Create Improved Migration:
- Write NEW migrated sentence addressing ALL issues above
- Provide improved word mapping with 2-3 alternatives each
- Verify: Logic [OK], Grammar [OK], Content [OK], Topic [OK], Learning [OK]
</thinking>

Based on my analysis above, here is the improved migration that addresses the failed dimensions:

{{"original": "{original}", "imitation": "<improved_migrated_sentence>", "map": {{"word1": ["alt1", "alt2", "alt3"], "word2": ["alt1", "alt2", "alt3"]}}}}

JSON:"""
            
            correction_format = {
                "original": "Original sentence, str",
                "imitation": "Improved migrated sentence, str",
                "map": "Improved word mapping dictionary, dict"
            }
            
            try:
                result = llm_function(correct_prompt, correction_format)
                
                if result and isinstance(result, dict):
                    # 处理TED迁移修正结果
                    corrected_data = {
                        'original': str(result.get('original', original)).strip(),
                        'imitation': str(result.get('imitation', '')).strip(),
                        'map': result.get('map', {}),
                        'paragraph': paragraph
                    }
                    
                    # 验证修正结果
                    improved_imitation = corrected_data['imitation']
                    if (improved_imitation and 
                        len(improved_imitation.split()) >= 8 and
                        isinstance(corrected_data['map'], dict) and
                        len(corrected_data['map']) >= 2):
                        print("[SUCCESS] [CORRECTION] 修正成功:")
                        print(f"   原句: {original}")
                        print(f"   改进: {improved_imitation}")
                        print(f"   映射: {len(corrected_data['map'])} 个词汇")
                        print(f"   详细映射: {corrected_data['map']}")
                        corrected_chunks.append(corrected_data)
                    else:
                        print("[FAIL] [CORRECTION] 修正失败: 改进句太短或映射不足")
                        
            except Exception:
                continue
        
        return {
            "corrected_shadow_chunks": corrected_chunks,
            "processing_logs": [f"修正节点: 修正了 {len(corrected_chunks)}/{len(rejected_chunks)} 个语块"]
        }
        
    except Exception as e:
        return {
            "errors": [f"修正节点出错: {e}"],
            "processing_logs": ["修正节点: 修正过程出错"]
        }
