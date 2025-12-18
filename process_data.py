import os
import argparse
from document_loader import DocumentLoader
from text_splitter import TextSplitter
from vector_store import VectorStore
from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, VECTOR_DB_PATH

import base64
from tqdm import tqdm
from rag_agent import RAGAgent # 用于调用 Vision API


# 你的基础数据路径
BASE_DATA_DIR = os.path.join(".", "data")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def process_images_with_vision_model(chunks):
    """
    遍历文档块，找到图片块，调用视觉模型生成描述
    """
    agent = RAGAgent() # 实例化以使用其中的 vision_client
    processed_chunks = []
    
    print("\n👁️ 正在进行图片语义分析与描述生成 (这可能需要一些时间)...")
    
    image_chunks = [c for c in chunks if c.get("is_image")]
    text_chunks = [c for c in chunks if not c.get("is_image")]
    
    # 先把纯文本放进去
    processed_chunks.extend(text_chunks)
    
    for chunk in tqdm(image_chunks, desc="分析图片", unit="张"):
        try:
            img_path = chunk["image_path"]
            if not os.path.exists(img_path):
                continue
                
            base64_img = encode_image(img_path)
            
            # 使用 Agent 中已有的方法生成描述
            # 注意：这里我们复用 understand_image，但提示词是针对通用搜索优化的
            description = agent.understand_image(base64_img)
            
            if description:
                # 更新内容：加上文件名作为前缀，增强检索相关性
                final_content = f"【图片内容描述】(文件: {chunk['filename']}, 页码: {chunk['page_number']})\n{description}"
                chunk["content"] = final_content
                # 移除 is_image 标记，或者保留它用于后续逻辑，这里我们要保留 image_path
                processed_chunks.append(chunk)
                
        except Exception as e:
            print(f"处理图片 {chunk.get('image_path')} 失败: {e}")
    
    return processed_chunks









def main():
    # 1. 解析参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", type=str, default=None, help="指定主题文件夹")
    parser.add_argument("--incremental", action="store_true", help="增量更新模式")
    args = parser.parse_args()

    # 2. 确定路径
    if args.theme:
        target_dir = os.path.join(BASE_DATA_DIR, args.theme)
    else:
        target_dir = BASE_DATA_DIR # 默认处理全部

    if not os.path.exists(target_dir):
        print(f"目录不存在: {target_dir}")
        return

    print(f"📂 处理目录: {target_dir}")

    # 3. 初始化
    # 注意：DocumentLoader 会递归加载，所以如果是处理子文件夹，它只会加载该文件夹下的
    loader = DocumentLoader(data_dir=target_dir)
    splitter = TextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    vector_store = VectorStore(db_path=VECTOR_DB_PATH)
    

    # 4. 清理策略
    if not args.incremental:
        print("🧹 全量模式：清空数据库...")
        vector_store.clear_collection()
    else:
        print("➕ 增量模式：保留旧数据...")

    # 5. 执行处理
    documents = loader.load_all_documents(specific_dir=target_dir)
    if not documents:
        print("⚠️ 该目录下没有文档")
        return

    
# 6. 切分文档
    # 注意：我们需要修改 TextSplitter 以跳过已经标记为 is_image 的块，或者在 split_documents 后处理
    # 这里我们采用简单的策略：先切分文本，图片块保持原样
    
    # 临时策略：手动分离
    raw_text_docs = [d for d in documents if not d.get("is_image")]
    raw_image_docs = [d for d in documents if d.get("is_image")]
    
    # 切分文本
    text_chunks = splitter.split_documents(raw_text_docs)
    
    # 合并图片块（无需切分，因为每个图片就是一个独立的知识点）
    # 并且要给图片块加上必要的 chunk_id 等字段
    image_chunks_formatted = []
    for i, img_doc in enumerate(raw_image_docs):
        img_doc["chunk_id"] = f"img_{i}"
        image_chunks_formatted.append(img_doc)
        
    all_chunks = text_chunks + image_chunks_formatted
    
    # 7. 关键步骤：调用视觉模型增强数据
    # 只有当存在图片块时才调用
    if image_chunks_formatted:
        all_chunks = process_images_with_vision_model(all_chunks)
    
    print(f"💾 写入 {len(all_chunks)} 条数据 (含文本与图片描述)...")
    
    # 注意：确保 vector_store.add_documents 能处理 metadata 中的 None 值
    # 最好在 add_documents 前把 metadata 清洗一下，把 None 转为空字符串
    for chunk in all_chunks:
        if "is_image" in chunk: del chunk["is_image"] # 清理标记
        if chunk.get("image_path") is None: chunk["image_path"] = ""
            
    vector_store.add_documents(all_chunks)
    
    print("✅ 完成！")

if __name__ == "__main__":
    main()