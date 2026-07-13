# 姓名清洗审阅工作台

这是一个用于发现和人工审阅同音异形姓名的 Python 工具。程序先按姓氏和拼音相似度生成候选组，再通过频次、年份、职位、单位等上下文帮助研究者判断是否需要统一写法。

## 安装与启动

建议使用 Python 3.11 或更高版本：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器界面支持 CSV、XLSX 和 XLS 文件。CSV 会依次尝试 UTF-8 和 GB18030 编码。

## 审阅流程

1. 上传数据并选择姓名列。
2. 选择年份列，以及职位、单位、地区等辅助判断列。
3. 调整拼音相似度阈值并扫描候选组。
4. 对照姓名频次、组内占比、差异字和“年份—职位 / 单位”时间线。
5. 逐组选择全组合并、不合并或自定义映射。
6. 下载清洗后的 CSV 和修正映射 CSV。

界面会把最高频写法标为“建议保留”，但不会自动合并。高频只是辅助线索：同名不同人、原始材料中的系统性错字等情况都可能使高频写法并非正确答案。

清洗结果会新增 `<姓名列>_raw`，保存首次清洗前的姓名；原姓名列则应用人工确认的映射。

## 如何看时间线

例如同一候选组中：

- `王俊峰` 在 2008–2012 年和 2015–2018 年均任“副市长”；
- `王俊锋` 只在 2013–2014 年同一单位、同一职位出现；
- 两者拼音一致，且只差一个同音字。

这种连续性中断是疑似错字的重要证据。反之，如果两个写法在同一年、不同地区或不同单位同时出现，则不应仅凭同音和频次进行合并。

## 终端模式

原有 CLI 入口仍可使用：

```bash
python example_usage.py
```

也可以在代码中调用：

```python
from advanced_name_cleaner import AdvancedNameCleaner

cleaner = AdvancedNameCleaner(
    aux_columns=["year", "post1", "company"],
    threshold=0.85,
)
cleaned_df, mapping = cleaner.interactive_review(df, name_col="p_name")
```

如需自行构建界面，可调用 `build_group_evidence()` 获取结构化的变体、时间线、相似度和原始记录，调用 `apply_corrections()` 应用人工映射。

## 测试

```bash
python -m pytest
python -m py_compile advanced_name_cleaner.py app.py
```

## 方法边界

- 候选生成只使用姓氏首字、姓名长度和拼音相似度；年份、职位等字段仅用于人工判断。
- 候选组不是自动判错结果。
- 同名不同人消歧、跨姓氏别名识别和自然语言职位归一化不在当前范围内。
