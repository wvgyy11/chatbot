import os
import socket
import getpass
import platform
import subprocess
import pandas as pd
import streamlit as st
from datetime import timedelta

st.set_page_config(page_title="系统软硬件监控面板", page_icon="🖥️", layout="wide")

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def format_bytes(bytes_num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

st.title("🖥️ Linux 软硬件信息仪表盘")

# 1. 系统基础信息
st.subheader("📌 操作系统 & 基础信息")
col1, col2, col3, col4 = st.columns(4)

os_name = "Linux"
if os.path.exists("/etc/os-release"):
    for line in read_file("/etc/os-release").splitlines():
        if line.startswith("PRETTY_NAME="):
            os_name = line.split("=", 1)[1].strip('"')
            break

uptime_raw = read_file("/proc/uptime")
uptime_str = str(timedelta(seconds=int(float(uptime_raw.split()[0])))) if uptime_raw else "未知"

try:
    user = getpass.getuser()
except Exception:
    user = os.environ.get('USER', 'unknown')

col1.metric("操作系统", os_name)
col2.metric("内核版本", platform.uname().release)
col3.metric("运行时间", uptime_str)
col4.metric("当前用户 / 架构", f"{user} ({platform.machine()})")

# 2. CPU & 内存
st.markdown("---")
st.subheader("⚡ CPU 与 内存使用")
col_cpu, col_mem = st.columns(2)

# CPU 数据
with col_cpu:
    st.markdown("#### 处理器 (CPU)")
    cpu_info = read_file("/proc/cpuinfo")
    model_name = "未知"
    for line in cpu_info.splitlines():
        if "model name" in line:
            model_name = line.split(":", 1)[1].strip()
            break
    st.write(f"**型号**: `{model_name}`")
    st.write(f"**核心总数**: `{os.cpu_count() or '未知'} 线程`")

# 内存数据
with col_mem:
    st.markdown("#### 内存 (RAM)")
    meminfo = {}
    for line in read_file("/proc/meminfo").splitlines():
        parts = line.split(":")
        if len(parts) == 2 and parts[1].strip().split()[0].isdigit():
            meminfo[parts[0].strip()] = int(parts[1].strip().split()[0]) * 1024

    total_mem = meminfo.get('MemTotal', 1)
    avail_mem = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
    used_mem = total_mem - avail_mem
    pct = round((used_mem / total_mem) * 100, 1)

    st.progress(pct / 100.0)
    st.write(f"**已用**: {format_bytes(used_mem)} / **总计**: {format_bytes(total_mem)} (`{pct}%`)")

# 3. 磁盘信息
st.markdown("---")
st.subheader("💾 磁盘存储")
stat = os.statvfs('/')
d_total = stat.f_frsize * stat.f_blocks
d_free = stat.f_frsize * stat.f_bavail
d_used = d_total - d_free
d_pct = round((d_used / d_total) * 100, 1) if d_total else 0

st.write(f"**根目录 (/)**: 已使用 `{format_bytes(d_used)}` / 总计 `{format_bytes(d_total)}`")
st.progress(d_pct / 100.0)
