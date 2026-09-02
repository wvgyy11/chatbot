import os
import re
import sys
import time
import socket
import platform
import subprocess
from datetime import timedelta

# ANSI 颜色定义
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}═══ [ {title} ] {Colors.RESET}" + "═" * (50 - len(title)))

def print_item(key, value):
    print(f"  {Colors.BOLD}{key:<18}{Colors.RESET}: {value}")

def run_cmd(cmd):
    """安全执行系统命令并返回输出"""
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, timeout=2)
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception:
        return ""

def read_file(path):
    """安全读取系统文件"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return ""

def format_bytes(bytes_num):
    """字节转换可读大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

# ==================== 1. 系统与软件信息 ====================
def get_os_info():
    print_section("操作系统 / 软件信息 (OS & Software)")
    
    # 获取 Linux 发行版
    os_name = "Linux"
    if os.path.exists("/etc/os-release"):
        content = read_file("/etc/os-release")
        for line in content.splitlines():
            if line.startswith("PRETTY_NAME="):
                os_name = line.split("=", 1)[1].strip('"')
                break
    
    # 运行时间
    uptime_str = "未知"
    uptime_raw = read_file("/proc/uptime")
    if uptime_raw:
        uptime_seconds = float(uptime_raw.split()[0])
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    print_item("操作系统", f"{Colors.GREEN}{os_name}{Colors.RESET}")
    print_item("内核版本", platform.uname().release)
    print_item("系统架构", platform.machine())
    print_item("主机名", socket.gethostname())
    print_item("当前登录用户", os.getlogin() if hasattr(os, 'getlogin') else os.environ.get('USER', 'unknown'))
    print_item("运行时间", uptime_str)
    print_item("Python 版本", platform.python_version())
    print_item("系统语言", os.environ.get('LANG', '未知'))

# ==================== 2. CPU 信息 ====================
def get_cpu_info():
    print_section("处理器信息 (CPU)")
    
    cpu_info = read_file("/proc/cpuinfo")
    model_name = "未知"
    cores = os.cpu_count() or 0
    physical_cores = set()

    for line in cpu_info.splitlines():
        if "model name" in line:
            model_name = line.split(":", 1)[1].strip()
        elif "core id" in line:
            physical_cores.add(line.split(":", 1)[1].strip())
            
    phy_count = len(physical_cores) if physical_cores else cores

    # CPU 频率 (MHz)
    freq_mhz = ""
    for line in cpu_info.splitlines():
        if "cpu MHz" in line:
            freq_mhz = line.split(":", 1)[1].strip() + " MHz"
            break

    print_item("CPU 型号", f"{Colors.YELLOW}{model_name}{Colors.RESET}")
    print_item("核心/线程数", f"{phy_count} 物理核心 / {cores} 逻辑线程")
    if freq_mhz:
        print_item("当前主频", freq_mhz)

# ==================== 3. 内存信息 ====================
def get_mem_info():
    print_section("内存与交换区 (RAM & Swap)")
    
    meminfo = {}
    content = read_file("/proc/meminfo")
    for line in content.splitlines():
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            val = parts[1].strip().split()[0]
            if val.isdigit():
                meminfo[key] = int(val) * 1024 # 转换为字节

    total_mem = meminfo.get('MemTotal', 0)
    avail_mem = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
    used_mem = total_mem - avail_mem
    mem_usage_pct = (used_mem / total_mem * 100) if total_mem else 0

    swap_total = meminfo.get('SwapTotal', 0)
    swap_free = meminfo.get('SwapFree', 0)
    swap_used = swap_total - swap_free
    swap_usage_pct = (swap_used / swap_total * 100) if swap_total else 0

    print_item("物理内存 (总计)", format_bytes(total_mem))
    print_item("物理内存 (已用)", f"{format_bytes(used_mem)} ({mem_usage_pct:.1f}%)")
    print_item("物理内存 (可用)", format_bytes(avail_mem))
    if swap_total > 0:
        print_item("Swap 交换区", f"已用: {format_bytes(swap_used)} / 总计: {format_bytes(swap_total)} ({swap_usage_pct:.1f}%)")
    else:
        print_item("Swap 交换区", "未启用")

# ==================== 4. 磁盘与挂载点 ====================
def get_disk_info():
    print_section("存储空间 (Disk / Partitions)")
    
    df_output = run_cmd("df -h -x tmpfs -x devtmpfs -x squashfs -x overlay --output=source,fstype,size,used,avail,pcent,target")
    if df_output:
        lines = df_output.splitlines()
        print(f"  {Colors.BOLD}{lines[0]}{Colors.RESET}")
        for line in lines[1:]:
            print(f"  {line}")
    else:
        # 降级方案
        stat = os.statvfs('/')
        total = stat.f_frsize * stat.f_blocks
        free = stat.f_frsize * stat.f_bavail
        used = total - free
        print_item("根分区 (/)", f"已用: {format_bytes(used)} / 总计: {format_bytes(total)}")

# ==================== 5. 显卡 (GPU) 与主板 ====================
def get_hardware_extra():
    print_section("硬件外设 (Motherboard & GPU)")
    
    # 主板信息 (可能需要root，非root尝试读取)
    board_vendor = read_file("/sys/class/dmi/id/board_vendor")
    board_name = read_file("/sys/class/dmi/id/board_name")
    if board_name:
        print_item("主板型号", f"{board_vendor} {board_name}")
    else:
        dmi_prod = read_file("/sys/class/dmi/id/product_name")
        if dmi_prod:
            print_item("设备型号", dmi_prod)

    # 检查 NVIDIA GPU
    nvidia_smi = run_cmd("nvidia-smi --query-gpu=name,memory.total,temperature.gpu,driver_version --format=csv,noheader")
    if nvidia_smi:
        for line in nvidia_smi.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 4:
                print_item("NVIDIA GPU", f"{Colors.GREEN}{parts[0]}{Colors.RESET} | 显存: {parts[1]} | 温度: {parts[2]}°C | 驱动: {parts[3]}")
    else:
        # PCI 扫描 GPU
        pci_gpu = run_cmd("lspci | grep -iE 'vga|3d|display'")
        if pci_gpu:
            for idx, line in enumerate(pci_gpu.splitlines()):
                gpu_name = line.split(":", 2)[-1].strip()
                print_item(f"GPU [{idx}]", gpu_name)
        else:
            print_item("独立显卡", "未检测到或无 lspci/nvidia-smi 权限")

# ==================== 6. 网络信息 ====================
def get_network_info():
    print_section("网络接口 (Network)")
    
    # 获取默认外网 IP (尝试连接公网DNS，不真正发包)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    
    print_item("主本地 IP", f"{Colors.GREEN}{local_ip}{Colors.RESET}")
    
    # 网卡概览
    ip_brief = run_cmd("ip -brief address")
    if ip_brief:
        for line in ip_brief.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                name, state, addr = parts[0], parts[1], " ".join(parts[2:])
                status_color = Colors.GREEN if state == "UP" else Colors.DIM
                print(f"  {Colors.BOLD}{name:<12}{Colors.RESET} [{status_color}{state:<4}{Colors.RESET}] {addr}")

# ==================== 主函数 ====================
def main():
    if platform.system() != "Linux":
        print(f"{Colors.RED}错误: 该脚本仅支持 Linux 系统。{Colors.RESET}")
        sys.exit(1)

    print(f"\n{Colors.BOLD}{Colors.HEADER}================= 系统软硬件检测概览 ================={Colors.RESET}")
    print(f"{Colors.DIM}采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    
    get_os_info()
    get_cpu_info()
    get_mem_info()
    get_disk_info()
    get_hardware_extra()
    get_network_info()
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}======================================================{Colors.RESET}\n")

if __name__ == "__main__":
    main()
