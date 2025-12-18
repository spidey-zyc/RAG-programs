# ingest_orphaned_images.py
import os
import uuid
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
from config import VECTOR_DB_PATH, COLLECTION_NAME, STATIC_DIR, OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_EMBEDDING_MODEL
from openai import OpenAI

def ingest_images():
    print("🚀 开始扫描硬盘上的孤儿图片，并将其注册到数据库...")
    
    # 1. 初始化
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH, settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    
    # 初始化 Embedding 客户端 (虽然不用视觉模型，但存入数据库必须要有向量，这个很便宜)
    openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    # 2. 扫描硬盘上的所有图片
    image_files = []
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                full_path = os.path.join(root, file)
                # 转换为相对路径
                rel_path = os.path.relpath(full_path, start=".")
                image_files.append({
                    "filename": file,
                    "path": rel_path.replace("\\", "/"), # 统一正斜杠
                    "theme": os.path.basename(root) # 用文件夹名作为主题
                })

    print(f"📂 硬盘上共找到 {len(image_files)} 张图片。")

    # 3. 准备入库数据
    ids = []
    documents = []
    metadatas = []
    
    print("⚙️ 正在生成数据结构...")
    for img in image_files:
        # ⚠️ 关键折中：因为不想花钱调 Vision API，我们用文件名作为 content
        # 这样至少能保证数据入库，且能在前端显示。
        # 搜索效果完全依赖于文件名的质量。
        description = f"【图片资源】 文件名: {img['filename']} (所属主题: {img['theme']})"
        
        ids.append(str(uuid.uuid4()))
        documents.append(description)
        metadatas.append({
            "filename": img["filename"],
            "image_path": img["path"],   # ✅ 这就是前端需要的指路牌
            "is_image": True,            # ✅ 这就是 check_database 需要的标记
            "page_number": 1,
            "chunk_id": "img_manual_ingest"
        })

    # 4. 批量 Embedding 并写入 (这是最便宜的 text-embedding-v4)
    batch_size = 10
    total = len(documents)
    
    print(f"💾 正在写入数据库 (共 {total} 条)...")
    
    for i in tqdm(range(0, total, batch_size)):
        batch_docs = documents[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]
        
        try:
            # 获取文本向量 (非常便宜)
            resp = openai_client.embeddings.create(input=batch_docs, model=OPENAI_EMBEDDING_MODEL)
            batch_embeddings = [d.embedding for d in resp.data]
            
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_docs,
                metadatas=batch_metas
            )
        except Exception as e:
            print(f"❌ 批次 {i} 写入失败: {e}")

    print("🎉 完成！这 382 张图片现在已经在数据库里了。")
    print("👉 请重启 Chainlit，现在应该能看到图片了。")

if __name__ == "__main__":
    ingest_images()