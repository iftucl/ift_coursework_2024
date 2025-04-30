### 🔄 第一步：**删除现有的配置**

进入你的项目目录 `coursework_two/`，删除以下文件/文件夹：

```bash
rm -r source/
rm -r build/
rm Makefile
rm make.bat
```

### 🏗 第二步：指定目录为 `docs/`

如果你希望文档集中在 `docs/` 文件夹下（便于组织或部署到 GitHub Pages），你可以这样运行：

    ```bash
    poetry run sphinx-quickstart docs
    ```

然后在提示中选择：

- **不分开 source 和 build**
- 输入你的项目名称、作者等

Sphinx 会把所有内容生成在 `docs/` 文件夹内。

---

### ✅ 第三步：配置 + 生成文档

进入 `docs/`，然后：

1. **添加 autodoc 插件**到 `docs/conf.py`：
   ```python
   extensions = [
       'sphinx.ext.autodoc',
       'sphinx.ext.napoleon',
       'sphinx.ext.viewcode',
   ]

   import os
   import sys

   sys.path.insert(0, os.path.abspath('..'))
   ```

2. **自动生成 `.rst` 文件**（假设你要文档化 `modules/` 和 `FastAPI/`和`test/`）：

   ```bash
   poetry run sphinx-apidoc -o docs/ modules/ FastAPI/ test/
   ```

3. **在docs文件夹下看到modules.rst文件等，因此要在index.rst里引入它们**：
    .. toctree::
        :maxdepth: 2
        :caption: Contents:

        modules
        FastAPI
        test

4. **构建 HTML 文档**：

   ```bash
   poetry run sphinx-build -b html docs/ docs/_build/
   ```

然后你就可以在 `docs/_build/index.html` 中查看最终生成的文档啦 🎉

5. **创建代码文档**：
    ```bash
   poetry run sphinx-apidoc -o docs/ modules/ FastAPI/ test/
   ```

---

需要我帮你写一条完整命令串，自动创建并配置 `docs/` 文件夹吗？