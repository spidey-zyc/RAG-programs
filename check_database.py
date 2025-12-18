import os
import chromadb
from chromadb.config import Settings
from config import VECTOR_DB_PATH, COLLECTION_NAME

def check_images_specifically():
    print(f"🎯 正在连接数据库: {VECTOR_DB_PATH}")
    
    if not os.path.exists(VECTOR_DB_PATH):
        print("❌ 数据库文件不存在！")
        return

    client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH, 
        settings=Settings(anonymized_telemetry=False)
    )
    
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"❌ 无法读取集合: {e}")
        return

    print("🔍 正在使用 metadata 过滤器查找图片数据...")

    # === 尝试方案 A: 通过 is_image=True 过滤 ===
    try:
        # ChromaDB 支持 where 过滤
        results = collection.get(
            where={"is_image": True},
            include=["metadatas", "documents"]
        )
        
        count = len(results["ids"])
        print(f"📊 标记为 'is_image=True' 的数据条数: {count}")
        
        if count == 0:
            print("⚠️ 警告: 数据库里没有一条数据的 metadata 包含 {'is_image': True}")
            print("👉这说明你之前的 process_data.py 可能根本没把图片标记写进去，或者你运行的是旧版本代码。")
        else:
            print("\n📸 发现图片数据！正在检查路径完整性：")
            for i in range(min(count, 5)): # 只看前5条
                meta = results["metadatas"][i]
                doc_preview = results["documents"][i][:30].replace("\n", "")
                
                img_path = meta.get("image_path")
                print(f"  [{i}] 文件名: {meta.get('filename')}")
                print(f"      内容摘要: {doc_preview}...")
                print(f"      📍 image_path: {img_path}")
                
                if not img_path:
                    print("      ❌ 路径丢失! (image_path is None)")
                elif not os.path.exists(img_path):
                    print(f"      ❌ 路径无效! (硬盘上找不到文件: {img_path})")
                else:
                    print("      ✅ 路径有效，文件存在。")
                print("-" * 40)

    except Exception as e:
        print(f"❌ 查询出错: {e}")

    # === 尝试方案 B: 如果方案A没找到，尝试暴力扫描 ===
    # 防止 is_image 标记没打上，但 image_path 有值的情况
    if count == 0:
        print("\n🔄 尝试方案 B: 暴力扫描前 1000 条数据，查找任何包含 '.png/.jpg' 的记录...")
        all_data = collection.get(limit=1000, include=["metadatas"])
        found_any = False
        for meta in all_data["metadatas"]:
            path = meta.get("image_path")
            if path and isinstance(path, str) and len(path) > 5:
                print(f"  Found one! Filename: {meta.get('filename')} | Path: {path}")
                found_any = True
        
        if not found_any:
            print("🛑 彻底确认：数据库里没有任何有效的 image_path 记录。")

if __name__ == "__main__":
    check_images_specifically()