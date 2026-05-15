from datetime import datetime
from typing import Dict, Any,cast

from ..state import StudyFlowState
from ...core.model import get_chat_model
from ...config.logging import get_logger

from langchain.messages import HumanMessage,AIMessage,SystemMessage

logger = get_logger(__name__)


def feedback_node(state:StudyFlowState) -> dict[str,Any]:
    """
    反馈生成节点
    
    功能：
    1. 根据得分生成个性化反馈
    2. 提供学习建议和改进方向
    3. 决定是否需要重新出题（得分低于60分且重试次数<3）
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态字典，包含 feedback 和 should_retry
    """
    logger.info("[Feedback Node] 开始生成反馈")
    
    try:
        score = state.get("score",0)
        score_details = state.get("score_details", {})
        learning_plan = state.get("learning_plan", {})
        retry_count = state.get("retry_count", 0)
        
        logger.info(f"[Feedback Node] 当前得分: {score}, 重试次数: {retry_count}")
        
        model = get_chat_model()
        
        question_scores = cast(dict[str,Any],score_details).get("question_scores", [])
        wrong_questions = [q for q in question_scores if not q["is_correct"]]
        
        
        per_question_review = ""
        if question_scores:
            per_question_review = "\n\n逐题作答记录:\n"
            for index, q in enumerate(question_scores, 1):
                status = "正确" if q["is_correct"] else "需要改进"
                per_question_review += (
                    f"- 第{index}题({status}): "
                    f"学生答案={q['user_answer']}; "
                    f"标准答案={q['correct_answer']}; "
                    f"得分={q['points_earned']}/{q['points_possible']}; "
                    f"评分反馈={q['feedback']}\n"
                )
                
        
         # 生成个性化反馈
        feedback_prompt = f"""作为一位耐心的学习导师，请根据学生的测验结果提供个性化反馈。

                            学习主题: {cast(dict[str,Any],learning_plan).get('topic', '未知')}
                            难度级别: {cast(dict[str,Any],learning_plan).get('difficulty', '未知')}

                            测验结果:
                            - 得分: {score} 分
                            - 答对题数: {cast(dict[str,Any],score_details).get('correct_count', 0)}/{cast(dict[str,Any],score_details).get('total_count', 0)}
                            {per_question_review}

                            请提供:
                            1. 先用2-3句话复盘学生当前理解水平，不要只鼓励。
                            2. 按题指出关键错因：学生答案缺了什么、标准答案为什么成立。
                            3. 给出下一轮作答前最该补的2-3个知识点。
                            4. 如果系统会重新出题，请明确告诉学生下一轮应该重点注意什么。

                            输出要求：
                            - 使用中文。
                            - 保持具体、可操作。
                            - 不要重复原始题目全文。
                            - 总字数控制在350字以内。"""

        logger.info("[Feedback Node] 调用 LLM 生成个性化反馈...")
        response = model.invoke(
            [
                HumanMessage(content=feedback_prompt)
            ]
        )
        
        feedback = response.content
        
        should_retry = cast(int,score) < 60 and retry_count < 3
        
        feedback_message = f"\n\n学习反馈\n\n{feedback}\n\n"
        
        if should_retry:
            feedback_message += f"由于得分未达到60分，系统将基于本轮薄弱点重新生成练习题。（第 {retry_count + 1} 次重试）\n"
            feedback_message += "下一轮请优先修正上面逐题复盘中标出的概念缺口。"
        elif retry_count >= 3:
            feedback_message += "你已经尝试了3次，建议先回顾学习资料，重点补齐本轮复盘中反复出现的知识点后再继续。"
        else:
            feedback_message += "本轮已通过。你可以继续输入新的学习目标，或围绕当前主题提出更深入的问题。"
            
        
        new_retry_count = retry_count + 1 if should_retry else retry_count
        
        logger.info(f"[Feedback Node] should_retry={should_retry}, new_retry_count={new_retry_count}")
        
        return {
            "feedback": feedback_message,
            "should_retry": should_retry,
            "retry_count": new_retry_count,
            "messages":[AIMessage(content=feedback_message)],
            "current_step":"feedback",
            "update_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"[Feedback Node] 生成反馈失败: {str(e)}", exc_info=True)
        return {
            "error": f"反馈生成失败: {str(e)}",
            "error_node": "feedback",
            "current_step": "feedback_error",
            "updated_at": datetime.now().isoformat()
        }
        
        
