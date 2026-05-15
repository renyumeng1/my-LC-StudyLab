# LangChain Overview

LangChain is a framework for building applications powered by large language models. It helps developers connect prompts, models, tools, memory, retrievers, and application logic into repeatable workflows.

## Core Ideas

- A model provides language understanding and generation.
- A prompt defines the task and constraints for the model.
- A chain composes multiple operations into one flow.
- A tool exposes external actions such as search, calculation, or database access.
- An agent decides when to call tools and how to use their results.

## In LC-StudyLab

LC-StudyLab uses LangChain to power chat, study planning, quiz generation, answer grading, feedback generation, and retrieval augmented generation. The backend wraps these capabilities behind FastAPI endpoints so the frontend or tests can call them consistently.
