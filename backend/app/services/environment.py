"""环境检测服务 - 支持 NVIDIA CUDA 和 AMD ROCm"""

import subprocess
import json
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime


class EnvironmentService:
    """环境检测服务"""
    
    @staticmethod
    def check_python() -> Dict[str, Any]:
        """检测 Python 环境"""
        result = {
            "python_path": shutil.which("python3") or shutil.which("python"),
            "python_version": None,
            "pip_version": None,
            "venv_path": None,
        }
        
        # Python 版本
        try:
            py_version = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            result["python_version"] = py_version.stdout.strip()
        except Exception:
            pass
        
        # pip 版本
        try:
            pip_version = subprocess.run(
                ["pip3", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            result["pip_version"] = pip_version.stdout.strip()
        except Exception:
            try:
                pip_version = subprocess.run(
                    ["pip", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                result["pip_version"] = pip_version.stdout.strip()
            except Exception:
                pass
        
        # 虚拟环境
        venv = subprocess.run(
            ["python3", "-c", "import sys; print(sys.prefix if sys.prefix != sys.base_prefix else '')"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if venv.stdout.strip():
            result["venv_path"] = venv.stdout.strip()
        
        return result
    
    @staticmethod
    def check_nvidia() -> Dict[str, Any]:
        """检测 NVIDIA GPU"""
        result = {
            "gpu_type": "none",
            "cuda_version": None,
            "nvidia_smi_available": False,
            "gpu_info": {"gpu_type": "none", "gpus": []},
        }
        
        # 检查 nvidia-smi
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return result
        
        result["nvidia_smi_available"] = True
        result["gpu_type"] = "nvidia"
        
        # 获取 GPU 信息
        try:
            smi_output = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                 "--format=json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if smi_output.returncode == 0:
                data = json.loads(smi_output.stdout)
                gpus = []
                for gpu in data.get("gpu", []):
                    gpus.append({
                        "index": int(gpu["index"]),
                        "name": gpu["name"],
                        "memory_total_mb": int(gpu["memory.total"].split()[0]),
                        "memory_used_mb": int(gpu["memory.used"].split()[0]),
                        "memory_free_mb": int(gpu["memory.free"].split()[0]),
                        "utilization_gpu": int(gpu["utilization.gpu"].split()[0]),
                        "temperature": int(gpu["temperature.gpu"].split()[0]),
                    })
                result["gpu_info"] = {"gpu_type": "nvidia", "gpus": gpus}
        except Exception as e:
            result["gpu_info"] = {"gpu_type": "nvidia", "gpus": [], "error": str(e)}
        
        # 检测 CUDA 版本
        try:
            cuda_version = subprocess.run(
                ["nvcc", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if cuda_version.returncode == 0:
                # 解析版本号
                for line in cuda_version.stdout.split("\n"):
                    if "release" in line.lower():
                        result["cuda_version"] = line.strip()
                        break
        except Exception:
            pass
        
        return result
    
    @staticmethod
    def check_amd() -> Dict[str, Any]:
        """检测 AMD GPU (ROCm)"""
        result = {
            "gpu_type": "none",
            "rocm_version": None,
            "rocm_smi_available": False,
            "gpu_info": {"gpu_type": "none", "gpus": []},
        }
        
        # 检查 rocm-smi
        rocm_smi = shutil.which("rocm-smi")
        if not rocm_smi:
            return result
        
        result["rocm_smi_available"] = True
        result["gpu_type"] = "amd"
        
        # 获取 GPU 信息
        try:
            smi_output = subprocess.run(
                ["rocm-smi", "--showallinfo", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if smi_output.returncode == 0:
                data = json.loads(smi_output.stdout)
                gpus = []
                # 解析 ROCm SMI 输出（格式可能因版本而异）
                for card_id, card_info in data.items():
                    if isinstance(card_info, dict):
                        gpus.append({
                            "index": int(card_id) if card_id.isdigit() else 0,
                            "name": card_info.get("Card series", "AMD GPU"),
                            "memory_total_mb": int(card_info.get("VRAM Total Memory", 0)) // (1024 * 1024),
                            "memory_used_mb": int(card_info.get("VRAM Used Memory", 0)) // (1024 * 1024),
                            "memory_free_mb": int(card_info.get("VRAM Free Memory", 0)) // (1024 * 1024),
                            "utilization_gpu": int(card_info.get("GPU Activity (%)", 0)),
                            "temperature": int(card_info.get("Temperature (Sensor edge) (C)", 0)),
                        })
                result["gpu_info"] = {"gpu_type": "amd", "gpus": gpus}
        except Exception as e:
            result["gpu_info"] = {"gpu_type": "amd", "gpus": [], "error": str(e)}
        
        # 检测 ROCm 版本
        try:
            hipcc_version = subprocess.run(
                ["hipcc", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if hipcc_version.returncode == 0:
                for line in hipcc_version.stdout.split("\n"):
                    if "version" in line.lower():
                        result["rocm_version"] = line.strip()
                        break
        except Exception:
            pass
        
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
                    ["python3", "-c", f"import {pkg}; print(getattr({pkg}, '__version__', 'unknown'))"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if version_cmd.returncode == 0:
                    version = version_cmd.stdout.strip()
                    result[f"{pkg}_version"] = version
            except Exception:
                pass
        
        return result
    
    @staticmethod
    def detect_gpu_type() -> str:
        """自动检测 GPU 类型"""
        # 优先检测 NVIDIA
        nvidia = EnvironmentService.check_nvidia()
        if nvidia["nvidia_smi_available"]:
            return "nvidia"
        
        # 检测 AMD
        amd = EnvironmentService.check_amd()
        if amd["rocm_smi_available"]:
            return "amd"
        
        return "none"
    
    def get_full_status(self) -> Dict[str, Any]:
        """获取完整环境状态"""
        python_info = self.check_python()
        
        # 自动检测 GPU 类型
        gpu_type = self.detect_gpu_type()
        
        if gpu_type == "nvidia":
            gpu_info = self.check_nvidia()
        elif gpu_type == "amd":
            gpu_info = self.check_amd()
        else:
            gpu_info = {
                "gpu_type": "none",
                "cuda_version": None,
                "rocm_version": None,
                "nvidia_smi_available": False,
                "rocm_smi_available": False,
                "gpu_info": {"gpu_type": "none", "gpus": []},
            }
        
        package_info = self.check_packages()
        
        # 判断环境状态
        status = "not_installed"
        message = "Environment not checked yet"
        
        if python_info["python_path"]:
            if gpu_type != "none":
                if package_info["vllm_version"]:
                    status = "ready"
                    message = f"Environment ready ({gpu_type.upper()})"
                else:
                    status = "partial"
                    message = "GPU detected but vLLM not installed"
            else:
                status = "partial"
                message = "Python ready but no GPU detected"
        else:
            status = "error"
            message = "Python not found"
        
        return {
            **python_info,
            **gpu_info,
            **package_info,
            "status": status,
            "message": message,
            "last_checked_at": datetime.now().isoformat(),
        }
