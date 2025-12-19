# inspect_db.py
import chromadb
from config import VECTOR_DB_PATH

# 连接到数据库
client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

# 1. 列出所有主题 (Collections)
collections = client.list_collections()
print(f"📊 当前共有 {len(collections)} 个主题:\n")

for col in collections:
    count = col.count() # 获取该主题下的文档数量
    print(f"  📂 主题名称: [{col.name}]")
    print(f"     - 数据量: {count} 条片段")
    
    # 稍微看一眼里面的数据（可选）
#    if count > 0:
#        peek = col.peek(limit=1)
#        if peek['metadatas']:
#            print(f"     - 示例来源: {peek['metadatas'][0].get('filename')}")
#    print("-" * 30)