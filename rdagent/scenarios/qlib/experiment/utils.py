import shutil
from pathlib import Path

import pandas as pd

# render it with jinja
from jinja2 import Environment, StrictUndefined

from rdagent.components.coder.factor_coder.config import FACTOR_IMPLEMENT_SETTINGS
from rdagent.utils.env import QTDockerEnv


def generate_data_folder_from_qlib():
    template_path = Path(__file__).parent / "factor_data_template"
    qtde = QTDockerEnv()
    qtde.prepare()

    # Run the Qlib backtest
    execute_log = qtde.run(
        local_path=str(template_path),
        entry=f"python generate.py",
    )

    assert (
        Path(__file__).parent / "factor_data_template" / "daily_pv_all.h5"
    ).exists(), "daily_pv_all.h5 is not generated."
    assert (
        Path(__file__).parent / "factor_data_template" / "daily_pv_debug.h5"
    ).exists(), "daily_pv_debug.h5 is not generated."

    Path(FACTOR_IMPLEMENT_SETTINGS.data_folder).mkdir(parents=True, exist_ok=True)
    shutil.copy(
        Path(__file__).parent / "factor_data_template" / "daily_pv_all.h5",
        Path(FACTOR_IMPLEMENT_SETTINGS.data_folder) / "daily_pv.h5",
    )
    shutil.copy(
        Path(__file__).parent / "factor_data_template" / "README.md",
        Path(FACTOR_IMPLEMENT_SETTINGS.data_folder) / "README.md",
    )

    Path(FACTOR_IMPLEMENT_SETTINGS.data_folder_debug).mkdir(parents=True, exist_ok=True)
    shutil.copy(
        Path(__file__).parent / "factor_data_template" / "daily_pv_debug.h5",
        Path(FACTOR_IMPLEMENT_SETTINGS.data_folder_debug) / "daily_pv.h5",
    )
    shutil.copy(
        Path(__file__).parent / "factor_data_template" / "README.md",
        Path(FACTOR_IMPLEMENT_SETTINGS.data_folder_debug) / "README.md",
    )


def get_data_folder_intro():
    """Directly get the info of the data folder.
    It is for preparing prompting message.
    """

    if (
        not Path(FACTOR_IMPLEMENT_SETTINGS.data_folder).exists()
        or not Path(FACTOR_IMPLEMENT_SETTINGS.data_folder_debug).exists()
    ):
        generate_data_folder_from_qlib()

    JJ_TPL = Environment(undefined=StrictUndefined, autoescape=True).from_string(
        """
{{file_name}}
```{{type_desc}}
{{content}}
```
"""
    )
    content_l = []
    for p in Path(FACTOR_IMPLEMENT_SETTINGS.data_folder_debug).iterdir():
        if p.name.endswith(".h5"):
            df = pd.read_hdf(p)
            # get  df.head() as string with full width
            pd.set_option("display.max_columns", None)  # or 1000
            pd.set_option("display.max_rows", None)  # or 1000
            pd.set_option("display.max_colwidth", None)  # or 199
            rendered = JJ_TPL.render(
                file_name=p.name,
                type_desc="generated by `pd.read_hdf(filename).head()`",
                content=df.head().to_string(),
            )
            content_l.append(rendered)
        elif p.name.endswith(".md"):
            with open(p) as f:
                content = f.read()
                rendered = JJ_TPL.render(
                    file_name=p.name,
                    type_desc="markdown",
                    content=content,
                )
                content_l.append(rendered)
        else:
            raise NotImplementedError(
                f"file type {p.name} is not supported. Please implement its description function.",
            )
    return "\n ----------------- file splitter -------------\n".join(content_l)
