# 改进后的 inspect_db.py
import chromadb
from config import VECTOR_DB_PATH

try:
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collections = client.list_collections()
    print(f"📊 当前共有 {len(collections)} 个主题:\n")

    for col in collections:
        print(f"  📂 主题名称: [{col.name}]")
        
        # 1. 获取数量
        try:
            count = col.count()
            print(f"     - 数据量: {count} 条片段")
        except Exception as e:
            print(f"     - ❌ 获取数量失败: {e}")
            continue

        # 2. 尝试读取数据 (增加容错)
        if count > 0:
            try:
                peek = col.peek(limit=1)
                if peek['metadatas']:
                    print(f"     - 示例来源: {peek['metadatas'][0].get('filename')}")
            except Exception as e:
                print(f"     - ❌ 数据读取失败 (索引可能已损坏): {e}")
        
        print("-" * 30)

except Exception as e:
    print(f"❌ 无法连接数据库: {e}")