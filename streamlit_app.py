import os
import sys
import shutil
import socket
import getpass
import platform
import subprocess
import urllib.request
import streamlit as st

st.set_page_config(page_title="容器探针", page_icon="🕵️", layout="wide")

st.title("🕵️ Streamlit Cloud 容器探针 & 硬件检测")
st.caption("真实硬件限制探测工具 (支持 cgroup 穿透与交互终端)")

# ----------------- 辅助函数 -----------------
def format_bytes(bytes_num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

def get_real_memory_limit():
    """穿透 Docker/K8s 查看真实被限制的内存配额 (cgroup)"""
    limit_files = [
        "/sys/fs/cgroup/memory.max",                    # cgroup v2
        "/sys/fs/cgroup/memory/memory.limit_in_bytes"   # cgroup v1
    ]
    for path in limit_files:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    val = f.read().strip()
                    if val != "max" and val.isdigit():
                        bytes_val = int(val)
                        if bytes_val < 10**14:  # 排除未限制的极大值
                            return format_bytes(bytes_val), bytes_val
            except Exception:
                pass
    return "未做严格限制或共享宿主机", 0

def run_bash_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        output = res.stdout if res.returncode == 0 else (res.stderr or "命令执行完成但无输出")
        return output
    except Exception as e:
        return f"执行失败: {str(e)}"

# ----------------- 1. 真实配额与宿主机概况 -----------------
st.subheader("1. 硬件限制与容器配额 (Real Quotas)")

col1, col2, col3, col4 = st.columns(4)

# 真实内存限制
real_mem_str, _ = get_real_memory_limit()
col1.metric("🔒 容器内存配额 (真实限制)", real_mem_str, help="Streamlit Cloud 给单个应用分配的硬性上限，通常约 1GB")

# CPU 线程
col2.metric("⚡ 可见 CPU 核心数", f"{os.cpu_count()} 核", help="注意：虽然可见多核，但计算资源是多租户共享抢占的")

# 磁盘配额
total_b, used_b, free_b = shutil.disk_usage("/")
col3.metric("💾 磁盘可用空间", f"{format_bytes(free_b)}", f"总空间 {format_bytes(total_b)}")

# 出网 IP
try:
    public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=2).read().decode('utf8')
except Exception:
    public_ip = "获取失败"
col4.metric("🌐 容器出口公网 IP", public_ip)

st.markdown("---")

# ----------------- 2. 系统与宿主机底层信息 -----------------
st.subheader("2. 容器环境与系统详情")

c1, c2 = st.columns(2)
with c1:
    st.markdown("##### 🖥️ 系统信息")
    st.write(f"- **操作系统**: `{platform.platform()}`")
    st.write(f"- **Python 版本**: `{platform.python_version()}`")
    st.write(f"- **当前执行用户**: `{getpass.getuser()}` (UID: `{os.getuid() if hasattr(os, 'getuid') else 'N/A'}`)")
    st.write(f"- **工作目录**: `{os.getcwd()}`")

with c2:
    st.markdown("##### ⚙️ 宿主机 CPU 型号")
    cpu_model = run_bash_cmd("cat /proc/cpuinfo | grep 'model name' | head -n 1 | awk -F': ' '{print $2}'")
    st.code(cpu_model.strip() or "无法获取", language="text")

st.markdown("---")

# ----------------- 3. 网页版交互 Linux 终端 -----------------
st.subheader("3. 网页版 Linux 终端")
st.caption("在这里输入任何 Linux 命令直接执行（例如：`ls -la`, `ps aux`, `top -b -n 1`, `pip list`, `env` 等）")

# 快捷命令按钮
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
cmd_input = ""

default_cmd = st.text_input("输入 Linux 命令后按回车：", value="uname -a && free -h && df -h")

if default_cmd:
    with st.spinner("正在执行命令..."):
        result = run_bash_cmd(default_cmd)
        st.markdown(f"**`{default_cmd}` 执行结果:**")
        st.code(result, language="bash")
