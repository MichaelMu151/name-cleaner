# Advanced Name Cleaner for Chinese Name Variants

> In a nutshell: Automatically detect and help you unify Chinese names that sound the same but are written differently (e.g., "张三" vs. "张山"), through an interactive decision process.

---

## Why This Tool?

When organizing employee rosters, customer lists, or project member records, you often encounter:

- The same person recorded with typo‑induced homophones (e.g., "李思" vs. "李斯")
- Mixed usage of abbreviations and full names (e.g., "王五" vs. "王武")
- Manual entry inconsistencies like "张珊" and "张山" coexisting

Manually checking thousands of rows is tedious and error‑prone.  
**This tool** automatically clusters suspected name variants and then guides you through **interactive decisions** to quickly standardise them.

---

## Key Features

- **Automatic clustering** – groups names with similar Pinyin spellings
- **Contextual information** – displays auxiliary columns (year, department, company, etc.) during decision‑making to help you judge
- **Flexible actions** – supports merging all, custom mapping, or skipping a group
- **Traceable results** – automatically keeps the original name column and exports a correction map

---

## Input and Output

### Input (what you need to prepare)
- A **tabular dataset** (as a `pandas.DataFrame`), e.g., read from CSV or Excel
- The table must contain a column of **Chinese names** (column name is configurable)
- You may also specify **auxiliary columns** (e.g., year, department, company) – these are shown only for context and do not affect the algorithm

### Output (what you get)
1. **A cleaned DataFrame** – the name column is standardised, and a new column `{original_column}_raw` is added to preserve the original values
2. **A correction mapping dictionary** – records "original name → standardised name"
3. (Optional) Save the result to CSV or Excel

---

## Quick Start (3 Steps)

### 1. Install Dependencies
Make sure your Python version is ≥ 3.7, then run:
```bash
pip install pandas numpy pypinyin tabulate tqdm
```
> `difflib` is built‑in, so no extra installation is needed.

### 2. Prepare Your Data
For example, your CSV file `my_data.csv` might look like:

| p_name | year | company |
|--------|------|---------|
| 张三   | 2020 | A公司   |
| 张山   | 2020 | A公司   |
| 张珊   | 2021 | B公司   |

### 3. Run the Cleaning Script
Create a Python script (e.g., `clean_my_data.py`) with the following:

```python
import pandas as pd
from advanced_name_cleaner import AdvancedNameCleaner

# Load your data
df = pd.read_csv('my_data.csv')

# Instantiate the cleaner with auxiliary columns and similarity threshold
cleaner = AdvancedNameCleaner(
    aux_columns=['year', 'company'],   # replace with your actual column names
    threshold=0.85                     # similarity threshold (explained below)
)

# Start the interactive review
df_clean, mapping = cleaner.interactive_review(df, name_col='p_name')

# Check results
print("Correction map:", mapping)
print("Cleaned data:", df_clean)

# Save results
df_clean.to_csv('cleaned_data.csv', index=False, encoding='utf-8-sig')
```

When you run the script, an **interactive command‑line interface** will appear (see next section).

---

## 🖥️ Interactive Interface Walkthrough

The tool automatically finds suspected groups and asks you to decide on each one. Example screen:

```
【疑似混淆分组】 发现 3 个变体
+----+--------+--------+--------+--------+----------+
| ID | 名字   | 频次   | 拼音   | year   | company  |
+----+--------+--------+--------+--------+----------+
| 1  | 张三   | 5      | zhangsan| 2020   | A公司    |
| 2  | 张山   | 2      | zhangsan| 2020   | A公司    |
| 3  | 张珊   | 1      | zhangsan| 2021   | B公司    |
+----+--------+--------+--------+--------+----------+

指令:
  [ID]      : 全组合并（如输入 1，则其他人名都改为第1个）
  pass / p  : 跳过（不同人）
  custom / c: 自定义（如 '2>1' 表示把2改为1）
  stop / q  : 保存并退出
指令 > 
```

### What You Can Enter:
- A number ID (e.g., `1`) → all names in the group are changed to the one with that ID.
- `pass` → treat them as different persons; keep everything unchanged and move on.
- `custom` → define your own mapping, e.g., `2>1;3>1` means change ID 2 and ID 3 to ID 1.
- `stop` → stop immediately; changes made so far are applied, remaining groups are left untouched.

> 💡 Tip: Auxiliary columns (year, company) help you judge – if two names appear in different years or different companies, they are likely different people, so you may want to `pass`.

---

## Configurable Parameters

When creating the `AdvancedNameCleaner` object, two main parameters are available:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `aux_columns` | `list` | `[]` | List of auxiliary column names (e.g., `['year', 'department']`). These columns are displayed during decision‑making to provide context, but are **not** used in the similarity calculation. |
| `threshold` | `float` | `0.85` | **Similarity threshold** (range 0~1). Two names are clustered only if their Pinyin similarity exceeds this value. A higher value makes grouping stricter (fewer false positives, but may miss some variants); a lower value makes grouping looser (more variants found, but may merge different people). |

### How to Adjust the Threshold?
- Start with the default 0.85 and observe the proposed groups.
- If you see clearly different people grouped together → increase the threshold (e.g., to 0.90).
- If you notice variants of the same person are not grouped → decrease the threshold (e.g., to 0.80).
- It’s recommended to adjust in steps of 0.03–0.05 until you find the best balance for your data.

---

## Output Details

### 1. Cleaned DataFrame
- The name column (e.g., `p_name`) now contains standardised names.
- A new column `p_name_raw` is added to keep the original values for verification. 

### 2. Correction Mapping Dictionary
Example:
```python
{'张山': '张三', '张珊': '张三'}
```
This means "张山" and "张珊" were both changed to "张三".

### 3. Saving Results
You can use `to_csv()` or `to_excel()` as shown in the example.

---

## Complete Demo (with Simulated Data)

We provide an `example_usage.py` script that generates a small mock dataset and runs the full cleaning process. You can run it directly:

```bash
python example_usage.py
```

Follow the interactive prompts to quickly understand how the tool works.

---

## Q&A ====

Q: Does the tool support English names or numbers?
A: It is primarily designed for Chinese names. Non‑Chinese characters are ignored, which may affect similarity – it is recommended to pre‑process such cases.

Q: Can I fully automate the merging without manual intervention?
A: This tool is designed to be semi‑automatic because name unification often requires domain knowledge (same pronunciation does not always mean same person). If you prefer full automation, you could modify the code to always pick the most frequent name in each group, but that is not recommended.

Q: My dataset has hundreds of thousands of rows. Will it be slow?
A: The algorithm groups names by their first character, so complexity is manageable. For tens of thousands of rows, it usually finishes within tens of seconds. If the dataset is extremely large, consider testing on a sample first.

Q: Do I have to specify auxiliary columns?
A: No, they are optional. If you do not specify any, the tool will only show the name, frequency, and Pinyin – you will have to decide based on that alone.

Q: I get `ModuleNotFoundError: No module named 'pypinyin'` – what now?
A: Install the missing package: `pip install pypinyin`.

**Q: How can I be sure the corrections are correct?**  
A: After cleaning, you can compare the `p_name_raw` and `p_name` columns, or review the correction mapping. It is always good practice to keep a backup of the original data.

---

## Contributing and Feedback

Issues and Pull Requests are welcome.  
If you have any questions about usage, please open an issue in the GitHub repository.

---

## Project Structure

```
name_cleaner/
├── advanced_name_cleaner.py   # Core class
├── example_usage.py           # Demo script
├── README.md                  # This file
└── .gitignore                 # (Optional) Git ignore file
```
