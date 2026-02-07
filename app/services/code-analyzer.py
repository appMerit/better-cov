"""Error analyzer agent for failure signature analysis.

Uses Claude Agent SDK to analyze clusters and recommend code fixes.
Passes representative samples selected by distance to centroid.
"""

import json
from pathlib import Path

from app.models.internal.error_analyzer import ErrorAnalysis, FailureSignatureGroup
from app.services.code_analyzer.core import (
    AGENT,
    FILE_ACCESS_POLICY,
    TOOL,
    get_llm_client,
)

from .prompts import SYSTEM, TASK


class FailureSignatureAnalyzer:
    """Analyzes clusters of failure signatures to identify root causes and recommend fixes."""

    name = AGENT.ERROR_ANALYZER
    file_access = FILE_ACCESS_POLICY.READ_ONLY
    system_prompt = SYSTEM
    output_type = ErrorAnalysis
    standard_tools = [TOOL.GLOB, TOOL.GREP, TOOL.LS, TOOL.READ]

    async def run(
        self, failed_group: FailureSignatureGroup, code_path: str
    ) -> ErrorAnalysis:
        """Analyze failure signature group and provide solutions.

        Args:
            failed_group: Group of failure signatures with similar patterns
            code_path: Path to sandboxed code for analysis

        Returns:
            ErrorAnalysis with root cause, traceback, and recommendations
        """
        client = await get_llm_client()

        if self.name not in client.compiled_agents:
            client.compile_agent(
                agent_name=self.name,
                file_access=self.file_access,
                output_type=self.output_type,
                standard_tools=self.standard_tools,
                system_prompt=self.system_prompt,
                cwd=Path(code_path),
            )

        schema = json.dumps(ErrorAnalysis.model_json_schema(), indent=2)

        # Get consolidated summary
        if not failed_group.consolidated_summary:
            raise ValueError(
                "FailureSignatureGroup must have consolidated_summary set before analysis"
            )

        summary = failed_group.consolidated_summary
        metadata = failed_group.metadata  # type: ignore

        # ============================================================================
        # BUILD RICH CONTEXT from representative samples
        # ============================================================================

        # Cluster overview - keep it focused and actionable
        top_components = summary.all_code_components[:3]  # Top 3 components
        top_errors = summary.common_error_messages[:2]  # Top 2 error messages

        cluster_overview = f"""
**Cluster**: {summary.cluster_label} ({summary.failure_count} failures)

**Common Errors**:
{chr(10).join(f"- {msg[:100]}{'...' if len(msg) > 100 else ''} ({count}x)" for msg, count in top_errors)}

**Key Components** (grep targets):
{chr(10).join(f"- {comp}" for comp in top_components)}

**Action**: grep "{top_components[0]}" to start investigation
"""

        # Representative samples (selected by distance to centroid)
        samples_context = """
**Representative Failure Samples** (most typical in cluster):
"""

        for idx, sample in enumerate(summary.representative_samples, 1):
            samples_context += f"""
---
### Sample {idx}: {sample.test_name}
**Test File**: {sample.test_file}
**Representativeness**: {sample.distance_to_centroid:.4f} (lower = more typical)

**Error**: {sample.error_message}

**Failed Assertions**:
"""
            for assertion in sample.failed_assertions:
                samples_context += f"```\n{assertion.pretty}\n```\n"

            # LLM interaction context (keep concise)
            if sample.llm_messages:
                samples_context += "\n**LLM Messages**:\n"
                for msg_idx, msg in enumerate(sample.llm_messages, 1):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    # Aggressively truncate - show just enough to understand context
                    if role == "system" and len(content) > 300:
                        content = content[:300] + "...[system prompt truncated]"
                    elif len(content) > 200:
                        content = content[:200] + "...[truncated]"
                    samples_context += f"  {msg_idx}. {role}: {content}\n"
                samples_context += "\n"

            # Tool calls
            if sample.tool_calls:
                samples_context += (
                    f"**Tools Called**: {', '.join(sample.tool_calls)}\n\n"
                )
            else:
                samples_context += "**Tools Called**: None\n\n"

            # Execution trace (code locations) - show key components only
            if sample.code_locations:
                samples_context += "**Execution Trace** (key components):\n"
                # Show first 5 components (most relevant)
                for loc in sample.code_locations[:5]:
                    samples_context += f"  → {loc.component}\n"
                if len(sample.code_locations) > 5:
                    samples_context += (
                        f"  ... and {len(sample.code_locations) - 5} more\n"
                    )
                samples_context += "\n"

            # Actual output (compact)
            samples_context += f"**Actual Output**:\n```\n{sample.actual_output}\n```\n"

        # Combine all context
        full_context = f"""
{cluster_overview}

{samples_context}
"""

        # Build task prompt
        # Define max_turns here so we can reference it in the prompt
        max_turns = 75

        task = TASK.format(
            name=metadata.name,
            description=metadata.description,
            schema=schema,
            context=full_context.strip(),
        )

        # Add explicit turn limit reminder at the end
        task += f"""

⚠️  **TURN LIMIT REMINDER**: You have {max_turns} turns maximum.
- If you reach turn ~{int(max_turns * 0.85)} without completing analysis, EMIT PARTIAL RESULTS
- Use `emit_structured_result` with whatever you've verified so far
- Partial analysis > no analysis"""

        # Give agent sufficient turns for: grep → read → analyze → verify → output
        error_analyses = await client.run_agent(
            self.name, task, self.output_type, max_turns=max_turns
        )

        return error_analyses
