import asyncio
from dataclasses import asdict
from typing import Any, List
import openai
from daily_paper.core.operators.base import Operator
from daily_paper.core.models import Paper, PaperWithSummary
from daily_paper.core.common import logger
from daily_paper.core.config import LLMConfig
from tqdm.asyncio import tqdm_asyncio


class LLMSummarizer(Operator):
    """使用LLM生成论文摘要的算子"""

    def __init__(self, llm_config: LLMConfig):
        """初始化LLMSummarizer

        Args:
            llm_config: LLM配置
            max_concurrent_requests: 最大并发请求数，默认为5
        """
        self.client = openai.AsyncOpenAI(
            api_key=llm_config.api_key, base_url=llm_config.base_url
        )
        self.model = llm_config.model_name
        self.semaphore = asyncio.Semaphore(llm_config.max_concurrent_requests)

    async def summarize_paper(self, paper_text) -> str:
        async with self.semaphore:
            prompt = f"用中文帮我介绍一下这篇文章: {paper_text}"
            summary = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术论文分析助手。"},
                    {"role": "user", "content": prompt},
                ],
            )
            return summary.choices[0].message.content

    async def process(
        self, papers: list[tuple[Paper, str]]
    ) -> list[tuple[PaperWithSummary]]:
        """为论文生成总结

        Args:
            papers: 论文列表

        Returns:
            List[PaperWithSummary]: 添加了摘要的论文列表
        """
        # 使用asyncio.gather并行处理所有论文
        tasks = [self.summarize_paper(paper_text) for paper, paper_text in papers]
        summaries = await tqdm_asyncio.gather(*tasks, desc="总结论文", total=len(tasks))

        # 将结果组装成PaperWithSummary对象
        results = [
            PaperWithSummary(**asdict(paper), summary=summary)
            for (paper, _), summary in zip(papers, summaries)
        ]

        return results
