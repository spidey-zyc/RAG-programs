# fix_paths.py
import os
import chromadb
from chromadb.config import Settings
from config import VECTOR_DB_PATH, COLLECTION_NAME, STATIC_DIR

def get_all_image_files(root_dir):
    """递归扫描 static 目录，建立 {文件名: 相对路径} 的映射"""
    image_map = {}
    print(f"🔍 正在扫描 {root_dir} 下的所有图片...")
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                # 获取绝对路径
                abs_path = os.path.join(root, file)
                # 获取相对于项目根目录的路径 (用于存入数据库)
                # 假设运行在项目根目录，rel_path 应该是 static/images/theme/xxx.png
                rel_path = os.path.relpath(abs_path, start=".")
                
                # 存入字典，Key是文件名，Value是新路径
                image_map[file] = rel_path.replace("\\", "/") # 统一转为正斜杠
    
    print(f"✅ 找到 {len(image_map)} 张图片。")
    return image_map

def fix_database_paths():
    # 1. 连接数据库
    print(f"💾 连接向量数据库: {VECTOR_DB_PATH}")
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH, settings=Settings(anonymized_telemetry=False))
    
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"❌ 找不到集合 {COLLECTION_NAME}: {e}")
        return

    # 2. 获取所有数据 (只获取 metadata 和 ids，不获取 embedding，速度极快)
    # limit设大一点以覆盖所有数据
    data = collection.get(include=["metadatas"])
    
    ids = data["ids"]
    metadatas = data["metadatas"]
    
    if not ids:
        print("⚠️ 数据库为空。")
        return

    # 3. 扫描当前真实的文件位置
    # 假设图片都在 static 文件夹下
    real_image_map = get_all_image_files(STATIC_DIR)

    updates_count = 0
    ids_to_update = []
    metadatas_to_update = []

    print("🛠️ 开始检查数据库记录...")

    for i, meta in enumerate(metadatas):
        # 只要是包含 image_path 的记录
        if meta.get("image_path") and meta.get("is_image"):
            old_path = meta["image_path"]
            filename = os.path.basename(old_path)
            
            # 在新扫描的地图里找这个文件名
            if filename in real_image_map:
                new_path = real_image_map[filename]
                
                # 如果路径不一致，说明你移动过文件
                if old_path != new_path:
                    # 更新 metadata
                    meta["image_path"] = new_path
                    
                    ids_to_update.append(ids[i])
                    metadatas_to_update.append(meta)
                    updates_count += 1
                    print(f"   [修正] {filename}: \n     旧: {old_path} \n     新: {new_path}")
            else:
                print(f"   [警告] 数据库中有图片 {filename}，但在磁盘上找不到！")

    # 4. 批量更新数据库
    if updates_count > 0:
        print(f"\n💾 正在更新 {updates_count} 条记录到数据库...")
        collection.update(
            ids=ids_to_update,
            metadatas=metadatas_to_update
        )
        print("🎉 数据库修复完成！前端现在可以正常显示新位置的图片了。")
    else:
        print("✨ 数据库路径与磁盘文件一致，无需更新。")

if __name__ == "__main__":
    fix_database_paths()