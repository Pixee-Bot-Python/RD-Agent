import json
from pathlib import Path
from typing import Dict

from jinja2 import Environment, StrictUndefined

from rdagent.components.coder.factor_coder.CoSTEER.evolvable_subjects import (
    FactorEvolvingItem,
)
from rdagent.components.coder.factor_coder.utils import get_data_folder_intro
from rdagent.core.conf import RD_AGENT_SETTINGS
from rdagent.core.log import RDAgentLog
from rdagent.core.prompts import Prompts
from rdagent.core.scenario import Scenario
from rdagent.oai.llm_utils import APIBackend

scheduler_prompts = Prompts(file_path=Path(__file__).parent.parent / "prompts.yaml")


def RandomSelect(to_be_finished_task_index, implementation_factors_per_round):
    import random

    to_be_finished_task_index = random.sample(
        to_be_finished_task_index,
        implementation_factors_per_round,
    )

    RDAgentLog().info(f"The random selection is: {to_be_finished_task_index}")
    return to_be_finished_task_index


def LLMSelect(
    to_be_finished_task_index,
    implementation_factors_per_round,
    evo: FactorEvolvingItem,
    former_trace: Dict,
    scen: Scenario,
):
    tasks = []
    for i in to_be_finished_task_index:
        # find corresponding former trace for each task
        target_factor_task_information = evo.sub_tasks[i].get_factor_information()
        if target_factor_task_information in former_trace:
            tasks.append((i, evo.sub_tasks[i], former_trace[target_factor_task_information]))

    system_prompt = (
        Environment(undefined=StrictUndefined)
        .from_string(
            scheduler_prompts["select_implementable_factor_system"],
        )
        .render(
            scenario=scen.get_scenario_all_desc(),
        )
    )

    while True:
        user_prompt = (
            Environment(undefined=StrictUndefined)
            .from_string(
                scheduler_prompts["select_implementable_factor_user"],
            )
            .render(
                factor_num=implementation_factors_per_round,
                sub_tasks=tasks,
            )
        )
        if (
            APIBackend().build_messages_and_calculate_token(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )
            < RD_AGENT_SETTINGS.chat_token_limit
        ):
            break

    response = APIBackend().build_messages_and_create_chat_completion(
        user_prompt=user_prompt,
        system_prompt=system_prompt,
        json_mode=True,
    )
    try:
        selection = json.loads(response)["selected_factor"]
        if not isinstance(selection, list):
            return to_be_finished_task_index
        selection_index = [x for x in selection if isinstance(x, int)]
    except:
        return to_be_finished_task_index

    return selection_index