"""dashboard.py - Alias entrypoint for 04_review_dashboard.py."""

import os
import sys

dashboard_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "04_review_dashboard.py")

if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        is_streamlit = get_script_run_ctx() is not None
    except Exception:
        is_streamlit = False

    if is_streamlit:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("review_dashboard", dashboard_script)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.render_dashboard()
    else:
        import subprocess
        print("🚀 正在启动 Streamlit 审核看板 (http://localhost:8501)...")
        cmd = [sys.executable, "-m", "streamlit", "run", dashboard_script] + sys.argv[1:]
        subprocess.run(cmd)
