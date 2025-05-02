---

## ✅ 步骤：在 `coursework_two/` 目录下生成完整的 Sphinx 文档

---

### 🔄 第一步：清理旧的 Sphinx 文件（可选）

如果之前已经初始化过 Sphinx，先清除旧文件：

```bash
cd coursework_two
rm -rf docs/
```

---

### 🏗️ 第二步：生成新的 Sphinx 配置（不分 source/build）

```bash
cd coursework_two
poetry run sphinx-quickstart docs
```

在交互式提示中选择：

- Separate source and build directories: ❌ 否
- Project name、author：✅ 按你需要填写
- Build .gitignore: ✅ 建议选 Yes
- 所有扩展选项可以先跳过，后面手动加

---

### 🛠️ 第三步：编辑 `docs/conf.py`

打开 `docs/conf.py`，找到扩展和路径配置部分，修改如下：

```python
# -- Path setup ----------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# -- General configuration -----------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

# -- HTML output ---------------------------------------------------

html_theme = 'alabaster'  # 或 'sphinx_rtd_theme'，看你喜好
```

---

### 📦 第四步：生成 `.rst` 文件（递归）

```bash
poetry run sphinx-apidoc -o docs/ modules/
poetry run sphinx-apidoc -o docs/ my_fastapi/
poetry run sphinx-apidoc -o docs/ test/
```

这一步会在 `docs/` 下生成多个 `.rst` 文件，每个模块一个。**这是你想要的结构。**

---

### 🧱 第五步：编辑 `docs/index.rst`

你只需要保留最基础结构并引入顶层模块（其他模块会自动跟随引用）：

```rst
Welcome to 项目的文档!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
   my_fastapi
   test
```

---

### 🌍 第六步：生成 HTML 文档

```bash
poetry run sphinx-build -b html docs/ docs/_build/
```

打开：

```
docs/_build/index.html
```

即可浏览完整文档（包括所有模块、函数、类等的说明）。

---

## ✅ 生成文档后怎么用？

你可以：

- 本地用浏览器打开 `docs/_build/index.html` 查看文档
- 把 `docs/` 上传到 GitHub 并用 [GitHub Pages](https://pages.github.com/) 部署文档（设置 Pages 源目录为 `docs/_build/`）
- 生成 PDF 或其他格式文档（可通过 `sphinx-build -b latexpdf` 等实现）

---
