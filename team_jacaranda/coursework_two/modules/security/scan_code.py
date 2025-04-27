import os

def run_bandit_scan():
    # 指定要检查的源代码路径
    src_path = "modules/data_storage"
    
    # 使用 poetry 调用 bandit 扫描
    os.system(f"poetry run bandit -r {src_path}")

if __name__ == "__main__":
    run_bandit_scan()

