"""
Project Manager - Quản lý dự án và hố khoan
"""
import os
import json
import csv
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class ProjectManager:
    """Quản lý dự án và hố khoan"""
    
    def __init__(self, base_dir: str = "projects"):
        """Khởi tạo ProjectManager với thư mục gốc lưu dự án"""
        self.base_dir = Path(base_dir)
        self.current_project: Optional[Dict] = None
        self.current_hole: Optional[Dict] = None
        
        # Tạo thư mục nếu chưa tồn tại
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_project(self, name: str, description: str = "") -> Dict:
        """Tạo dự án mới"""
        # Tạo tên thư mục từ tên dự án (loại bỏ ký tự đặc biệt)
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
        project_dir = self.base_dir / safe_name
        
        # Nếu thư mục đã tồn tại, thêm số vào sau
        counter = 1
        original_name = project_dir.name
        while project_dir.exists():
            project_dir = project_dir.parent / f"{original_name}_{counter}"
            counter += 1
        
        # Tạo cấu trúc thư mục
        (project_dir / "holes").mkdir(parents=True)
        
        # Tạo file thông tin dự án
        project_info = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "path": str(project_dir.absolute())
        }
        
        with open(project_dir / "project_info.json", "w", encoding="utf-8") as f:
            json.dump(project_info, f, indent=2, ensure_ascii=False)
        
        # Tạo file cấu hình các trường dữ liệu mặc định
        self._create_default_fields_config(project_dir)
        
        self.current_project = project_info
        return project_info
    
    def _create_default_fields_config(self, project_dir: Path):
        """Tạo file cấu hình các trường dữ liệu mặc định"""
        default_fields = [
            {"name": "Thời gian", "unit": "datetime", "required": True, "enabled": True},
            {"name": "Độ sâu", "unit": "m", "required": True, "enabled": True},
            {"name": "Vận tốc", "unit": "m/s", "required": True, "enabled": True},
            {"name": "Lực đập", "unit": "N", "required": False, "enabled": False},
            {"name": "Nhiệt độ", "unit": "°C", "required": False, "enabled": False},
            {"name": "Ghi chú", "unit": "text", "required": False, "enabled": False}
        ]
        
        config = {
            "fields": default_fields,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(project_dir / "fields_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def list_projects(self) -> List[Dict]:
        """Liệt kê tất cả các dự án"""
        projects = []
        for item in self.base_dir.iterdir():
            if not item.is_dir():
                continue
                
            info_file = item / "project_info.json"
            if info_file.exists():
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        project_info = json.load(f)
                        projects.append(project_info)
                except (json.JSONDecodeError, IOError):
                    continue
        
        return sorted(projects, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def load_project(self, project_path: str) -> Optional[Dict]:
        """Tải thông tin dự án từ đường dẫn"""
        project_dir = Path(project_path)
        info_file = project_dir / "project_info.json"
        
        if not info_file.exists():
            return None
        
        try:
            with open(info_file, "r", encoding="utf-8") as f:
                project_info = json.load(f)
                self.current_project = project_info
                return project_info
        except (json.JSONDecodeError, IOError):
            return None
    
    def create_hole(self, name: str, location: str = "", notes: str = "") -> Dict:
        """Tạo hố khoan mới trong dự án hiện tại"""
        if not self.current_project:
            raise ValueError("Chưa chọn dự án")
        
        project_dir = Path(self.current_project["path"])
        holes_dir = project_dir / "holes"
        
        # Tạo tên thư mục an toàn
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()
        hole_dir = holes_dir / safe_name
        
        # Nếu thư mục đã tồn tại, thêm số vào sau
        counter = 1
        original_name = hole_dir.name
        while hole_dir.exists():
            hole_dir = hole_dir.parent / f"{original_name}_{counter}"
            counter += 1
        
        # Tạo thư mục hố khoan
        hole_dir.mkdir(parents=True)
        
        # Tạo file thông tin hố khoan
        hole_info = {
            "name": name,
            "location": location,
            "notes": notes,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "data_files": []
        }
        
        with open(hole_dir / "hole_info.json", "w", encoding="utf-8") as f:
            json.dump(hole_info, f, indent=2, ensure_ascii=False)
        
        # Cập nhật thời gian sửa đổi của dự án
        self._update_project_timestamp()
        
        self.current_hole = hole_info
        return hole_info
    
    def list_holes(self) -> List[Dict]:
        """Liệt kê tất cả các hố khoan trong dự án hiện tại"""
        if not self.current_project:
            return []
        
        project_dir = Path(self.current_project["path"])
        holes_dir = project_dir / "holes"
        
        if not holes_dir.exists():
            return []
        
        holes = []
        for item in holes_dir.iterdir():
            if not item.is_dir():
                continue
                
            info_file = item / "hole_info.json"
            if info_file.exists():
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        hole_info = json.load(f)
                        hole_info["path"] = str(item.absolute())
                        holes.append(hole_info)
                except (json.JSONDecodeError, IOError):
                    continue
        
        return sorted(holes, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def save_data(self, data: List[Dict], filename: str = None) -> str:
        """Lưu dữ liệu vào file CSV trong thư mục hố khoan hiện tại"""
        if not self.current_project or not self.current_hole:
            raise ValueError("Chưa chọn dự án hoặc hố khoan")
        
        # Lấy thông tin đường dẫn
        project_dir = Path(self.current_project["path"])
        hole_name = self.current_hole.get('name', 'unknown_hole')
        # Create safe directory name
        safe_hole_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
        holes_dir = project_dir / "holes" / safe_hole_name
        
        # Tạo thư mục nếu chưa tồn tại
        holes_dir.mkdir(parents=True, exist_ok=True)
        
        # Tạo tên file nếu không có
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data_{timestamp}.csv"
        
        # Đảm bảo đuôi .csv
        if not filename.lower().endswith('.csv'):
            filename += '.csv'
        
        filepath = holes_dir / filename
        
        # Determine field names from actual data if data exists
        if data and len(data) > 0:
            field_names = list(data[0].keys())
        else:
            # Fallback to fields from config
            fields_config = self._load_fields_config(project_dir)
            field_names = [f["name"] for f in fields_config["fields"] if f.get("enabled", True)]
        
        # Ghi dữ liệu vào file CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(data)
        
        # Cập nhật danh sách file dữ liệu trong thông tin hố khoan
        self._update_hole_data_files(holes_dir, filename)
        
        # Cập nhật thời gian sửa đổi
        self._update_project_timestamp()
        
        return str(filepath)
    
    def _load_fields_config(self, project_dir: Path) -> Dict:
        """Tải cấu hình các trường dữ liệu"""
        config_file = project_dir / "fields_config.json"
        if not config_file.exists():
            self._create_default_fields_config(project_dir)
        
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _update_hole_data_files(self, hole_dir: Path, filename: str):
        """Cập nhật danh sách file dữ liệu trong thông tin hố khoan"""
        info_file = hole_dir / "hole_info.json"
        if not info_file.exists():
            return
        
        with open(info_file, "r+", encoding="utf-8") as f:
            hole_info = json.load(f)
            
            # Thêm file mới vào danh sách nếu chưa có
            if "data_files" not in hole_info:
                hole_info["data_files"] = []
            
            if filename not in hole_info["data_files"]:
                hole_info["data_files"].append(filename)
                hole_info["updated_at"] = datetime.now().isoformat()
                
                # Ghi lại file
                f.seek(0)
                json.dump(hole_info, f, indent=2, ensure_ascii=False)
                f.truncate()
    
    def _update_project_timestamp(self):
        """Cập nhật thời gian sửa đổi của dự án"""
        if not self.current_project:
            return
        
        project_dir = Path(self.current_project["path"])
        info_file = project_dir / "project_info.json"
        
        if not info_file.exists():
            return
        
        with open(info_file, "r+", encoding="utf-8") as f:
            project_info = json.load(f)
            project_info["updated_at"] = datetime.now().isoformat()
            
            # Ghi lại file
            f.seek(0)
            json.dump(project_info, f, indent=2, ensure_ascii=False)
            f.truncate()
        
        # Cập nhật thông tin dự án hiện tại
        self.current_project = project_info

    def get_data_file_path(self, hole_name: str, filename: str) -> Optional[Path]:
        """Lấy đường dẫn đầy đủ đến file dữ liệu"""
        if not self.current_project:
            return None
            
        project_dir = Path(self.current_project["path"])
        filepath = project_dir / "holes" / hole_name / filename
        
        return filepath if filepath.exists() else None

    def delete_hole(self, hole_name: str, hole_path: str = None) -> bool:
        """Xóa hố khoan khỏi dự án hiện tại"""
        if not self.current_project:
            return False
            
        # Nếu có hole_path, dùng nó luôn
        if hole_path:
            hole_dir = Path(hole_path)
        else:
            # Fallback: cố gắng tìm hole_dir từ tên
            project_dir = Path(self.current_project["path"])
            
            # Tái tạo tên thư mục safe_name từ hole_name
            # Lưu ý: Logic này phải khớp hoàn toàn với create_hole
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in hole_name).strip()
            hole_dir = project_dir / "holes" / safe_name
            
            # Nếu thư mục không tồn tại, thử tìm các thư mục có suffix số (ví dụ: Hole_1)
            if not hole_dir.exists():
                # Thử tìm bằng cách duyệt qua tất cả thư mục và đọc info
                found = False
                holes_dir = project_dir / "holes"
                if holes_dir.exists():
                    for item in holes_dir.iterdir():
                        if item.is_dir():
                            info_file = item / "hole_info.json"
                            if info_file.exists():
                                try:
                                    with open(info_file, "r", encoding="utf-8") as f:
                                        info = json.load(f)
                                        if info.get("name") == hole_name:
                                            hole_dir = item
                                            found = True
                                            break
                                except:
                                    pass
                
                if not found:
                    return False

        try:
            if hole_dir.exists():
                shutil.rmtree(hole_dir)
                
                # Nếu đang là hố khoan hiện tại thì reset
                if self.current_hole and self.current_hole.get("name") == hole_name:
                    self.current_hole = None
                
                self._update_project_timestamp()
                return True
        except Exception as e:
            print(f"Lỗi khi xóa hố khoan {hole_name}: {e}")
            return False
        
        return False