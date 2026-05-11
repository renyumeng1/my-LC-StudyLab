import os
from pathlib import Path
from typing import Any

import pytest


def _read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip().upper() == key.upper():
            return value.strip().strip("\"'")
    return ""


def _find_dotenv() -> Path | None:
    backend_dir = (
        Path(__file__).resolve().parents[3]
    )  # tests/workflows/nodes -> backend
    for candidate in [
        backend_dir / ".env",
        backend_dir.parent / ".env",
    ]:
        if candidate.exists():
            return candidate
    return None


def _resolve_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("test-"):
        return api_key

    dotenv = _find_dotenv()
    if dotenv:
        api_key = _read_env_value(dotenv, "OPENAI_API_KEY")
        if api_key and not api_key.startswith("test-"):
            return api_key

    return ""


@pytest.fixture(scope="module")
def planner_node_module() -> Any:
    api_key = _resolve_api_key()
    if not api_key:
        pytest.skip(
            "需要设置真实 OPENAI_API_KEY（.env 或环境变量）才能运行 planner_node 真实请求测试"
        )

    os.environ["OPENAI_API_KEY"] = api_key
    import backend.workflows.nodes.planner_node as module

    return module


@pytest.mark.integration
class TestPlannerNodeIntegration:
    """planner_node 真实 LLM 请求集成测试"""

    def test_basic_learning_plan(self, planner_node_module: Any) -> None:
        """基础场景：生成 Python 装饰器学习计划"""
        state: dict[str, Any] = {
            "user_question": "我想学习Python的装饰器（decorator），它是如何工作的？",
            "messages": [],
        }

        result = planner_node_module.planner_node(state)

        self._assert_no_error(result)
        plan = self._assert_valid_plan(result)
        self._print_plan("Python 装饰器", plan)

    def test_advanced_topic(self, planner_node_module: Any) -> None:
        """进阶场景：生成 Transformer 架构学习计划"""
        state: dict[str, Any] = {
            "user_question": "Transformer注意力机制的数学原理是什么？多头注意力如何并行计算？",
            "messages": [],
        }

        result = planner_node_module.planner_node(state)

        self._assert_no_error(result)
        plan = self._assert_valid_plan(result)
        self._print_plan("Transformer 注意力机制", plan)

    def test_beginner_topic(self, planner_node_module: Any) -> None:
        """入门场景：生成 Git 基础学习计划"""
        state: dict[str, Any] = {
            "user_question": "Git是什么？怎么用？我完全没接触过版本控制。",
            "messages": [],
        }

        result = planner_node_module.planner_node(state)

        self._assert_no_error(result)
        plan = self._assert_valid_plan(result)
        self._print_plan("Git 入门", plan)

    # ======================= helpers =======================

    @staticmethod
    def _assert_no_error(result: dict[str, Any]) -> None:
        assert "error" not in result, (
            f"planner_node 返回错误:\n"
            f"  error: {result.get('error')}\n"
            f"  error_node: {result.get('error_node')}"
        )

    @staticmethod
    def _assert_valid_plan(result: dict[str, Any]) -> dict[str, Any]:
        assert "learning_plan" in result, "返回结果中缺少 learning_plan"
        plan: dict[str, Any] = result["learning_plan"]

        assert plan.get("topic"), "学习主题不能为空"
        assert (
            len(plan.get("objectives", [])) >= 3
        ), f"学习目标至少3个，实际: {len(plan.get('objectives', []))}"
        assert (
            len(plan.get("key_points", [])) >= 5
        ), f"关键知识点至少5个，实际: {len(plan.get('key_points', []))}"
        assert plan.get("difficulty") in (
            "beginner",
            "intermediate",
            "advanced",
        ), f"难度级别不合法: {plan.get('difficulty')}"
        assert (
            isinstance(plan.get("estimated_time"), int) and plan["estimated_time"] > 0
        ), f"预计时间应为正整数: {plan.get('estimated_time')}"

        assert "messages" in result, "返回结果中缺少 messages"
        assert "current_step" in result, "返回结果中缺少 current_step"

        return plan

    @staticmethod
    def _print_plan(label: str, plan: dict[str, Any]) -> None:
        print(f"\n{'=' * 60}")
        print(f"📋 [{label}] 学习计划 LLM 输出:")
        print(f"  主题: {plan['topic']}")
        print(f"  难度: {plan['difficulty']}")
        print(f"  预计时间: {plan['estimated_time']} 分钟")
        print(f"  学习目标 ({len(plan['objectives'])} 条):")
        for i, obj in enumerate(plan["objectives"], 1):
            print(f"    {i}. {obj}")
        print(f"  关键知识点 ({len(plan['key_points'])} 条):")
        for point in plan["key_points"]:
            print(f"    • {point}")
        print(f"{'=' * 60}\n")
