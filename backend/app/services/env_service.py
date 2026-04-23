"""环境检测服务"""

import subprocess
import json
import shutil
from typing import Optional, Dict, Any
from datetime import datetime


class EnvironmentService:
    """环境检测服务"""
    
    @staticmethod
    def check_python() -> Dict[str, Any]:
        """检测 Python 环境"""
        result = {
            "python_path": shutil.which("python3"),
            "python_version": None,
            "pip_version": None,
            "venv_path": None,
        }
        
        # Python 版本
        try:
            py_version = subprocess.run(
                ["python3", "--version"],
                capture_output=True, text=True, timeout=5
            )
            result["python_version"] = py_version.stdout.strip().split()[-1]
        except Exception:
            pass
        
        # pip 版本
        try:
            pip_version = subprocess.run(
                ["pip3", "--version"],
                capture_output=True, text=True, timeout=5
            )
            result["pip_version"] = pip_version.stdout.strip().split()[-1]
        except Exception:
            pass
        
        # 虚拟环境
        venv = subprocess.run(
            ["python3", "-c", "import sys; print(sys.prefix if sys.prefix != sys.base_prefix else '')"],
            capture_output=True, text=True, timeout=5
        )
        if venv.stdout.strip():
            result["venv_path"] = venv.stdout.strip()
        
        return result
    
    @staticmethod
    def check_nvidia() -> Dict[str, Any]:
        """检测 NVIDIA GPU"""
        result = {
            "gpu_type": "nvidia",
            "cuda_version": None,
            "nvidia_smi_available": False,
            "gpu_info": {"gpu_type": "nvidia", "gpus": []},
        }
        
        # 检测 nvidia-smi
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return result
        
        result["nvidia_smi_available"] = True
        
        try:
            # 获取 GPU 信息
            smi_output = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            
            gpus = []
            for line in smi_output.stdout.strip().split('\n'):
                if line:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        gpus.append({
                            "index": int(parts[0]),
                            "name": parts[1],
                            "memory_total_mb": int(parts[2]),
                            "memory_used_mb": int(parts[3]),
                            "memory_free_mb": int(parts[4]),
                            "utilization_gpu": int(parts[5]),
                            "temperature": int(parts[6]),
                        })
            
            result["gpu_info"]["gpus"] = gpus
            
            # 检测 CUDA 版本
            cuda_output = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version,cuda_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if cuda_output.stdout.strip():
                cuda_info = cuda_output.stdout.strip().split(', ')
                if len(cuda_info) >= 2:
                    result["cuda_version"] = cuda_info[1].split()[0]
                    
        except Exception as e:
            print(f"NVIDIA detection error: {e}")
        
        return result
    
    @staticmethod
    def check_amd() -> Dict[str, Any]:
        """检测 AMD GPU"""
        result = {
            "gpu_type": "amd",
            "rocm_version": None,
            "rocm_smi_available": False,
            "gpu_info": {"gpu_type": "amd", "gpus": []},
        }
        
        # 检测 rocm-smi
        rocm_smi = shutil.which("rocm-smi")
        if not rocm_smi:
            return result
        
        result["rocm_smi_available"] = True
        
        try:
            # 获取 GPU 信息
            smi_output = subprocess.run(
                ["rocm-smi", "--showallinfo"],
                capture_output=True, text=True, timeout=10
            )
            
            # 解析 rocm-smi 输出（简化版）
            gpus = []
            for line in smi_output.stdout.split('\n'):
                if 'GPU[' in line or 'Card' in line:
                    # 简化解析，实际项目需要更完善的解析
                    gpus.append({
                        "index": len(gpus),
                        "name": "AMD GPU",
                        "memory_total_mb": 0,
                        "memory_used_mb": 0,
                        "memory_free_mb": 0,
                        "utilization_gpu": 0,
                        "temperature": 0,
                    })
            
            result["gpu_info"]["gpus"] = gpus
            
            # 检测 ROCm 版本
            hip_output = subprocess.run(
                ["hipcc", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if hip_output.stdout:
                for line in hip_output.stdout.split('\n'):
                    if 'HIP version' in line or 'ROCm version' in line:
                        result["rocm_version"] = line.split()[-1]
                        break
                    
        except Exception as e:
            print(f"AMD detection error: {e}")
        
        return result
    
    @staticmethod
    def check_packages() -> Dict[str, Optional[str]]:
        """检测 Python 包版本"""
        result = {
            "torch_version": None,
            "transformers_version": None,
            "vllm_version": None,
        }
        
        packages = ["torch", "transformers", "vllm"]
        for pkg in packages:
            try:
                version_cmd = subprocess.run(
                    ["python3", "-c", f"import {pkg}; print({pkg}.__version__)"],
                    capture_output=True, text=True, timeout=5
                )
                if version_cmd.returncode == 0:
                    version_key = f"{pkg}_version"
                    result[version_key] = version_cmd.stdout.strip()
            except Exception:
                pass
        
        return result
    
    @staticmethod
    def detect_gpu_type() -> Dict[str, Any]:
        """自动检测 GPU 类型"""
        # 优先检测 NVIDIA
        nvidia = EnvironmentService.check_nvidia()
        if nvidia["nvidia_smi_available"]:
            return nvidia
        
        # 检测 AMD
        amd = EnvironmentService.check_amd()
        if amd["rocm_smi_available"]:
            return amd
        
        # 无 GPU
        return {
            "gpu_type": "none",
            "cuda_version": None,
            "rocm_version": None,
            "nvidia_smi_available": False,
            "rocm_smi_available": False,
            "gpu_info": {"gpu_type": "none", "gpus": []},
        }
    
    @classmethod
    def check_all(cls) -> Dict[str, Any]:
        """执行完整环境检测"""
        python_info = cls.check_python()
        gpu_info = cls.detect_gpu_type()
        package_info = cls.check_packages()
        
        # 确定环境状态
        status = "not_installed"
        message = "environment not checked"
        
        if python_info["python_path"]:
            if package_info["vllm_version"]:
                if gpu_info["gpu_type"] in ["nvidia", "amd"]:
                    status = "ready"
                    message = f"environment is ready ({gpu_info['gpu_type'].upper()})"
                else:
                    status = "partial"
                    message = "vLLM installed but no GPU detected"
            else:
                status = "partial"
                message = "Python available but vLLM not installed"
        
        return {
            **python_info,
            **gpu_info,
            **package_info,
            "status": status,
            "message": message,
            "last_checked_at": datetime.now().isoformat(),
        }
